import pytest

from aio_scrapy.crawler import Crawler
from aio_scrapy.spiders import BaseSpider


class TestExecuteEngine:

    @pytest.fixture()
    async def crawler(self):
        crawler = Crawler(BaseSpider)
        yield crawler
        await crawler.stop()

    @pytest.mark.asyncio
    async def test_open_spider(self, crawler):
        pass
