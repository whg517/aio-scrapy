import logging
from asyncio.futures import Future
from typing import TYPE_CHECKING, Any, Optional

from periodic import Periodic
from yarl import URL

from aio_scrapy import signals
from aio_scrapy.downloader import Downloader
from aio_scrapy.exceptions import DontCloseSpider
from aio_scrapy.scheduler import SimpleScheduler
from aio_scrapy.scraper import Scraper
from aio_scrapy.utils import CallLateOnce

if TYPE_CHECKING:
    from aio_scrapy.crawler import Crawler
    from aio_scrapy.spiders import BaseSpider
logger = logging.getLogger(__name__)


class Slot:

    def __init__(self):
        self.in_progress = set()

    def add_in_progress(self, task: Future):
        self.in_progress.add(task)

    def remove_in_progress(self, task: Future):
        self.in_progress.remove(task)


class ExecutionEngine:

    def __init__(self, crawler: 'Crawler') -> None:
        self.downloader = Downloader(crawler)
        self.scheduler = SimpleScheduler.from_crawler(crawler)
        self.crawler = crawler
        self.running = False
        self._close_wait: Future = self.crawler.loop.create_future()

        self.slot = Slot()

        self.spider: Optional['BaseSpider'] = None

        self.request_periodic_task: Optional[Periodic] = None

        self.scraper = Scraper(self.crawler)

        self.next_call: Optional[CallLateOnce] = None

        self.is_idle = False
        self.close_if_idle = True
        self.closing = False

    async def start(self) -> Any:
        logger.info('Engine start')
        await self.crawler.signals.send(signal=signals.engine_started)
        self.running = True
        if self.request_periodic_task:
            await self.request_periodic_task.start()
        return await self._close_wait

    async def stop(self) -> None:
        logger.info('Engine stop.')
        self.slot.closing = True
        await self.crawler.signals.send(signal=signals.engine_stopped)
        self.running = False
        if self.request_periodic_task:
            await self.request_periodic_task.stop()

        self._close_wait.set_result('stop')

    async def open_spider(self, spider: 'BaseSpider', start_urls, close_if_idle: bool = True) -> None:
        self.close_if_idle = close_if_idle
        self.spider = spider
        await self.crawler.signals.send(signal=signals.spider_opened, spider=spider)
        self.next_call = CallLateOnce(self._next_request, start_urls)
        self.request_periodic_task = Periodic(5, self.next_call.scheduler)

    def should_revocation(self):

        if any([
            self.downloader.should_revocation(),
            self.scraper.should_revocation(),
            self.closing
        ]):
            return True

    async def _next_request(self, start_requests) -> None:
        """
        Schedule next request. If should revocation, it will not schedule url to queue.
        And check spider is idle, will close or idle.
        :param start_requests:
        :return:
        """
        while not self.should_revocation():
            if not await self._next_request_from_scheduler(self.spider):
                break

        if start_requests and not self.should_revocation():
            try:
                url = next(start_requests)
                url = URL(url)
            except StopIteration:
                pass
            else:
                await self.crawl(url, self.spider)

        if self.spider_is_idle(self.spider) and self.close_if_idle:
            await self._spider_idle(self.spider)

    async def crawl(self, url: URL, spider):
        """
        Add url to scheduler queue.
        :param url:
        :param spider:
        :return:
        """
        self.scheduler.enqueue_request(url)
        await self.next_call.scheduler()

    async def _next_request_from_scheduler(self, spider) -> bool:
        url = self.scheduler.next_request()
        if url:
            await self.next_call.scheduler()
            response = await self.downloading(url)
            await self.scraper.enqueue_scrape(url, response, spider)
            return True
        else:
            return False

    async def downloading(self, url: URL):
        response = await self.downloader.fetch(url)
        await self.next_call.scheduler()
        return response

    async def _spider_idle(self, spider: 'BaseSpider'):
        results = await self.crawler.signals.send(signal=signals.spider_idle, dont_log=DontCloseSpider)
        if any(isinstance(result, DontCloseSpider) for func, result in results):
            return

        if self.spider_is_idle(spider):
            await self.close_spider(spider, reason='finished')

    def spider_is_idle(self, spider):
        if not self.scraper.is_idle():
            return False

        if self.downloader.active:
            return False

        if self.scheduler.has_pending_requests():
            return False

        return True

    async def close_spider(self, spider, reason='finished'):
        if not self.closing:
            self.closing = True
            await self.downloader.close()
            await self.scraper.close_spider(spider)
            await self.scheduler.close(reason)
            await self.crawler.signals.send(signals.spider_closed, spider=spider, reason=reason)
            await self.stop()
