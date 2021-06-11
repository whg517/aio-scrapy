import asyncio
import logging
import pprint
from collections import defaultdict, deque
from typing import TYPE_CHECKING, Any, List, Optional

from aio_scrapy.settings import Settings
from aio_scrapy.utils import create_instance, load_object, wrapper_run_function

if TYPE_CHECKING:
    from aio_scrapy.crawler import Crawler
    from aio_scrapy.spiders import BaseSpider

logger = logging.getLogger(__name__)


class BaseMiddlewareManager:
    """
    Basic middleware manager, you should inherit it and implement some methods what must implement.
    """

    component_name = 'base middleware'

    def __init__(self, *middlewares):
        self.middlewares = middlewares
        self.methods = defaultdict(deque)
        for mw in middlewares:
            self._add_middleware(mw)

    @classmethod
    def from_settings(cls, settings: Settings, crawler: Optional['Crawler'] = None):
        mw_list = cls._get_mw_list_from_settings(settings)
        middlewares = []
        enabled = []
        for cls_path in mw_list:
            mw_cls = load_object(cls_path)
            mw = create_instance(mw_cls, settings, crawler)
            middlewares.append(mw)
            enabled.append(cls_path)

        logger.info(f'Enabled {cls.component_name}: \n {pprint.pformat(enabled)}')

        return cls(*middlewares)

    @classmethod
    def from_crawler(cls, crawler: 'Crawler'):
        return cls.from_settings(crawler.settings, crawler)

    @classmethod
    def _get_mw_list_from_settings(cls, settings) -> List[str]:
        raise NotImplementedError

    def _add_middleware(self, mw: Any):
        if hasattr(mw, 'open_spider'):
            self.methods['open_spider'].append(mw.open_spider)
        if hasattr(mw, 'close_spider'):
            self.methods['close_spider'].appendleft(mw.close_spider)

    async def _process_chain(self, method_name: str, obj: Any, *args: Any):
        for callback in self.methods[method_name]:
            obj = await callback(obj, *args)
        return obj

    async def _process_parallel(self, method_name: str, obj: Any, *args: Any):
        callbacks = [wrapper_run_function(callback, obj, *args) for callback in self.methods[method_name]]
        return await asyncio.gather(*callbacks)

    async def open_spider(self, spider: 'BaseSpider'):
        return await self._process_parallel('open_spider', spider)

    async def close_spider(self, spider: 'BaseSpider'):
        return await self._process_parallel('close_spider', spider)
