"""Classes for representing data"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Flag, IntEnum, auto
from typing import ClassVar, List, Optional, Set, Union
from uuid import UUID, uuid4

import apischema

from superscore.serialization import as_tagged_union
from superscore.type_hints import AnyEpicsType
from superscore.utils import utcnow

logger = logging.getLogger(__name__)
_root_uuid = _root_uuid = UUID("a28cd77d-cc92-46cc-90cb-758f0f36f041")


class Severity(IntEnum):
    NO_ALARM = 0
    MINOR = auto()
    MAJOR = auto()
    INVALID = auto()


class Status(IntEnum):
    NO_ALARM = 0
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
    description: str = ""
    creation_time: datetime = field(default_factory=utcnow)

    def __post_init__(self) -> None:
        if isinstance(self.uuid, str):
            self.uuid = UUID(self.uuid)
        return

    def swap_to_uuids(self) -> List[Union[Entry, UUID]]:
        """
        Swap to UUID references where relevant.

        Returns a list of objects referenced by this Entry,
        either an Entry's that has been swapped to UUIDs,
        or a UUID if it was already filled with a UUID.
        """
        return []

    def validate(self, toplevel: bool = True) -> bool:
        """
        Ensures Entry is properly formed.

        Raises apischema.ValidationError if type checking fails during
        deserialization
        """
        if toplevel:
            try:
                serial = apischema.serialize(self)
                apischema.deserialize(type(self), serial)
                return True
            except apischema.ValidationError:
                return False
        else:
            return True


@dataclass
class Parameter(Entry):
    """An Entry that stores a PV name"""
    pv_name: str = ""
    abs_tolerance: Optional[float] = None
    rel_tolerance: Optional[float] = None
    readback: Optional[Parameter] = None
    read_only: bool = False

    def validate(self, toplevel: bool = True) -> bool:
        readback_is_valid = self.readback is None or self.readback.validate(toplevel=False)
        return readback_is_valid and super().validate(toplevel=toplevel)

    def accept(self, visitor) -> None:
        visitor.visitParameter(self)
        if self.readback is not None:
            visitor.visit(self.readback)


@dataclass
class Setpoint(Entry):
    """A Value that can be written to the EPICS environment"""
    pv_name: str = ""
    data: Optional[AnyEpicsType] = None
    status: Status = Status.UDF
    severity: Severity = Severity.INVALID
    readback: Optional[Readback] = None

    @classmethod
    def from_parameter(
        cls,
        origin: Parameter,
        data: AnyEpicsType,
        status: Status = Status.UDF,
        severity: Severity = Severity.INVALID,
    ) -> Setpoint:

        return cls(
            pv_name=origin.pv_name,
            data=data,
            status=status,
            severity=severity,
            readback=origin.readback,
        )

    def validate(self, toplevel: bool = True) -> bool:
        readback_is_valid = self.readback is None or self.readback.validate(toplevel=False)
        return readback_is_valid and super().validate(toplevel=toplevel)

    def accept(self, visitor) -> None:
        visitor.visitSetpoint(self)
        if self.readback is not None:
            visitor.visit(self.readback)


@dataclass
class Readback(Entry):
    """
    A read-only Value representing machine state that cannot be written to. A
    restore is considered complete when all Setpoint values are within
    tolerance of their Readback values.

    abs_tolerance - tolerance given in units matching the Setpoint
    rel_tolerance - tolerance given as a percentage
    timeout - time (seconds) after which a Setpoint restore is considered to
              have failed
    """
    pv_name: str = ""
    data: Optional[AnyEpicsType] = None
    status: Status = Status.UDF
    severity: Severity = Severity.INVALID
    abs_tolerance: Optional[float] = None
    rel_tolerance: Optional[float] = None
    timeout: Optional[float] = None

    @classmethod
    def from_parameter(
        cls,
        origin: Parameter,
        data: AnyEpicsType,
        status: Status = Status.UDF,
        severity: Severity = Severity.INVALID,
        timeout: Optional[float] = None,
    ) -> Readback:

        return cls(
            pv_name=origin.pv_name,
            data=data,
            status=status,
            severity=severity,
            abs_tolerance=origin.abs_tolerance,
            rel_tolerance=origin.rel_tolerance,
            timeout=timeout,
        )

    def accept(self, visitor) -> None:
        visitor.visitReadback(self)


class Nestable:
    """Mix-in class that provides methods for nested container Entries"""
    def validate(self, toplevel: bool = True):
        """
        Validates self and all children. If toplevel, also validates structure
        of the Entry tree. This avoids redundant work by only performing tree-
        level validation once.

        Overrides Entry.validate().
        """
        tree_is_valid = not toplevel or (not self.has_cycle() and super().validate(toplevel=True))
        return tree_is_valid and all(child.validate(toplevel=False) for child in self.children)

    def has_cycle(self, parents=None) -> bool:
        if parents is None:
            parents = frozenset()

        if self.uuid in parents:
            return True
        else:
            parents_including_self = parents | {self.uuid}
            for child in self.children:
                if isinstance(child, type(self)) and child.has_cycle(parents=parents_including_self):
                    return True
            return False


@dataclass
class Collection(Nestable, Entry):
    """Nestable group of Parameters and Collections"""
    meta_pvs: ClassVar[List[Parameter]] = []
    all_tags: ClassVar[Set[Tag]] = set()

    title: str = ""
    children: List[Union[UUID, Parameter, Collection]] = field(default_factory=list)
    tags: Set[Tag] = field(default_factory=set)

    def swap_to_uuids(self) -> List[Entry]:
        ref_list = []

        new_children = []
        for child in self.children:
            if isinstance(child, Entry):
                uuid_ref = child.uuid
            else:
                uuid_ref = child

            new_children.append(uuid_ref)
            ref_list.append(child)

        self.children = new_children
        return ref_list

    def accept(self, visitor) -> None:
        visitor.visitCollection(self)
        for entry in self.children:
            visitor.visit(entry)


@dataclass
class Snapshot(Nestable, Entry):
    """
    Nestable group of Values and Snapshots.  Effectively a data-filled Collection
    """
    title: str = ""
    origin_collection: Optional[Union[UUID, Collection]] = None
    children: List[Union[UUID, Readback, Setpoint, Snapshot]] = field(
        default_factory=list
    )
    tags: Set[Tag] = field(default_factory=set)
    meta_pvs: List[Readback] = field(default_factory=list)

    def swap_to_uuids(self) -> List[Union[Entry, UUID]]:
        ref_list = []

        if isinstance(self.origin_collection, Entry):
            ref_list.append(self.origin_collection)

            origin_ref = self.origin_collection.uuid
            self.origin_collection = origin_ref

        new_children = []
        for child in self.children:
            if isinstance(child, Entry):
                uuid_ref = child.uuid
            else:
                uuid_ref = child

            new_children.append(uuid_ref)
            ref_list.append(child)

        self.children = new_children

        return ref_list

    def accept(self, visitor) -> None:
        visitor.visitSnapshot(self)
        for entry in self.children:
            visitor.visit(entry)


@dataclass
class Root:
    """Top level structure holding ``Entry``'s.  Denotes the top of the tree"""
    meta_id: UUID = _root_uuid
    entries: List[Entry] = field(default_factory=list)

    def accept(self, visitor) -> None:
        visitor.visitRoot(self)
        for entry in self.entries:
            visitor.visit(entry)
