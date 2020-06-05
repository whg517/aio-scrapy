import os
from logging.config import dictConfig

from aio_scrapy.settings import Settings


def verbose_formatter(verbose: bool) -> str:
    if verbose is True:
        return 'verbose'
    else:
        return 'simple'


def configure_logging(settings: Settings):
    os.makedirs(settings.get('LOG_DIR'), exist_ok=True)
    default_logging = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            'verbose': {
                'format': '%(asctime)s %(levelname)s %(name)s %(process)d %(thread)d %(message)s'
            },
            'simple': {
                'format': '%(asctime)s %(levelname)s %(message)s'
            },
            "access": {
                "()": "uvicorn.logging.AccessFormatter",
                "fmt": '%(asctime)s %(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s',
            },
        },
        "handlers": {
            "console": {
                "formatter": 'verbose',
                'level': 'DEBUG',
                "class": "logging.StreamHandler",
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'DEBUG',
                'formatter': 'verbose',
                'filename': settings.get('LOGFILE'),
                'maxBytes': 1024 * 1024 * 1024 * 200,  # 200M
                'backupCount': '5',
                'encoding': 'utf-8'
            },
        },
        "loggers": {
            '': {'level': settings.get('LOGLEVEL'), 'handlers': ['console', 'file']},
        }
    }
    dictConfig(default_logging)
