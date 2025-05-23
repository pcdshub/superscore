"""
Base shim abstract base class
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional

from superscore.model import Severity, Status
from superscore.type_hints import AnyEpicsType
from superscore.utils import utcnow


class _BaseShim:
    async def get(self, address: str) -> EpicsData:
        raise NotImplementedError

    async def put(self, address: str, value: Any):
        raise NotImplementedError

    def monitor(self, address: str, callback: Callable):
        raise NotImplementedError


@dataclass
class EpicsData:
    """Unified EPICS data type for holding data and relevant metadata"""
    data: Optional[AnyEpicsType]
    status: Severity = Status.UDF
    severity: Status = Severity.INVALID
    timestamp: datetime = field(default_factory=utcnow)

    # Extra metadata
    units: Optional[str] = None
    precision: Optional[int] = None
    upper_ctrl_limit: Optional[float] = None
    lower_ctrl_limit: Optional[float] = None
    lower_alarm_limit: Optional[float] = None  # LOLO
    upper_alarm_limit: Optional[float] = None  # HIHI
    lower_warning_limit: Optional[float] = None  # LOW
    upper_warning_limit: Optional[float] = None  # HIGH
    enums: Optional[list[str]] = None
