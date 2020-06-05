from typing import TYPE_CHECKING, Dict, List

from aio_scrapy.middlewares import BaseMiddlewareManager

if TYPE_CHECKING:
    from aio_scrapy.spiders import BaseSpider


class ItemPipelineManager(BaseMiddlewareManager):

    component_name = 'item pipeline'

    @classmethod
    def _get_mw_list_from_settings(cls, settings) -> List[str]:
        return settings.get('ITEM_PIPELINES')

    async def process_item(self, item: Dict, spider: 'BaseSpider'):
        return await self._process_chain('process_item', item, spider)
