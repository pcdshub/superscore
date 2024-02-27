"""
Dataclasses structures for data model.

All data objects inherit from Entry, which specifies common metadata
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import (Any, List, Optional, Sequence, Union, get_args, get_origin,
                    get_type_hints)
from uuid import UUID, uuid4

from apischema.validation import ValidationError, validate, validator

from superscore.type_hints import AnyEpicsType

logger = logging.getLogger(__name__)
_default_uuid = 'd3c8b6b8-7d4d-47aa-bb55-ba9c1b99bd9e'


@dataclass
class Entry:
    """
    Base class for items in the data model.
    Holds common metadata and validation methods
    """
    meta_id: UUID = field(default_factory=uuid4)
    name: str = ''
    description: str = ''
    creation: datetime = field(default_factory=datetime.utcnow, compare=False)

    def validate(self, recursive: bool = True) -> None:
        """
        Validate current values conform to type hints.  Throws ValidationError on failure

        Parameters
        ----------
        recursive : bool, optional
            whether or not to validate , by default True
        """
        # apischema validates on deserialization, but we want to validate at runtime
        # Will gather validator decorated methods
        validate(self)

    @validator
    def validate_types(self):
        """validate any types inheriting from Entry are valid"""
        # This probably could just use typeguard, but let's see if I can do it
        hint_dict = get_type_hints(type(self))

        for field_name, hint in hint_dict.items():
            self.validate_field(field_name, hint)

    def validate_field(self, field_name: str, hint: Any) -> None:
        """
        Validate `self.{field_name}` matches type hint `hint`

        Parameters
        ----------
        field_name : str
            the name of the field on self
        hint : Any
            the type hint we expect `self.{field_name}` to match

        Raises
        ------
        ValidationError
            if a type mismatch is found
        """
        field_value = getattr(self, field_name)
        origin = get_origin(hint)
        is_list = False

        while origin:  # Drill down through nested types, only Lists currently
            if origin is Union:
                break
            elif origin in (list, Sequence):
                hint = get_args(hint)[0]  # Lists only have one type
                origin = get_origin(hint)
                is_list = True
                # Mark list and check each entry in list
            else:
                origin = get_origin(hint)
                hint = get_args(hint)

            # end condition
            if origin is None:
                break

        if Any in get_args(hint):
            return
        elif (origin is None):
            if not isinstance(field_value, hint):
                raise ValidationError('improper type found in field')
        elif (origin is Union) and (UUID in get_args(hint)):
            # Case of interest.   A hint of Union[UUID, SomeType]
            if is_list:
                list_comp = (isinstance(it, get_args(hint)) for it in field_value)
                if not all(list_comp):
                    raise ValidationError('improper type in list-field')
            elif not isinstance(field_value, get_args(hint)):
                raise ValidationError('improper type found in field')


@dataclass
class Parameter(Entry):
    """An Entry that stores a PV name"""
    pv_name: str = ''
    read_only: bool = False


@dataclass
class Value(Entry):
    """
    An Entry that attaches a piece of data to a Parameter.
    Can be thought of a PV - data pair
    """
    data: AnyEpicsType = ''
    origin: Union[UUID, Parameter] = _default_uuid

    def __post_init__(self):
        if self.origin is _default_uuid:
            raise TypeError("__init__ missing required argument: 'origin'")

    @classmethod
    def from_origin(cls, origin: Parameter, data: Optional[AnyEpicsType] = None) -> Value:
        """
        Create a Value from its originating Parameter and corresponding `data`
        Note that the returned Value may not be valid.

        Parameters
        ----------
        origin : Parameter
            the parameter used to
        data : Optional[AnyEpicsType]
            The data read from the Parameter - `origin`

        Returns
        -------
        Value
            A filled and valid Value object
        """
        new_value = cls(
            name=origin.name + '_value',
            description=f'Value generated from {origin.name}',
            origin=origin
        )

        if data is not None:
            new_value.data = data

        return new_value


@dataclass
class Collection(Entry):
    parameters: List[Union[UUID, Parameter]] = field(default_factory=list)
    collections: List[Union[UUID, Collection]] = field(default_factory=list)


@dataclass
class Snapshot(Entry):
    origin: Union[UUID, Collection] = _default_uuid

    values: List[Union[UUID, Value]] = field(default_factory=list)
    snapshots: List[Union[UUID, Snapshot]] = field(default_factory=list)

    def __post_init__(self):
        if self.origin is _default_uuid:
            raise TypeError("__init__ missing required argument: 'origin'")

    @classmethod
    def from_origin(
        cls,
        origin: Collection,
        values: Optional[List[Union[UUID, Value]]] = None,
        snapshots: Optional[List[Union[UUID, Snapshot]]] = None
    ) -> Snapshot:
        """
        Create a Snapshot from its originating Collection.
        Note that the returned Snapshot may not be valid.

        Parameters
        ----------
        origin : Collection
            the Collection used to define this Snapshot

        Returns
        -------
        Snapshot
            A filled and valid Snapshot object
        """
        new_snap = cls(
            name=origin.name + '_snapshot',
            description=f'Snapshot generated from {origin.name}',
            origin=origin
        )

        if values is not None:
            new_snap.values = values

        if snapshots is not None:
            new_snap.snapshots = snapshots

        return new_snap

    @validator
    def validate_tree(self) -> None:
        """Validate the values and snapshots match those specified in origin"""
        # TODO: complete this method
        return


@dataclass
class Root:
    """Base level structure holding Entry objects"""
    entries: List[Entry] = field(default_factory=list)

    def validate(self):
        for entry in self.entries:
            entry.validate()
