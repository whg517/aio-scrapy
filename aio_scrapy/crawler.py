import asyncio
import logging
from asyncio import Future
from typing import Any, Optional, Set, Type

from aio_scrapy.engine import ExecutionEngine
from aio_scrapy.settings import Settings
from aio_scrapy.signal_manager import SignalManager
from aio_scrapy.spiders import BaseSpider

logging.basicConfig(level=logging.DEBUG)


class Crawler:

    def __init__(
            self,
            spider_cls: Type[BaseSpider],
            settings: Optional[Settings] = None,
            loop: Optional[asyncio.AbstractEventLoop] = None
    ):
        self.loop = loop or asyncio.get_event_loop()
        self.spider_cls = spider_cls

        if isinstance(settings, dict) or settings is None:
            settings = Settings(settings)
        self.settings = settings.copy()

        self.spider_cls.update_settings(self.settings)

        self.signals = SignalManager(self)
        self.spider = None
        self.engine = ExecutionEngine(self)

        self.future = self.loop.create_future()

    def _create_spider(self, **kwargs: Any) -> BaseSpider:
        return self.spider_cls.from_crawl(self, **kwargs)

    async def crawl(self, **kwargs: Any) -> None:
        self.spider = self._create_spider(**kwargs)
        start_requests = self.spider.start_requests()
        await self.engine.open_spider(self.spider, start_requests)
        await self.engine.start()

    async def stop(self) -> None:
        await self.engine.stop()


class CrawlerRunner:

    def __init__(
            self,
            settings: Optional[Settings] = None,
            loop: Optional[asyncio.AbstractEventLoop] = None
    ) -> None:
        self.settings = settings
        self.loop = loop or asyncio.get_event_loop()
        self._tasks: Set[Future] = set()
        self.crawlers: Set[Crawler] = set()

    def crawl(
            self,
            spider_cls: Type[BaseSpider],
            **kwargs: Any
    ) -> None:
        crawler = self.create_crawler(spider_cls)
        self.crawlers.add(crawler)
        task = self.loop.create_task(crawler.crawl(**kwargs))
        self._tasks.add(task)

    def create_crawler(self, spider_cls: Type[BaseSpider]):
        return Crawler(spider_cls, self.settings, self.loop)

    async def join(self) -> None:
        await asyncio.gather(*self._tasks)

    async def stop(self) -> None:
        await asyncio.gather(*[crawler.stop for crawler in self.crawlers])

    def run_until_complete(self) -> None:
        self.loop.run_until_complete(self.join())
