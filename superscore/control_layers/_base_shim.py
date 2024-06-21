"""
Base shim abstract base class
"""
from typing import Any, Callable

from superscore.type_hints import AnyEpicsType


class _BaseShim:
    async def get(self, address: str) -> AnyEpicsType:
        raise NotImplementedError

    async def put(self, address: str, value: Any):
        raise NotImplementedError

    def monitor(self, address: str, callback: Callable):
        raise NotImplementedError
