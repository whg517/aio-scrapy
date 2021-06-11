from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aio_scrapy.crawler import Crawler
    from aio_scrapy.spiders import BaseSpider


class BaseScheduler:

    @classmethod
    def from_crawler(cls, crawler: 'Crawler', *args, **kwargs):
        raise NotImplementedError

    def open(self, spider: 'BaseSpider'):
        raise NotImplementedError

    def close(self, reason):
        raise NotImplementedError

    def enqueue_request(self, request):
        raise NotImplementedError

    def has_pending_requests(self):
        raise NotImplementedError

    def next_request(self):
        raise NotImplementedError


class SimpleScheduler(BaseScheduler):

    def __init__(self):
        self.queue_cls = deque

        self.queue = self.queue_cls()

    @classmethod
    def from_crawler(cls, crawler: 'Crawler', *args, **kwargs):
        return cls()

    def enqueue_request(self, request):
        self.queue.append(request)

    def has_pending_requests(self):
        return len(self.queue) > 0

    def next_request(self):
        if self.queue:
            return self.queue.popleft()
        else:
            return None

    async def open(self, spider: 'BaseSpider'):
        pass

    async def close(self, reason):
        pass
