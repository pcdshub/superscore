"""
Base shim abstract base class
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from superscore.model import Severity, Status
from superscore.type_hints import AnyEpicsType
from superscore.utils import utcnow


class _BaseShim:
    async def get(self, address: str) -> AnyEpicsType:
        raise NotImplementedError

    async def put(self, address: str, value: Any):
        raise NotImplementedError

    def monitor(self, address: str, callback: Callable):
        raise NotImplementedError


@dataclass
class EpicsData:
    """Unified EPICS data type for holding data and relevant metadata"""
    data: AnyEpicsType
    status: Severity = Status.UDF
    severity: Status = Severity.INVALID
    timestamp: datetime = field(default_factory=utcnow)
