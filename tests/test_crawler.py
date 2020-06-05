import pytest

from proxypool.scrapy.crawler import Crawler
from proxypool.scrapy.spiders import BaseSpider


class TestCrawler:
    @pytest.mark.asyncio
    async def test_crawl(self, loop, mocker_server):
        class Spider(BaseSpider):
            name = 'test'
            start_urls = [f'{mocker_server}?id={i}' for i in range(1)]

            def parse(self, response):
                return {'url': response.url}

        crawler = Crawler(Spider, loop=loop)
        await crawler.crawl()


class TestCrawlerRunner:
    pass
