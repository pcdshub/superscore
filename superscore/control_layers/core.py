"""
Main control layer objects.  Exposes basic communication operations,
and dispatches to various shims depending on the context.
"""
import asyncio
from contextlib import suppress
from functools import singledispatchmethod
from typing import Any, Dict

from ._aioca import AiocaShim
from ._base_shim import _ShimBase


class ControlLayer:
    """
    Control Layer used to communicate with the control system, dispatching to
    whichever shim is relevant.
    """
    shims: Dict[str, _ShimBase]

    def __init__(self, *args, **kwargs):
        self.shims = {
            'ca': AiocaShim(),
        }

    def shim_from_pv(self, pv: str) -> _ShimBase:
        split = pv.split("://", 1)
        if len(split) > 1:
            # We got something like pva://mydevice, so use specified comms mode
            shim = self.shims.get(split[0], None)
        else:
            # No comms mode specified, use the default
            shim = list(self.shims.values())[0]

        if shim is None:
            raise ValueError(f"PV is of an unsupported protocol: {pv}")

        return shim

    @singledispatchmethod
    def get(self, pv):
        print(f"PV is of an unsupported type: {type(pv)}. Provide either "
              "a string or list of strings")

    @get.register
    def _(self, pv: str):
        return asyncio.run(self._get_one(pv))

    @get.register
    def _(self, pv: list):
        coros = []
        for p in pv:
            coros.append(self._get_one(p))

        loop = asyncio.get_event_loop()
        return loop.run_until_complete(asyncio.gather(*coros))

    async def _get_one(self, pv: str):
        shim = self.shim_from_pv(pv)
        return await shim.get(pv)

    @singledispatchmethod
    def put(self, pv, value: Any):
        print(f"PV is of an unsupported type: {type(pv)}. Provide either "
              "a string or list of strings")

    @put.register
    def _(self, pv: str, value: Any):
        return asyncio.run(self._put_one(pv, value))

    @put.register
    def _(self, pv: list, value: list, sequential: bool = False):
        coros = []
        for p, val in zip(pv, value):
            coros.append(self._put_one(p, val))

        loop = asyncio.get_event_loop()
        return loop.run_until_complete(asyncio.gather(*coros))

    async def _put_one(self, pv: str, value: Any):
        shim = self.shim_from_pv(pv)
        return await shim.put(pv, value)

    def subscribe(self, pv, cb):
        # Subscribes a callback to the PV address
        shim = self.shim_from_pv(pv)
        shim.monitor(pv, cb)

    def stop(self):
        # stop all currently running tasks.
        # TODO: make all tasks generated in superscore actually handle
        # CancelledError properly and clean up...
        loop = asyncio.get_event_loop()
        pending_tasks = asyncio.all_tasks(loop)
        for task in pending_tasks:
            task.cancel()
            with suppress(asyncio.CancelledError):
                loop.run_until_complete(task)
