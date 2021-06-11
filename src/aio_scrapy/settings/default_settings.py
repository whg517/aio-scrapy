import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

LOG_DIR = os.path.join(BASE_DIR, 'log')
LOGFILE = os.path.join(LOG_DIR, 'aio_scrapy.log')

DEFAULT_USERAGENT = 'Mozilla/5.0 (Windows NT 10) AppleWebKit/537.2 (KHTML, like Gecko) Chrome/83.0.61 Safari/537.36'

ITEM_PROCESSOR = 'aio_scrapy.pipelines.ItemPipelineManager'

ITEM_PIPELINES = {}

DOWNLOAD_DELAY = 0.5

CONCURRENT_ITEMS = 10
CONCURRENT_REQUESTS = 10
