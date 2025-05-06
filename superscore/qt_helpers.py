"""
Helper QObject classes for managing dataclass instances.

Contains utilities for synchronizing dataclass instances between
widgets.
"""
from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import (Any, ClassVar, Dict, List, Optional, Set, Type, Union,
                    get_args, get_origin, get_type_hints)

from qtpy.QtCore import QObject
from qtpy.QtCore import Signal as QSignal

logger = logging.getLogger(__name__)


class QDataclassBridge(QObject):
    """
    Convenience structure for managing a dataclass along with qt.

    Once created, you can navigate this object much like it was the
    dataclass. For example:

    @dataclass
    def my_class:
        field: int
        others: list[OtherClass]

    Would allow you to access:
    bridge.field.put(3)
    bridge.field.changed_value.connect(my_slot)
    bridge.others.append(OtherClass(4))

    This does not recursively dive down the tree of subdataclasses.
    For these, we need to make multiple bridges.

    Parameters
    ----------
    data : any dataclass
        The dataclass we want to bridge to
    """
    data: Any

    def __init__(self, data: Any, parent: Optional[QObject] = None):
        super().__init__(parent=parent)
        self.data = data
        fields = get_type_hints(type(data))
        for name, type_hint in fields.items():
            self.set_field_from_data(name, type_hint, data)

    def set_field_from_data(
        self,
        name: str,
        type_hint: Any,
        data: Any,
        optional: bool = False
    ):
        """
        Set a field for this bridge based on the data and its type

        Parameters
        ----------
        name : str
            name of the field
        type_hint : Any
            The type hint annotation, returned from typing.get_type_hints
        data : any
            The dataclass for this bridge
        """
        # Need to figure out which category this is:
        # 1. Primitive value -> make a QDataclassValue
        # 2. Another dataclass -> make a QDataclassValue (object)
        # 3. A list of values -> make a QDataclassList
        # 4. A list of dataclasses -> QDataclassList (object)
        origin = get_origin(type_hint)
        args = get_args(type_hint)

        if not origin:
            # a raw type, no Union, Optional, etc
            NestedClass = QDataclassValue
            dtype = type_hint
        elif origin is dict:
            # Use dataclass value and override to object type
            NestedClass = QDataclassValue
            dtype = object
        elif origin in (list, Sequence):
            # Make sure we have list manipulation methods
            # Sequence resolved as from collections.abc (even if defined from typing)
            NestedClass = QDataclassList
            dtype = args[0]
        elif origin is set:
            NestedClass = QDataclassSet
            dtype = args[0]
        elif (origin is Union) and (type(None) in args):
            # Optional, need to allow NoneType to be emitted by changed_value signal
            if len(args) > 2:
                # Optional + many other types, dispatch to complex Union case
                self.set_field_from_data(name, args[:-1], data, optional=True)
            else:
                self.set_field_from_data(name, args[0], data, optional=True)
            return
        else:
            # some complex Union? e.g. Union[str, int, bool, float]
            logger.debug(f'Complex type hint found: {type_hint} - ({origin}, {args})')
            NestedClass = QDataclassValue
            dtype = object

        # handle more complex datatype annotations
        if dtype not in (int, float, bool, str):
            dtype = object

        setattr(
            self,
            name,
            NestedClass.of_type(dtype, optional=optional)(
                data,
                name,
                parent=self,
            ),
        )


class QDataclassElem:
    """
    Base class for elements of the QDataclassBridge

    Parameters
    ----------
    data : any dataclass
        The data we want to access and update
    attr : str
        The dataclass attribute to connect to
    """
    data: Any
    attr: str
    updated: QSignal
    _registry: ClassVar[Dict[str, type]]

    def __init__(
        self,
        data: Any,
        attr: str,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent=parent)
        self.data = data
        self.attr = attr


class QDataclassValue(QDataclassElem):
    """
    A single value in the QDataclassBridge.
    """
    changed_value: QSignal

    _registry = {}

    @classmethod
    def of_type(
        cls,
        data_type: type,
        optional: bool = False
    ) -> Type[QDataclassValue]:
        """
        Create a QDataclass with a specific QSignal

        Parameters
        ----------
        data_type : any primitive type
        optional : bool
            if the value is optional, True if ``None`` is a valid value
        """
        if optional:
            data_type = object

        try:
            return cls._registry[(data_type, optional)]
        except KeyError:
            ...

        new_class = type(
            f'QDataclassValueFor{data_type.__name__}',
            (cls, QObject),
            {
                'updated': QSignal(),
                'changed_value': QSignal(data_type),
            },
        )
        cls._registry[(data_type, optional)] = new_class
        return new_class

    def get(self) -> Any:
        """
        Return the current value.
        """
        return getattr(self.data, self.attr)

    def put(self, value: Any):
        """
        Change a value on the dataclass and update consumers.

        Parameters
        ----------
        value : any primitive type
        """
        setattr(self.data, self.attr, value)
        self.changed_value.emit(self.get())
        self.updated.emit()


