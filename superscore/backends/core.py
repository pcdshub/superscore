"""
Base superscore data storage backend interface
"""
import re
from collections.abc import Container, Generator
from typing import Callable, Iterable, NamedTuple, Union
from uuid import UUID

import superscore.tests.conftest_data
from superscore.model import Entry, Root
from superscore.type_hints import AnyEpicsType, TagDef

SearchTermValue = Union[AnyEpicsType, Container[AnyEpicsType], tuple[AnyEpicsType, ...]]
SearchTermType = tuple[str, str, SearchTermValue]


class SearchTerm(NamedTuple):
    attr: str
    operator: str
    value: SearchTermValue


class _Backend:
    """
    Base class for data storage backend.
    """

    def get_entry(self, meta_id: Union[UUID, str]) -> Entry:
        """
        Get entry with ``meta_id``
        Throws EntryNotFoundError
        """
        raise NotImplementedError

    def save_entry(self, entry: Entry):
        """
        Save ``entry`` into the database
        Throws EntryExistsError
        """
        raise NotImplementedError

    def delete_entry(self, entry: Entry) -> None:
        """
        Delete ``entry`` from the system (all instances)
        Throws BackendError if backend contains an entry with the same uuid as ``entry``
        but different data
        """
        raise NotImplementedError

    def update_entry(self, entry: Entry) -> None:
        """
        Update ``entry`` in the backend.
        Throws EntryNotFoundError
        """
        raise NotImplementedError

    def search(self, *search_terms: SearchTermType) -> Generator[Entry, None, None]:
        """
        Yield Entry objects matching all ``search_terms``. Each SearchTerm has the format
        (<attr>, <operator>, <value>).  Some operators take tuples as values.

        The supported operators are:
        - eq (equals)
        - lt (less than or equal to)
        - gt (greater than or equal to)
        - in
        - like (fuzzy match, depends on type of value)
        """
        raise NotImplementedError

    @staticmethod
    def compare(op: str, data: AnyEpicsType, target: SearchTermValue) -> bool:
        """
        Return whether data and target satisfy the op comparator, typically during application
        of a search filter. Possible values of op are detailed in _Backend.search

        Parameters
        ----------
        op: str
            one of the comparators that all backends must support, detailed in _Backend.search
        data: AnyEpicsType | Tuple[AnyEpicsType]
            data from an Entry that is being used to decide whether the Entry passes a filter
        target: AnyEpicsType | Tuple[AnyEpicsType]
            the filter value

        Returns
        -------
        bool
            whether data and target satisfy the op condition
        """
        if op == "eq":
            return data == target
        elif op == "lt":
            if isinstance(data, dict):
                return all(data[key] <= target.get(key, set()) for key in data)
            else:
                return data <= target
        elif op == "gt":
            if isinstance(data, dict):
                return all(data.get(key, set()) >= target[key] for key in target)
            else:
                return data >= target
        elif op == "in":
            return data in target
        elif op == "like":
            if isinstance(data, UUID):
                data = str(data)
            return re.search(target, data)
        else:
            raise ValueError(f"SearchTerm does not support operator \"{op}\"")

    @property
    def root(self) -> Root:
        """Return the Root Entry in this backend"""
        raise NotImplementedError

    def get_tags(self) -> TagDef:
        """
        Return the definition of valid entry tags. Each tag group has an id and name, so that
        groups can be renamed without invaliding existing data. Tags (tag group members) also
        each have an id and name, for the same reason.
        """
        raise NotImplementedError

    def set_tags(self, tags: TagDef) -> None:
        """Set the definition of valid entry tags"""
        raise NotImplementedError


def populate_backend(backend: _Backend, sources: Iterable[Union[Callable, str, Root, Entry]]) -> None:
    """
    Utility for quickly filling test backends with data. Supports a mix of many
    types of sources:
    * Roots
    * Entries
    * Callables that return Roots or Entries
    * strings that search for test data callables, but critically not fixtures
    """
    for source in sources:
        if isinstance(source, Callable):
            data = source()
        elif isinstance(source, str):
            func = getattr(superscore.tests.conftest_data, source, False)
            data = func()
        elif isinstance(source, (Root, Entry)):
            data = source
        else:
            raise ValueError(f"Unsupported source type: {type(source)}")

        if isinstance(data, Root):
            for entry in data.entries:
                backend.save_entry(entry)
            backend.set_tags(data.tag_groups)
        else:
            backend.save_entry(data)
