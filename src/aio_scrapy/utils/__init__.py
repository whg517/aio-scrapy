import asyncio
import functools
from asyncio import Task
from importlib import import_module
from typing import Any, Awaitable, Callable, Optional, TypeVar, Union

T = TypeVar('T')


def load_object(path: str):
    try:
        dot = path.rindex('.')
    except ValueError:
        raise ValueError("Error loading object '%s': not a full path" % path)

    module, name = path[:dot], path[dot + 1:]
    mod = import_module(module)

    try:
        obj = getattr(mod, name)
    except AttributeError:
        raise NameError("Module '%s' doesn't define any object named '%s'" % (module, name))

    return obj


def create_instance(cls: Any, settings, crawler, *args, **kwargs):
    if settings is None:
        if crawler is None:
            raise ValueError("Specify at least one of settings and crawler.")
        settings = crawler.settings
    if crawler and hasattr(cls, 'from_crawler'):
        return cls.from_crawler(crawler, *args, **kwargs)
    elif hasattr(cls, 'from_settings'):
        return cls.from_settings(settings, *args, **kwargs)
    else:
        return cls(*args, **kwargs)


async def run_in_thread_pool(func: Callable[..., Awaitable], *args: Any, **kwargs: Any):
    loop = asyncio.get_event_loop()
    if kwargs:
        func = functools.partial(func, **kwargs)
    return await loop.run_in_executor(None, func, *args)


async def wrapper_run_function(
        func: Union[Callable[..., T], Callable[..., Awaitable]],
        *args,
        **kwargs
):
    if asyncio.iscoroutinefunction(func):
        return await func(*args, **kwargs)
    else:
        return await run_in_thread_pool(func, *args, **kwargs)


class CallLateOnce:

    def __init__(self, func: Callable[..., Awaitable], *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs

        self._task: Optional[Task] = None

        self.loop = asyncio.get_event_loop()

    async def scheduler(self, delay: int = 0):
        if self._task is None:
            await asyncio.sleep(delay)
            self._task = self.loop.create_task(self())

    def cancel(self):
        if self._task:
            self._task.cancel()

    async def __call__(self):
        self._task = None
        await self.func(*self.args, **self.kwargs)
