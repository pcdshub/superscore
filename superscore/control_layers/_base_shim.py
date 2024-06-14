"""
Base shim abstract base class
"""
from typing import Any, Callable


class _BaseShim:
    async def get(self, address: str):
        raise NotImplementedError

    async def put(self, address: str, value: Any):
        raise NotImplementedError

    def monitor(self, address: str, callback: Callable):
        raise NotImplementedError
