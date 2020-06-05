import json
import os
from datetime import datetime
from typing import TYPE_CHECKING, Dict, Optional, TextIO

from aio_scrapy.pipelines.base import BasePipeline
from aio_scrapy.settings import Settings

if TYPE_CHECKING:
    from examples.demo import Spider
    from aio_scrapy.crawler import Crawler


class FilePipeline(BasePipeline):

    def __init__(self, settings: Settings):
        self.settings = settings
        self.path = '/tmp/test_scrapy'
        os.makedirs(self.path, exist_ok=True)
        self.file = os.path.join(self.path, f'{datetime.now().strftime("%Y%m%d%H%M%S")}.txt')
        self.file_obj: Optional[TextIO] = None

    @classmethod
    def from_crawler(cls, crawler: 'Crawler') -> 'FilePipeline':
        return cls(crawler.settings)

    def open_spider(self, spider: 'Spider'):
        self.file_obj = open(self.file, mode='w+', encoding='utf-8')

    def can_write(self) -> bool:
        return self.file_obj and not self.file_obj.closed

    async def process_item(self, item: Dict, spider: 'Spider'):
        if self.can_write():
            self.file_obj.write(json.dumps(item))

    def close_spider(self, spider: 'Spider'):
        if self.can_write():
            self.file_obj.close()
