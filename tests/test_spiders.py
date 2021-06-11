import inspect

import pytest
from aio_scrapy import signals

from aio_scrapy.spiders import BaseSpider
from aio_scrapy.utils.test import get_crawler


class TestBaseSpider:
    spider_cls = BaseSpider
    spider_name = 'demo'

    @pytest.fixture()
    def spider(self):
        yield self.spider_cls(name=self.spider_name)

    def test_init(self):
        spider = self.spider_cls(self.spider_name, demo=1)
        assert spider.start_urls == []
        assert spider.name == self.spider_name
        assert spider.demo == 1

    def test_init_error(self):
        with pytest.raises(ValueError, match=r'.* must have a name'):
            self.spider_cls()

    def test_start_requests(self):
        url = 'http://example.com'

        class Spider(self.spider_cls):
            name = self.spider_name
            start_urls = [url]

        spider = Spider()
        assert inspect.isgenerator(spider.start_requests())
        assert [url] == list(spider.start_requests())

    @pytest.mark.asyncio
    async def test_close(self, loop):
        class DemoSpider(self.spider_cls):
            name = 'demo'
            close_called = False

            async def closed(self, reason):
                self.close_called = True

        crawler = get_crawler(DemoSpider)
        spider = DemoSpider.from_crawl(crawler, name='demo')
        await crawler.signals.send(signals.spider_closed, spider=spider, reason=None)
        assert spider.close_called

    def test_logger(self, spider):
        assert spider.logger.name == self.spider_name

    @pytest.mark.asyncio
    async def test_parse(self, mocker, spider):
        with pytest.raises(NotImplementedError):
            await spider.parse(mocker)

    def test__str(self, spider):
        assert self.spider_name in str(spider)
