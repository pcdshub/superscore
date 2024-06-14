"""
Control layer shim for communicating asynchronously through channel access
"""
import logging
from typing import Any, Callable

from aioca import CANothing, caget, camonitor, caput

from superscore.control_layers._base_shim import _BaseShim
from superscore.errors import CommunicationError

logger = logging.getLogger(__name__)


class AiocaShim(_BaseShim):
    async def get(self, address: str):
        try:
            return await caget(address)
        except CANothing as ex:
            logger.debug(f"CA get failed {ex.__repr__()}")
            raise CommunicationError(f'CA get failed for {ex}')

    async def put(self, address: str, value: Any):
        try:
            await caput(address, value)
        except CANothing as ex:
            logger.debug(f"CA put failed {ex.__repr__()}")
            raise CommunicationError(f'CA put failed for {ex}')

    def monitor(self, address: str, callback: Callable):
        camonitor(address, callback)
