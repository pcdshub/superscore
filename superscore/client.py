"""Client for superscore.  Used for programmatic interactions with superscore"""
from typing import Any, Generator

from superscore.backends.core import _Backend
from superscore.model import Entry


class Client:
    backend: _Backend

    def __init__(self, backend=None, **kwargs) -> None:
        # if backend is None, startup default filestore backend
        return

    @classmethod
    def from_config(cls, cfg=None):
        raise NotImplementedError

    def search(self, **post) -> Generator[Entry, None, None]:
        """Search by key-value pair.  Can search by any field, including id"""
        return self.backend.search(**post)

    def save(self, entry: Entry):
        """Save information in ``entry`` to database"""
        # validate entry is valid
        self.backend.save_entry(entry)

    def delete(self, entry: Entry) -> None:
        """Remove item from backend, depending on backend"""
        # check for references to ``entry`` in other objects?
        self.backend.delete_entry(entry)

    def compare(self, entry_l: Entry, entry_r: Entry) -> Any:
        """Compare two entries.  Should be of same type, and return a diff"""
        raise NotImplementedError

    def apply(self, entry: Entry):
        """Apply settings found in ``entry``.  If no values found, no-op"""
        raise NotImplementedError

    def validate(self, entry: Entry):
        """
        Validate ``entry`` is properly formed and able to be inserted into
        the backend.  Includes checks the following:
        - dataclass is valid
        - reachable from root
        - references are not cyclical, and type-correct
        """
        raise NotImplementedError
