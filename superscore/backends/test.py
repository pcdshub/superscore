"""
Backend that manipulates Entries in-memory for testing purposes.
"""
from typing import List, Optional, Union
from uuid import UUID

from superscore.backends.core import _Backend
from superscore.errors import (BackendError, EntryExistsError,
                               EntryNotFoundError)
from superscore.model import Entry, Nestable, Root


class TestBackend(_Backend):
    """Backend that manipulates Entries in-memory, for testing purposes."""
    def __init__(self, data: Optional[List[Entry]] = None):
        if data is None:
            self.data = []
        else:
            self.data = data

        self._root = Root(entries=self.data)

    def save_entry(self, entry: Entry) -> None:
        try:
            self.get_entry(entry.uuid)
            raise EntryExistsError(f"Entry {entry.uuid} already exists")
        except EntryNotFoundError:
            self.data.append(entry)

    def get_entry(self, uuid: Union[UUID, str]) -> Entry:
        if isinstance(uuid, str):
            uuid = UUID(uuid)
        stack = self.data.copy()
        while len(stack) > 0:
            entry = stack.pop()
            if entry.uuid == uuid:
                return entry
            if isinstance(entry, Nestable):
                stack.extend(entry.children)
        raise EntryNotFoundError(f"Entry {entry.uuid} could not be found")

    def update_entry(self, entry: Entry) -> None:
        original = self.get_entry(entry.uuid)
        original.__dict__ = entry.__dict__

    def delete_entry(self, to_delete: Entry) -> None:
        stack = [self.data.copy()]
        while len(stack) > 0:
            children = stack.pop()
            for entry in children.copy():
                if entry == to_delete:
                    children.remove(entry)
                elif entry.uuid == to_delete.uuid:
                    raise BackendError(f"Can't delete: entry {to_delete.uuid} is out of sync with the version in the backend")
            stack.extend([entry.children for entry in children if isinstance(entry, Nestable)])

    @property
    def root(self) -> Root:
        return self._root
