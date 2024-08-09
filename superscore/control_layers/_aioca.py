"""
Control layer shim for communicating asynchronously through channel access
"""
import logging
from typing import Any, Callable

from aioca import CANothing, caget, camonitor, caput
from aioca.types import AugmentedValue
from epicscorelibs.ca import dbr

from superscore.control_layers._base_shim import EpicsData, _BaseShim
from superscore.errors import CommunicationError
from superscore.model import Severity, Status

logger = logging.getLogger(__name__)


class AiocaShim(_BaseShim):
    """async compatible EPICS channel access shim layer"""
    async def get(self, address: str) -> EpicsData:
        """
        Get the value at the PV: ``address``.

        Parameters
        ----------
        address : str
            The PV to caget.

        Returns
        -------
        EpicsData
            The data at ``address``.

        Raises
        ------
        CommunicationError
            If the caget operation fails for any reason.
        """
        try:
            value = await caget(address, format=dbr.FORMAT_TIME)
        except CANothing as ex:
            logger.debug(f"CA get failed {ex.__repr__()}")
            raise CommunicationError(f'CA get failed for {ex}')

        return self.value_to_epics_data(value)

    async def put(self, address: str, value: Any) -> None:
        """
        Put ``value`` to the PV ``address``.

        Parameters
        ----------
        address : str
            The PV to put ``value`` to.
        value : Any
            Value to put to ``address``.

        Raises
        ------
        CommunicationError
            If the caput operation fails for any reason.
        """
        try:
            await caput(address, value)
        except CANothing as ex:
            logger.debug(f"CA put failed {ex.__repr__()}")
            raise CommunicationError(f'CA put failed for {ex}')

    def monitor(self, address: str, callback: Callable) -> None:
        """
        Subscribe ``callback`` to updates on the PV ``address``.

        Parameters
        ----------
        address : str
            The PV to monitor.
        callback : Callable
            The callback to run on updates to ``address``
        """
        camonitor(address, callback)

    @staticmethod
    def value_to_epics_data(value: AugmentedValue) -> EpicsData:
        """
        Creates an EpicsData instance from an aioca provided AugmentedValue
        Assumes the augmented value was collected with FORMAT_TIME qualifier.
        AugmentedValue subclasses primitive datatypes, so they can be used as
        data directly.

        Parameters
        ----------
        value : AugmentedValue
            The value to repackage

        Returns
        -------
        EpicsData
            The filled EpicsData instance
        """
        severity = Severity(value.severity)
        status = Status(value.status)
        timestamp = value.timestamp

        return EpicsData(
            data=value,
            status=status,
            severity=severity,
            timestamp=timestamp
        )
