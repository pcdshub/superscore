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
            value_time = await caget(address, format=dbr.FORMAT_TIME)
            value_ctrl = await caget(address, format=dbr.FORMAT_CTRL)
        except CANothing as ex:
            logger.debug(f"CA get failed {ex.__repr__()}")
            raise CommunicationError(f'CA get failed for {ex}')

        return self.value_to_epics_data(value_time, value_ctrl)

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
    def value_to_epics_data(
        value_time: AugmentedValue, value_ctrl: AugmentedValue
    ) -> EpicsData:
        """
        Creates an EpicsData instance from an aioca provided AugmentedValue
        Assumes the AugmentedValue's are collected with FORMAT_TIME and
        FORMAT_CTRL qualifier.  AugmentedValue subclasses primitive datatypes,
        so they can be used as data directly.

        Parameters
        ----------
        value_time : AugmentedValue
            A value collected with dbr.FORMAT_TIME
        value_ctrl : AugmentedValue
            A value collected with dbr.FORMAT_CTRL

        Returns
        -------
        EpicsData
            The filled EpicsData instance
        """
        severity = Severity(value_time.severity)
        status = Status(value_time.status)
        timestamp = value_time.timestamp

        units = getattr(value_ctrl, "units", None)
        precision = getattr(value_ctrl, "precision", None)
        upper_ctrl_limit = getattr(value_ctrl, "upper_ctrl_limit", None)
        lower_ctrl_limit = getattr(value_ctrl, "lower_ctrl_limit", None)
        lower_alarm_limit = getattr(value_ctrl, "lower_alarm_limit", None)
        upper_alarm_limit = getattr(value_ctrl, "upper_alarm_limit", None)
        lower_warning_limit = getattr(value_ctrl, "lower_warning_limit", None)
        upper_warning_limit = getattr(value_ctrl, "upper_warning_limit", None)
        enums = getattr(value_ctrl, "enums", None)

        return EpicsData(
            data=+value_time,  # from aioca docs, +AugmentedValue strips augmentation
            status=status,
            severity=severity,
            timestamp=timestamp,
            units=units,
            precision=precision,
            upper_ctrl_limit=upper_ctrl_limit,
            lower_ctrl_limit=lower_ctrl_limit,
            lower_alarm_limit=lower_alarm_limit,
            upper_alarm_limit=upper_alarm_limit,
            lower_warning_limit=lower_warning_limit,
            upper_warning_limit=upper_warning_limit,
            enums=enums,
        )
