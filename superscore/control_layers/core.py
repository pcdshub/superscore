"""
Main control layer objects.  Exposes basic communication operations,
and dispatches to various shims depending on the context.
"""
import asyncio
from functools import singledispatchmethod
from typing import Any, Callable, Dict, Optional, Union

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
        """
        Determine the correct shim to use for the provided ``pv``.
        ``pv`` can optionally hold a protocol defining prefix such as "ca://" or
        "pva://".  If no prefix is provided, will select the first available shim.

        Parameters
        ----------
        pv : str
            a PV address such as "MY:PREFIX:mtr1" or "pva://MY:PREFIX:dt"

        Returns
        -------
        _BaseShim
            The shim held by this ControlLayer for ``pv``'s protocol

        Raises
        ------
        ValueError
            If pv cannot be recognized or a matching shim cannot be found
        """
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
    def get(self, pv: Union[str, list[str]]) -> Any:
        """
        Get the value(s) in ``pv``.
        If a single pv is provided, will return a single value.
        If a list of pvs is provided, will get the values for each asynchronously.

        Parameters
        ----------
        pv : Union[str, list[str]]
            The PV(s) to get values for.

        Returns
        -------
        Any
            The requested data
        """
        # Dispatches to _get_single and _get_list depending on type
        print(f"PV is of an unsupported type: {type(pv)}. Provide either "
              "a string or list of strings")

    @get.register
    def _get_single(self, pv: str) -> Any:
        """Synchronously get a single ``pv``"""
        return asyncio.run(self._get_one(pv))

    @get.register
    def _get_list(self, pv: list) -> Any:
        """Synchronously get a list of ``pv``"""
        async def gathered_coros():
            coros = []
            for p in pv:
                coros.append(self._get_one(p))
            return await asyncio.gather(*coros)

        return asyncio.run(gathered_coros())

    async def _get_one(self, pv: str):
        """
        Base async get function.  Use this to construct higher-level get methods
        """
        shim = self.shim_from_pv(pv)
        return await shim.get(pv)

    @singledispatchmethod
    def put(
        self,
        pv: Union[str, list[str]],
        value: Union[Any, list[Any]],
        cb: Optional[Callable] = None
    ) -> Union[TaskStatus, list[TaskStatus]]:
        """
        Put ``value`` to ``pv``
        If ``pv`` is a list, ``value`` and ``cb`` must be lists of equal length

        Parameters
        ----------
        pv : Union[str, list[str]]
            The PV(s) to put ``values`` to
        value : Union[Any, list[Any]]
            The value(s) to put to the ``pv``
        cb : Optional[Callable], by default None
            Callbacks to run on completion of the put task.
            Callbacks will be called with the associated TaskStatus as its
            sole argument

        Returns
        -------
        Union[TaskStatus, list[TaskStatus]]
            The TaskStatus object(s) for the put operation
        """
        # Dispatches to _put_single and _put_list depending on type
        print(f"PV is of an unsupported type: {type(pv)}. Provide either "
              "a string or list of strings")

    @put.register
    def _put_single(
        self,
        pv: str,
        value: Any,
        cb: Optional[Callable] = None
    ) -> TaskStatus:
        """Synchronously put ``value`` to ``pv``, running ``cb`` on completion"""
        async def status_coro():
            status = self._put_one(pv, value)
            if cb is not None:
                status.add_callback(cb)
            await status.task
            return status

        return asyncio.run(status_coro())

    @put.register
    def _put_list(
        self,
        pv: list,
        value: list,
        cb: Optional[list[Callable]] = None
    ) -> list[TaskStatus]:
        """
        Synchronously put ``value`` to ``pv``, running ``cb`` on completion.
        All arguments must be of equal length.
        """
        if cb is None:
            cb_length = len(pv)
        else:
            cb_length = len(cb)

        if not (len(pv) == len(value) == cb_length):
            raise ValueError(
                'Arguments are of different length: '
                f'pvs({len(pv)}), values({len(value)}), cbs({len(cb)})'
            )

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
        """
        Base async get function.  Use this to construct higher-level get methods
        """
        shim = self.shim_from_pv(pv)
        await shim.put(pv, value)

    def subscribe(self, pv: str, cb: Callable):
        """Subscribes a callback (``cb``) to the provide address (``pv``)"""
        shim = self.shim_from_pv(pv)
        shim.monitor(pv, cb)
