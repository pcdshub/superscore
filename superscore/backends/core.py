"""
Base superscore data storage backend interface
"""
from collections.abc import Container, Generator
from typing import NamedTuple, Union
from uuid import UUID

from superscore.model import Entry, Root
from superscore.type_hints import AnyEpicsType

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

    @property
    def root(self) -> Root:
        """Return the Root Entry in this backend"""
        raise NotImplementedError
