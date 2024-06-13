"""
Main control layer objects.  Exposes basic communication operations,
and dispatches to various shims depending on the context.
"""
import asyncio
from functools import singledispatchmethod
from typing import Any, Callable, Dict, Optional

from superscore.control_layers.status import TaskStatus

from ._aioca import AiocaShim
from ._base_shim import _BaseShim


class ControlLayer:
    """
    Control Layer used to communicate with the control system, dispatching to
    whichever shim is relevant.
    """
    shims: Dict[str, _BaseShim]

    def __init__(self, *args, **kwargs):
        self.shims = {
            'ca': AiocaShim(),
        }

    def shim_from_pv(self, pv: str) -> _BaseShim:
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
    def put(self, pv, value: Any, cb: Optional[Callable]):
        print(f"PV is of an unsupported type: {type(pv)}. Provide either "
              "a string or list of strings")

    @put.register
    def _(self, pv: str, value: Any, cb: Optional[Callable] = None):
        async def status_coro():
            status = self._put_one(pv, value)
            if cb is not None:
                status.add_callback(cb)
            await status.task
            return status

        return asyncio.run(status_coro())

    @put.register
    def _(self, pv: list, value: list, cb: Optional[list[Callable]] = None):

        async def status_coros():
            statuses = []
            if cb is None:
                callbacks = [None for _ in range(len(pv))]
            else:
                callbacks = cb

            for p, val, c in zip(pv, value, callbacks):
                status = self._put_one(p, val)
                if c is not None:
                    status.add_callback(c)

                statuses.append(status)
            await asyncio.gather(*[s.task for s in statuses])
            return statuses

        return asyncio.run(status_coros())

    @TaskStatus.wrap
    async def _put_one(self, pv: str, value: Any):
        shim = self.shim_from_pv(pv)
        await shim.put(pv, value)

    def subscribe(self, pv, cb):
        # Subscribes a callback to the PV address
        shim = self.shim_from_pv(pv)
        shim.monitor(pv, cb)
