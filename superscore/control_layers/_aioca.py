"""
Control layer shim for communicating asynchronously through channel access
"""
from typing import Any, Callable

from aioca import caget, camonitor, caput

from superscore.control_layers._base_shim import _BaseShim


class AiocaShim(_BaseShim):
    # TODO: consider handling datatype arguments in caput/get
    # TODO: wrap CANothing results into unified status object
    async def get(self, address: str):
        return await caget(address)

    async def put(self, address: str, value: Any):
        await caput(address, value)

    def monitor(self, address: str, callback: Callable):
        camonitor(address, callback)
