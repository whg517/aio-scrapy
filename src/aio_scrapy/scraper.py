import asyncio
import logging
from collections import deque
from typing import TYPE_CHECKING, Awaitable, Deque, Type

from aio_scrapy import signals
from aio_scrapy.exceptions import DropItem
from aio_scrapy.pipelines import ItemPipelineManager
from aio_scrapy.utils import load_object, wrapper_run_function

if TYPE_CHECKING:
    from aio_scrapy.crawler import Crawler
    from aio_scrapy.spiders import BaseSpider

logger = logging.getLogger(__name__)


class Scraper:

    def __init__(self, crawler: 'Crawler'):
        self.crawler = crawler
        item_processor_cls: Type[ItemPipelineManager] = load_object(crawler.settings.get('ITEM_PROCESSOR'))
        self.item_processor = item_processor_cls.from_crawler(crawler)
        self.max_size: int = crawler.settings.get('CONCURRENT_ITEMS')
        self.active: int = 0
        self.queue: Deque = deque()

    async def open_spider(self, spider: 'BaseSpider'):
        await self.item_processor.open_spider(spider)

    async def close_spider(self, spider: 'BaseSpider'):
        await self.item_processor.close_spider(spider)

    def should_revocation(self):
        return self.active >= self.max_size

    def is_idle(self):
        return not self.queue

    def enqueue_scrape(self, request, response, spider: 'BaseSpider') -> Awaitable:
        """
        Enqueue request, background process queue. Increase active during process a request and decrease
        active count when processed.
        Return a future object immediately, and future is done when a request processed.
        :param request:
        :param response:
        :param spider:
        :return:
        """
        future = self.crawler.loop.create_future()

        # Decrease active count when future is done.
        def _deactivate(x):
            self.active -= 1

        future.add_done_callback(_deactivate)
        self.queue.append((request, response, future))
        self.crawler.loop.create_task(self._scrap_from_queue(spider))
        return future

    async def _scrap_from_queue(self, spider):
        while self.queue:
            request, response, future = self.queue.popleft()
            # Increase active count when process item.
            self.active += 1
            parse = getattr(spider, 'parse')
            if parse:
                if asyncio.iscoroutinefunction(parse):
                    item = await parse(response)

                else:
                    item = await wrapper_run_function(parse, response)
                result = await self.handle_spider_output(item, request, response, spider)

                future.set_result(result)

    async def handle_spider_output(self, output, request, response, spider: 'BaseSpider'):
        if isinstance(output, dict):
            try:
                result = await self.item_processor.process_item(output, spider)
            except Exception as e:
                result = e
            await self._item_process_finished(result, output, response, spider)
        else:
            logger.error(f'Spider must return Dict or None, got {type(output).__name__} in {request}')

    async def _item_process_finished(self, output, item, response, spider):
        if isinstance(output, Exception):
            if isinstance(output, DropItem):
                await self.crawler.signals.send(
                    signal=signals.item_dropped,
                    item=item,
                    response=response,
                    spider=spider,
                    exception=output
                )
            else:
                await self.crawler.signals.send(
                    signal=signals.item_error,
                    item=item,
                    response=response,
                    spider=spider,
                    failure=output
                )
        else:
            logger.debug(f'Scraped from {response} \n{item}')
            await self.crawler.signals.send(
                signal=signals.item_scraped,
                item=output,
                response=response,
                spider=spider
            )
