from asyncio import AbstractEventLoop
from typing import TYPE_CHECKING, Dict, Optional, Type, Union

if TYPE_CHECKING:
    from aio_scrapy.spiders import BaseSpider
    from aio_scrapy.settings import Settings


def get_crawler(
        spider_cls: Type['BaseSpider'] = None,
        settings_dict: Optional[Union[Dict, 'Settings']] = None,
        loop: Optional[AbstractEventLoop] = None
):
    from aio_scrapy.crawler import CrawlerRunner
    from aio_scrapy.spiders import BaseSpider

    runner = CrawlerRunner(settings_dict, loop)
    return runner.create_crawler(spider_cls or BaseSpider)
