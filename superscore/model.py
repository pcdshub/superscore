"""Classes for representing data"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Flag, IntEnum, auto
from typing import ClassVar, List, Optional, Set, Union
from uuid import UUID, uuid4

from superscore.serialization import as_tagged_union
from superscore.type_hints import AnyEpicsType
from superscore.utils import utcnow

logger = logging.getLogger(__name__)
_root_uuid = _root_uuid = UUID('a28cd77d-cc92-46cc-90cb-758f0f36f041')


class Severity(IntEnum):
    NO_ALARM = auto()
    MINOR = auto()
    MAJOR = auto()
    INVALID = auto()


class Status(IntEnum):
    NO_ALARM = auto()
    READ = auto()
    WRITE = auto()
    HIHI = auto()
    HIGH = auto()
    LOLO = auto()
    LOW = auto()
    STATE = auto()
    COS = auto()
    COMM = auto()
    TIMEOUT = auto()
    HWLIMIT = auto()
    CALC = auto()
    SCAN = auto()
    LINK = auto()
    SOFT = auto()
    BAD_SUB = auto()
    UDF = auto()
    DISABLE = auto()
    SIMM = auto()
    READ_ACCESS = auto()
    WRITE_ACCESS = auto()


class Tag(Flag):
    pass


@as_tagged_union
@dataclass
class Entry:
    """
    Base class for items in the data model
    """
    uuid: UUID = field(default_factory=uuid4)
    description: str = ''
    creation_time: datetime = field(default_factory=utcnow)


@dataclass
class Parameter(Entry):
    """An Entry that stores a PV name"""
    pv_name: str = ''
    abs_tolerance: Optional[float] = None
    rel_tolerance: Optional[float] = None
    readback: Optional[Parameter] = None
    read_only: bool = False


@dataclass
class Value(Entry):
    """An Entry that stores a PV name and data pair"""
    pv_name: str = ''
    data: Optional[AnyEpicsType] = None
    status: Status = Status.UDF
    severity: Severity = Severity.INVALID


@dataclass
class Setpoint(Value):
    """A Value that can be written to the EPICS environment"""
    readback: Optional[Readback] = None


@dataclass
class Readback(Value):
    """
    A read-only Value representing machine state that cannot be written to. A
    restore is considered complete when all Setpoint values are within
    tolerance of their Readback values.

    abs_tolerance - tolerance given in units matching the Setpoint
    rel_tolerance - tolerance given as a percentage
    timeout - time (seconds) after which a Setpoint restore is considered to
              have failed
    """
    abs_tolerance: Optional[float] = None
    rel_tolerance: Optional[float] = None
    timeout: Optional[float] = None


@dataclass
class Collection(Entry):
    """Nestable group of Parameters and Collections"""
    meta_pvs: ClassVar[List[Parameter]] = []
    all_tags: ClassVar[Set[Tag]] = set()

    title: str = ""
    children: List[Union[Parameter, Collection]] = field(default_factory=list)
    tags: Set[Tag] = field(default_factory=set)


@dataclass
class Snapshot(Entry):
    """
    Nestable group of Values and Snapshots.  Effectively a data-filled Collection
    """
    title: str = ""
    origin_collection: Optional[UUID] = None
    children: List[Union[Value, Snapshot]] = field(default_factory=list)
    tags: Set[Tag] = field(default_factory=set)
    meta_pvs: List[Value] = field(default_factory=list)


@dataclass
class Root:
    """Top level structure holding ``Entry``'s.  Denotes the top of the tree"""
    meta_id: UUID = _root_uuid
    entries: List[Entry] = field(default_factory=list)
