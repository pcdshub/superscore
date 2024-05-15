"""
Base superscore data storage backend interface
"""
from typing import Generator
from uuid import UUID

from superscore.model import Entry


class _Backend:
    """
    Base class for data storage backend.
    """
    def get_entry(self, meta_id: UUID) -> Entry:
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

    def search(self, **search_kwargs) -> Generator[Entry, None, None]:
        """Yield a Entry objects corresponding matching ``search_kwargs``"""
        raise NotImplementedError
