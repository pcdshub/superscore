"""
Backend that manipulates Entries in-memory for testing purposes.
"""
from copy import deepcopy
from typing import Dict, Union
from uuid import UUID

from superscore.backends.core import SearchTermType, _Backend
from superscore.errors import (BackendError, EntryExistsError,
                               EntryNotFoundError)
from superscore.model import Entry, Nestable, Root


class TestBackend(_Backend):
    """Backend that manipulates Entries in-memory, for testing purposes."""
    __test__ = False  # Tell pytest this isn't a test case
    _entry_cache: Dict[UUID, Entry] = {}

    def __init__(
        self,
        root: Root = None
    ):
        self._root = root if root else Root()

        self._fill_entry_cache()

    def _fill_entry_cache(self) -> None:
        self._entry_cache = {}
        stack = deepcopy(self._root.entries)
        while len(stack) > 0:
            entry = stack.pop()
            uuid = entry.uuid
            if isinstance(uuid, str):
                uuid = UUID(uuid)
            self._entry_cache[uuid] = entry
            if isinstance(entry, Nestable):
                stack.extend(entry.children)

    def save_entry(self, entry: Entry) -> None:
        try:
            self.get_entry(entry.uuid)
            raise EntryExistsError(f"Entry {entry.uuid} already exists")
        except EntryNotFoundError:
            self._root.entries.append(entry)
            self._fill_entry_cache()

    def get_entry(self, uuid: Union[UUID, str]) -> Entry:
        if isinstance(uuid, str):
            uuid = UUID(uuid)

        try:
            return self._entry_cache[uuid]
        except KeyError:
            raise EntryNotFoundError(f"Entry {uuid} could not be found")

    def update_entry(self, entry: Entry) -> None:
        original = self.get_entry(entry.uuid)
        original.__dict__ = entry.__dict__

    def delete_entry(self, to_delete: Entry) -> None:
        stack = [self._root.entries.copy()]
        # remove from nested children
        while len(stack) > 0:
            children = stack.pop()
            for entry in children.copy():
                if entry == to_delete:
                    children.remove(entry)
                elif entry.uuid == to_delete.uuid:
                    raise BackendError(
                        f"Can't delete: entry {to_delete.uuid} "
                        "is out of sync with the version in the backend"
                    )
            stack.extend([entry.children for entry in children if isinstance(entry, Nestable)])

        # Remove from top level if necessary
        if to_delete in self._root.entries:
            self._root.entries.remove(to_delete)

        self._fill_entry_cache()

    @property
    def root(self) -> Root:
        return self._root

    def search(self, *search_terms: SearchTermType):
        for entry in self._entry_cache.values():
            conditions = []
            for attr, op, target in search_terms:
                # TODO: search for child pvs?
                if attr == "entry_type":
                    conditions.append(isinstance(entry, target))
                else:
                    try:
                        # check entry attribute by name
                        value = getattr(entry, attr)
                        conditions.append(self.compare(op, value, target))
                    except AttributeError:
                        conditions.append(False)
            if all(conditions):
                yield entry

    def get_tags(self) -> dict[int, str]:
        return self._root.all_tags

    def set_tags(self, tags: dict[int, str]) -> None:
        self._root.all_tags = tags
