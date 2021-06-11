from typing import TYPE_CHECKING, Dict, Optional

from aio_scrapy.settings import Settings

if TYPE_CHECKING:
    from aio_scrapy.crawler import Crawler
    from examples.demo import Spider


class BasePipeline:

    @classmethod
    def from_settings(
            cls,
            settings: Settings,
            crawler: Optional[Crawler] = None
    ) -> Optional['BasePipeline']:
        pass

    @classmethod
    def from_crawler(cls, crawler: 'Crawler') -> Optional['BasePipeline']:
        pass

    async def process_item(self, item: Dict, spider: 'Spider'):
        raise NotImplementedError

    async def open_spider(self, spider: 'Spider'):
        pass

    async def close_spider(self, spider: 'Spider'):
        pass
