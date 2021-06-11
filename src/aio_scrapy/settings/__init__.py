import copy
import json
from collections.abc import MutableMapping
from enum import IntEnum
from importlib import import_module
from typing import Any, Dict, Iterator, Optional, Union

from aio_scrapy.settings import default_settings


class SettingsPriorities(IntEnum):
    default = 0
    command = 10
    project = 20
    spider = 30
    cmdline = 40


def get_settings_priority(priority: Union[str, int]) -> int:
    if isinstance(priority, str):
        return SettingsPriorities[priority]
    if isinstance(property, int):
        return SettingsPriorities(priority)


class SettingsAttribute:
    def __init__(self, value: Any, priority: int):
        self.value: Any = value
        if isinstance(self.value, BaseSettings):
            self.priority = max(self.value.max_priority(), priority)
        else:
            self.priority = priority

    def set(self, value: Any, priority: Union[str, int]):
        if priority >= self.priority:
            if isinstance(self.value, BaseSettings):
                value = BaseSettings(value, priority=priority)
            self.value = value
            self.priority = priority

    def __str__(self):
        return f"<SettingsAttribute value={self.value!r} priority={self.priority}>"

    __repr__ = __str__


class BaseSettings(MutableMapping):

    def __init__(self, values: Any = None, priority: Union[str, int] = 'project'):
        self.frozen = False
        self.attributes: Dict[str, SettingsAttribute] = {}
        self.update(values, priority)

    def __contains__(self, name: str):
        return name in self.attributes

    def __setitem__(self, name: str, value: Any) -> None:
        self.set(name, value)

    def __delitem__(self, name: str) -> None:
        self._assert_mutability()
        del self.attributes[name]

    def __getitem__(self, name: str) -> Any:
        attribute = self.attributes.get(name)
        if attribute:
            return attribute.value

    def __len__(self) -> int:
        return len(self.attributes)

    def __iter__(self) -> Iterator[str]:
        return iter(self.attributes)

    def copy(self) -> 'BaseSettings':
        return copy.deepcopy(self)

    def freeze(self) -> None:
        self.frozen = True

    def frozen_copy(self):
        _copy = self.copy()
        _copy.freeze()
        return copy

    def get_priority(self, name: str) -> Optional[int]:
        if name not in self:
            return None
        return self.attributes[name].priority

    def update(self, values: Any, priority: Union[str, int] = 'project') -> None:
        self._assert_mutability()
        if isinstance(values, str):
            values = json.loads(values)
        if values is not None:
            if isinstance(values, BaseSettings):
                for name, value in values.items():
                    self.set(name, value, values.get_priority(name))
            else:
                for name, value in values.items():
                    self.set(name, value, priority)

    def set(self, name: str, value: Any, priority: Union[str, int] = 'project') -> None:
        self._assert_mutability()
        priority: int = get_settings_priority(priority)
        if name not in self:
            if isinstance(value, SettingsAttribute):
                self.attributes[name] = value
            else:
                self.attributes[name] = SettingsAttribute(value, priority)
        else:
            self.attributes[name].set(value, priority)

    def _assert_mutability(self):
        if self.frozen:
            raise TypeError("Trying to modify an immutable Settings object")

    def max_priority(self) -> int:
        if len(self) > 0:
            return max(self.get_priority(name) for name in self)
        return get_settings_priority(priority='default')

    def setup_module(self, module: Any, priority: Union[str, int] = 'project'):
        self._assert_mutability()
        if isinstance(module, str):
            module = import_module(module)
        for key in dir(module):
            if key.isupper():
                self.set(key, getattr(module, key), priority)

    def _to_dict(self):
        return {k: (v._to_dict() if isinstance(v, BaseSettings) else v) for k, v in self.items()}


class Settings(BaseSettings):

    def __init__(self, values: Any = None, priority: Union[str, int] = 'project'):
        super().__init__()

        self.setup_module(module=default_settings, priority='default')

        for name, val in self.items():
            if isinstance(val, dict):
                self.set(name, BaseSettings(val, 'default'), 'default')
        self.update(values, priority)
