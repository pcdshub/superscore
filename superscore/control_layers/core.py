"""
Main control layer objects.  Exposes basic communication operations,
and dispatches to various shims depending on the context.
"""
import asyncio
import logging
from functools import singledispatchmethod
from typing import Any, Callable, Dict, List, Optional, Union

from superscore.control_layers.status import TaskStatus

from ._aioca import AiocaShim
from ._base_shim import _BaseShim

logger = logging.getLogger(__name__)

# available communication shim layers
SHIMS = {
    'ca': AiocaShim()
}


class ControlLayer:
    """
    Control Layer used to communicate with the control system, dispatching to
    whichever shim is relevant.
    """
    shims: Dict[str, _BaseShim]

    def __init__(self, *args, shims: Optional[List[str]] = None, **kwargs):
        if shims is None:
            # load all available shims
            self.shims = SHIMS
            logger.debug('No shims specified, loading all available communication '
                         f'shims: {list(self.shims.keys())}')
        else:
            self.shims = {key: shim for key, shim in SHIMS.items() if key in shims}
            logger.debug('Loaded valid shims from the requested list: '
                         f'{list(self.shims.keys())}')

    def shim_from_pv(self, address: str) -> _BaseShim:
        """
        Determine the correct shim to use for the provided ``address``.
        ``address`` can optionally hold a protocol defining prefix such as "ca://" or
        "pva://".  If no prefix is provided, will select the first available shim.

        Parameters
        ----------
        address : str
            a PV address such as "MY:PREFIX:mtr1" or "pva://MY:PREFIX:dt"

        Returns
        -------
        _BaseShim
            The shim held by this ControlLayer for ``address``'s protocol

        Raises
        ------
        ValueError
            If address cannot be recognized or a matching shim cannot be found
        """
        split = address.split("://", 1)
        if len(split) > 1:
            # We got something like pva://mydevice, so use specified comms mode
            shim = self.shims.get(split[0], None)
        else:
            # No comms mode specified, use the default
            shim = list(self.shims.values())[0]

        if shim is None:
            raise ValueError(f"PV is of an unsupported protocol: {address}")

        return shim

    @singledispatchmethod
    def get(self, address: Union[str, list[str]]) -> Any:
        """
        Get the value(s) in ``address``.
        If a single pv is provided, will return a single value.
        If a list of pvs is provided, will get the values for each asynchronously.

        Parameters
        ----------
        address : Union[str, list[str]]
            The PV(s) to get values for.

        Returns
        -------
        Any
            The requested data
        """
        # Dispatches to _get_single and _get_list depending on type
        print(f"PV is of an unsupported type: {type(address)}. Provide either "
              "a string or list of strings")

    @get.register
    def _get_single(self, address: str) -> Any:
        """Synchronously get a single ``address``"""
        return asyncio.run(self._get_one(address))

    @get.register
    def _get_list(self, address: list) -> Any:
        """Synchronously get a list of ``address``"""
        async def gathered_coros():
            coros = []
            for p in address:
                coros.append(self._get_one(p))
            return await asyncio.gather(*coros)

        return asyncio.run(gathered_coros())

    async def _get_one(self, address: str):
        """
        Base async get function.  Use this to construct higher-level get methods
        """
        shim = self.shim_from_pv(address)
        return await shim.get(address)

    @singledispatchmethod
    def put(
        self,
        address: Union[str, list[str]],
        value: Union[Any, list[Any]],
        cb: Optional[Union[Callable, list[Callable]]] = None
    ) -> Union[TaskStatus, list[TaskStatus]]:
        """
        Put ``value`` to ``address``
        If ``address`` is a list, ``value`` and ``cb`` must be lists of equal length

        Parameters
        ----------
        address : Union[str, list[str]]
            The PV(s) to put ``values`` to
        value : Union[Any, list[Any]]
            The value(s) to put to the ``address``
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
        print(f"PV is of an unsupported type: {type(address)}. Provide either "
              "a string or list of strings")

    @put.register
    def _put_single(
        self,
        address: str,
        value: Any,
        cb: Optional[Callable] = None
    ) -> TaskStatus:
        """Synchronously put ``value`` to ``address``, running ``cb`` on completion"""
        async def status_coro():
            status = self._put_one(address, value)
            if cb is not None:
                status.add_callback(cb)
            await asyncio.gather(status, return_exceptions=True)
            return status

        return asyncio.run(status_coro())

    @put.register
    def _put_list(
        self,
        address: list,
        value: list,
        cb: Optional[list[Callable]] = None
    ) -> list[TaskStatus]:
        """
        Synchronously put ``value`` to ``address``, running ``cb`` on completion.
        All arguments must be of equal length.
        """
        if cb is None:
            cb_length = len(address)
        else:
            cb_length = len(cb)

        if not (len(address) == len(value) == cb_length):
            raise ValueError(
                'Arguments are of different length: '
                f'addresses({len(address)}), values({len(value)}), cbs({len(cb)})'
            )

        async def status_coros():
            statuses = []
            if cb is None:
                callbacks = [None for _ in range(len(address))]
            else:
                callbacks = cb

            for p, val, c in zip(address, value, callbacks):
                status = self._put_one(p, val)
                if c is not None:
                    status.add_callback(c)

                statuses.append(status)
            await asyncio.gather(*statuses, return_exceptions=True)
            return statuses

        return asyncio.run(status_coros())

    @TaskStatus.wrap
    async def _put_one(self, address: str, value: Any):
        """
        Base async put function.  Use this to construct higher-level put methods
        """
        shim = self.shim_from_pv(address)
        await shim.put(address, value)

    def subscribe(self, address: str, cb: Callable):
        """Subscribes a callback (``cb``) to the provide address (``address``)"""
        shim = self.shim_from_pv(address)
        shim.monitor(address, cb)
