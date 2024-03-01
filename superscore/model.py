"""
Dataclasses structures for data model.

All data objects inherit from Entry, which specifies common metadata
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import (Any, List, Sequence, Union, get_args, get_origin,
                    get_type_hints)
from uuid import UUID, uuid4

from apischema.validation import ValidationError, validate, validator

from superscore.serialization import as_tagged_union
from superscore.type_hints import AnyEpicsType

logger = logging.getLogger(__name__)
_root_uuid = UUID('a28cd77d-cc92-46cc-90cb-758f0f36f041')
_unset_data = object()
UNSET = 'unset'

# Essentially vendored from ophyd, but without array support.  Can expand to include
# numpy types later if needed
_data_type_map = {
    "number": (float,),
    "string": (str,),
    "integer": (int,),
    "boolean": (bool,)
}


@dataclass
@as_tagged_union
class Entry:
    """
    Base class for items in the data model.
    Holds common metadata and validation methods
    """
    meta_id: UUID = field(default_factory=uuid4)
    name: str = ''
    description: str = ''
    creation: datetime = field(default_factory=datetime.utcnow, compare=False)

    def validate(self) -> None:
        """
        Validate current values conform to type hints.
        Throws ValidationError on failure

        Parameters
        ----------
        recursive : bool, optional
            whether or not to validate, by default True
        """
        # apischema validates on deserialization, but we want to validate at runtime
        # Will gather @validator decorated methods.
        # Note this also runs on deserialization, for each Entry created
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
        Validate `self.{field_name}` matches type hint `hint`.
        Speciallized to the type hints present in this module,
        additions may require modification.

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
            else:
                origin = get_origin(hint)
                hint = get_args(hint)

            # end condition
            if origin is None:
                break

        if Any in get_args(hint):
            return
        if (origin is Union):
            inner_hint = get_args(hint)
        else:
            inner_hint = hint

        if is_list:
            list_comp = (isinstance(it, inner_hint) for it in field_value)
            if not all(list_comp):
                raise ValidationError(
                    f'improper type ({type(field_value)}) found in field '
                    f'(expecting {hint}])'
                )
        elif not isinstance(field_value, inner_hint):
            raise ValidationError(
                f'improper type ({type(field_value)}) found in field '
                f'(expecting {hint})'
            )


def data_type(data: Any):
    for type_name, data_type in _data_type_map.items():
        if isinstance(data, data_type):
            return type_name

    return UNSET


@dataclass
class Parameter(Entry):
    """An Entry that stores a PV name"""
    pv_name: str = ''
    read_only: bool = False


@dataclass
class Value(Parameter):
    """An Entry that stores a PV name and data pair"""
    data: AnyEpicsType = _unset_data
    data_type: str = 'unset'

    def __post_init__(self):
        # Cannot specify non-default arguments after default until 3.10 where
        # we can use @dataclass(kw_only=True).  Require them with post_init
        if self.data is not _unset_data:
            # attempt to cast
            self.data_type = data_type(self.data)

        if (self.data_type == 'unset'):
            raise TypeError('Value created without stored data and data type')

    @classmethod
    def from_parameter(cls, origin: Parameter, data: Any, data_type: str = UNSET):
        """Construct a Value from a parent Parameter"""
        return cls(
            pv_name=origin.pv_name,
            name=f'{origin.name} (value)',
            description=f'{origin.description} (value)',
            data=data,
            data_type=data_type,
            read_only=origin.read_only
        )


@dataclass
class Collection(Entry):
    """Group of Parameters and Collections (recursively)"""
    parameters: List[Union[UUID, Parameter]] = field(default_factory=list)
    collections: List[Union[UUID, Collection]] = field(default_factory=list)


@dataclass
class Snapshot(Entry):
    """
    Group of Values and Snapshots (recursively).
    Effectively a data-filled Collection
    """
    values: List[Union[UUID, Value]] = field(default_factory=list)
    snapshots: List[Union[UUID, Snapshot]] = field(default_factory=list)


@dataclass
class Root(Entry):
    """Base level structure holding Entry objects"""
    meta_id: UUID = _root_uuid
    entries: List[Entry] = field(default_factory=list)

    def validate(self):
        for entry in self.entries:
            entry.validate()
