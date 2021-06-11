import logging
from typing import TYPE_CHECKING, Any, Dict, Optional

from aiohttp import ClientResponse
from aiohttp.typedefs import StrOrURL

from aio_scrapy import signals
from aio_scrapy.utils import wrapper_run_function

if TYPE_CHECKING:  # pragma: no cover
    from aio_scrapy.crawler import Crawler  # noqa


class BaseSpider:
    name = None

    custom_settings: Optional[Dict] = None

    def __init__(self, name: str = None, **kwargs: Any):
        if name is not None:
            self.name = name
        elif not getattr(self, 'name', None):
            raise ValueError(f'{type(self).__name__} must have a name')
        self.__dict__.update(kwargs)
        if not hasattr(self, 'start_urls'):
            self.start_urls = []

    @property
    def logger(self):
        logger = logging.getLogger(self.name)
        return logger

    @classmethod
    def from_crawl(cls, crawler: 'Crawler', *args: Any, **kwargs: Any):
        spider = cls(*args, **kwargs)
        spider._set_crawler(crawler)
        return spider

    @classmethod
    def update_settings(cls, settings):
        settings.update(cls.custom_settings or {}, priority='spider')

    def _set_crawler(self, crawler: 'Crawler'):
        self.crawler = crawler
        self.settings = crawler.settings
        crawler.signals.connect(self.close, signals.spider_closed)

    @staticmethod
    async def close(spider, reason):
        closed = getattr(spider, 'closed', None)
        if callable(closed):
            return await wrapper_run_function(closed, reason)

    def start_requests(self) -> StrOrURL:
        for url in self.start_urls:
            yield url

    async def parse(self, response: ClientResponse):
        raise NotImplementedError('{}.parse callback is not defined'.format(self.__class__.__name__))

    def __str__(self):
        return f'<{type(self).__name__}, {self.name} at {id(self)}>'

    __repr__ = __str__
