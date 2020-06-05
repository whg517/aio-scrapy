import asyncio
import logging
import uuid
from asyncio import Future, Task
from collections import deque
from time import time
from typing import TYPE_CHECKING, Deque, Optional, Set

from aiohttp import BasicAuth, ClientSession, TCPConnector
from aiohttp.client_reqrep import ConnectionKey
from yarl import URL

from aio_scrapy import signals

if TYPE_CHECKING:
    from proxypool.scrapy.crawler import Crawler

logger = logging.getLogger(__name__)


class Downloader:

    def __init__(self, crawler: 'Crawler'):
        self.session: Optional[ClientSession] = None
        self.crawler = crawler
        self.max_limit: int = crawler.settings.get('CONCURRENT_REQUESTS')
        self.connector = TCPConnector(limit=self.max_limit)

        self.download_delay: bool = crawler.settings.get('DOWNLOAD_DELAY')

        self.default_user_agent = crawler.settings.get('DEFAULT_USERAGENT')

        self.last_seen: int = 0

        self.active: Set = set()
        self.queue: Deque = deque()
        self.process_queue_task: Optional[Task] = None
        self.crawler.signals.connect(self.engine_started, signal=signals.engine_started)

    def engine_started(self):
        self.init_session()

    def available_connections(self):
        """获取实际可用连接数量"""
        key = ConnectionKey(
            host='',
            port=0,
            is_ssl=True,
            ssl=None,
            proxy=URL(),
            proxy_auth=BasicAuth(login=''),
            proxy_headers_hash=0
        )
        return self.connector._available_connections(key)

    def should_revocation(self) -> bool:
        """
        如果可用连接数为 0 则返回 True
        :return:
        """
        return self.available_connections() <= 0

    def fetch(self, url: URL):
        response = self.enqueue_request(url)
        logger.info(f'Download: {url}')
        return response

    def enqueue_request(self, url: URL):
        """
        这里之所以使用一个 _id ，是因为 URL 类覆盖了 __eq__ 和 __hash__ 方法
        如果两个 url 字符串一样则这两个　URL 对象是同一个，放入 set() 集合中会
        被去重。
        :param url:
        :return:
        """
        _id = uuid.uuid1()

        def _deactivate(response: Future):
            self.active.remove(_id)

        self.active.add(_id)
        future = self.crawler.loop.create_future()
        self.queue.append((url, future))
        self.crawler.loop.create_task(self.process_queue())

        future.add_done_callback(_deactivate)
        return future

    async def process_queue(self, delay: Optional[float] = 0):
        """
        处理队列中数据
        :param delay:
        :return:
        """
        # 如果需要延时，延迟调用
        if delay:
            await asyncio.sleep(delay)

        # 如果任务正在执行，直接返回
        if self.process_queue_task and not self.process_queue_task.done():
            return

        now = time()
        # 下载延时，如果两次之间间隔小于设置的延时时间，则在下次调用会延长时间间隔和设置延时时间的差值
        if self.download_delay:
            interval = now - self.last_seen
            if interval < self.download_delay:
                # 满足延时条件，计算需要延时的实际时间
                _delay = self.download_delay - interval
                self.process_queue_task = self.crawler.loop.create_task(self.process_queue(_delay))
                return

        # 如果队列中有数据，且有可用连接，则持续调用
        while self.queue and self.available_connections() > 0:
            url, future = self.queue.popleft()
            response = await self.download(url)
            self.last_seen = now
            future.set_result(response)

            if self.download_delay:
                await self.process_queue()
                break

    async def download(self, url: URL):
        headers = {'user-agent': self.default_user_agent}
        response = await self.session.get(url, headers=headers)
        logger.info(f'Session download {url}')
        return response

    def init_session(self):
        if self.session is None:
            logger.debug('Init session')
            self.session = ClientSession(connector=self.connector)

    async def close(self):
        logger.debug('Close downloader.')
        if self.process_queue_task:
            self.process_queue_task.cancel()
        await self.session.close()
        await self.connector.close()