class QDataclassList(QDataclassElem):
    """
    A list of values in the QDataclassBridge.
    """
    added_value: QSignal
    added_index: QSignal
    removed_value: QSignal
    removed_index: QSignal
    changed_value: QSignal
    changed_index: QSignal

    _registry = {}

    @classmethod
    def of_type(
        cls,
        data_type: type,
        optional: bool = False
    ) -> Type[QDataclassList]:
        """
        Create a QDataclass with a specific QSignal

        Parameters
        ----------
        data_type : any primitive type
        optional : bool
            if the value is optional, True if ``None`` is a valid value
        """
        if optional:
            changed_value_type = object
        else:
            changed_value_type = data_type

        try:
            return cls._registry[(data_type, optional)]
        except KeyError:
            ...

        new_class = type(
            f'QDataclassListFor{data_type.__name__}',
            (cls, QObject),
            {
                'updated': QSignal(),
                'added_value': QSignal(data_type),
                'added_index': QSignal(int),
                'removed_value': QSignal(data_type),
                'removed_index': QSignal(int),
                'changed_value': QSignal(changed_value_type),
                'changed_index': QSignal(int),
            },
        )
        cls._registry[(data_type, optional)] = new_class
        return new_class

    def get(self) -> List[Any]:
        """
        Return the current list of values.
        """
        return getattr(self.data, self.attr)

    def put(self, values: List[Any]) -> None:
        """
        Replace the current list of values.
        """
        setattr(self.data, self.attr, values)
        self.updated.emit()

    def append(self, new_value: Any) -> None:
        """
        Add a new value to the end of the list and update consumers.
        """
        data_list = self.get()
        if data_list is None:
            data_list = []
            setattr(self.data, self.attr, data_list)
        data_list.append(new_value)
        self.added_value.emit(new_value)
        self.added_index.emit(len(data_list) - 1)
        self.updated.emit()

    def remove_value(self, removal: Any) -> None:
        """
        Remove a value from the list by value and update consumers.
        """
        index = self.get().index(removal)
        self.get().remove(removal)
        self.removed_value.emit(removal)
        self.removed_index.emit(index)
        self.updated.emit()

    def remove_index(self, index: int) -> None:
        """
        Remove a value from the list by index and update consumers.
        """
        value = self.get().pop(index)
        self.removed_value.emit(value)
        self.removed_index.emit(index)
        self.updated.emit()

    def put_to_index(self, index: int, new_value: Any) -> None:
        """
        Change a value in the list and update consumers.
        """
        self.get()[index] = new_value
        self.changed_value.emit(new_value)
        self.changed_index.emit(index)
        self.updated.emit()


class QDataclassSet(QDataclassElem):
    """
    A set of values in the QDataclassBridge.
    """
    added_value: QSignal
    removed_value: QSignal

    _registry = {}

    @classmethod
    def of_type(
        cls,
        data_type: type,
        optional: bool = False,
    ) -> Type[QDataclassList]:
        """
        Create a QDataclass with a specific QSignal

        Parameters
        ----------
        data_type : any primitive type
        """
        try:
            return cls._registry[data_type]
        except KeyError:
            pass

        new_class = type(
            f'QDataclassSetFor{data_type.__name__}',
            (cls, QObject),
            {
                'updated': QSignal(),
                'added_value': QSignal(data_type),
                'removed_value': QSignal(data_type),
            },
        )
        cls._registry[data_type] = new_class
        return new_class

    def get(self) -> Set:
        """
        Return the current set of values.
        """
        return getattr(self.data, self.attr)

    def put(self, values: Set) -> None:
        """
        Replace the current set of values.
        """
        setattr(self.data, self.attr, values)
        self.updated.emit()

    def add(self, new_value: Any) -> None:
        """
        Add a new value to the set and update consumers.
        """
        data = self.get()
        if data is None:
            data = set()
            setattr(self.data, self.attr, data)
        data.add(new_value)
        self.added_value.emit(new_value)
        self.updated.emit()

    def remove_value(self, removal: Any) -> None:
        """
        Remove a value from the list by value and update consumers.
        """
        self.get().discard(removal)
        self.removed_value.emit(removal)
        self.updated.emit()
