"""
Backend for configurations backed by files
"""

import contextlib
import json
import logging
import os
import shutil
from dataclasses import fields, replace
from functools import cache
from typing import Any, Container, Dict, Generator, Optional, Union
from uuid import UUID, uuid4

from apischema import deserialize, serialize

from superscore.backends.core import SearchTermType, _Backend
from superscore.errors import BackendError
from superscore.model import Entry, Nestable, Root
from superscore.utils import build_abs_path

logger = logging.getLogger(__name__)


class FilestoreBackend(_Backend):
    """
    Filestore configuration backend.

    Holds an entry cache, filled when a file is loaded.
    All CRUD operations reconstruct the Root object and save a new version of
    the database.
    File storage is a json file containing serialized model dataclasses.
    """
    _entry_cache: Dict[UUID, Entry]
    _root: Root

    def __init__(
        self,
        path: str,
        cfg_path: Optional[str] = None
    ) -> None:
        self._entry_cache = {}
        self._root = None
        self.path = path
        if cfg_path is not None:
            cfg_dir = os.path.dirname(cfg_path)
            self.path = build_abs_path(cfg_dir, path)
        else:
            self.path = path

    def _load_or_initialize(self) -> Dict[str, Any]:
        """
        Load an existing database or initialize a new one.
        Returns the entry cache for this backend
        """
        if self._root is None:
            try:
                self._root = self.load()
            except FileNotFoundError:
                logger.debug("Initializing new database")
                self.initialize()
                self._root = self.load()

        # flatten create entry cache
        self._entry_cache = {}
        for entry in self._root.entries:
            self.flatten_and_cache(entry)

        return self._entry_cache

    def flatten_and_cache(self, entry: Union[Entry, UUID]) -> None:
        """
        Flatten ``entry`` recursively, adding it to ``self._entry_cache`` if not
        present already.

        If ``entry`` is already a UUID, it should have already been cached, and
        can be skipped.

        Parameters
        ----------
        entry : Union[Entry, UUID]
            entry or uuid reference to flatten and cache
        """
        if isinstance(entry, UUID):
            return
        refs = entry.swap_to_uuids()
        for ref in refs:
            if isinstance(ref, Entry):
                self.maybe_add_to_cache(ref)
                self.flatten_and_cache(ref)

        self.maybe_add_to_cache(entry)

    def maybe_add_to_cache(self, item: Union[Entry, UUID]) -> None:
        """
        Adds ``item`` to the entry cache if it does not already exist

        Parameters
        ----------
        item : Union[Entry, UUID]
            _description_
        """
        if isinstance(item, UUID):
            return
        meta_id = item.uuid
        if meta_id in self._entry_cache:
            # duplicate uuids found
            return

        self._entry_cache[meta_id] = item

    def initialize(self):
        """
        Initialize a new JSON file database.

        Raises
        ------
        PermissionError
            If the JSON file specified by ``path`` already exists.

        Notes
        -----
        This exists because the `.store` and `.load` methods assume that the
        given path already points to a readable JSON file. In order to begin
        filling a new database, an empty but valid JSON file is created.
        """

        # Do not overwrite existing databases
        if os.path.exists(self.path) and os.stat(self.path).st_size > 0:
            raise PermissionError("File {} already exists. Can not initialize "
                                  "a new database.".format(self.path))
        self._root = Root()
        self.store()

    def reconstruct_root(self) -> Root:
        """
        Reconstruct `Root` given the entries in the entry cache
        """
        new_root = Root()

        new_children = []
        for root_child in self._root.entries:
            if root_child.uuid in self._entry_cache:
                new_child = self._entry_cache[root_child.uuid]
                new_children.append(self.fill_uuids(new_child))

        new_root.entries = new_children
        return new_root

    def fill_uuids(self, entry: Entry) -> Entry:
        """
        Recursively fill ``entry``'s uuid fields with the object it references.

        Parameters
        ----------
        entry : Entry
            Entry object to be filled

        Returns
        -------
        Entry
            a copy of ``entry`` with filled uuids
        """
        # Create a copy of the entry to be modified
        entry = replace(entry)

        for field in fields(entry):
            if field.name == 'uuid':
                continue
            field_data = getattr(entry, field.name)

            if isinstance(field_data, list):
                new_list = []
                for item in field_data:
                    if isinstance(item, UUID):
                        new_ref = self._entry_cache.get(item)
                        if new_ref:
                            new_ref = self.fill_uuids(new_ref)
                            new_list.append(new_ref)

                if new_list:
                    setattr(entry, field.name, new_list)
            elif isinstance(field_data, UUID):
                new_ref = self._entry_cache.get(field_data)
                if new_ref:
                    new_ref = self.fill_uuids(new_ref)
                    setattr(entry, field.name)

        return entry

    def store(self) -> None:
        """
        Stash the database in the JSON file.
        This is a two-step process:
        1. Write the database out to a temporary file
        2. Move the temporary file over the previous database.
        Step 2 is an atomic operation, ensuring that the database
        does not get corrupted by an interrupted json.dump.
        Parameters
        ----------
        db : dict
            Dictionary to store in JSON.
        """
        temp_path = self._temp_path()
        self._root = self.reconstruct_root()
        serialized = serialize(Root, self._root)

        try:
            with open(temp_path, 'w') as fd:
                json.dump(serialized, fd, indent=2)
                fd.write('\n')

            if os.path.exists(self.path):
                shutil.copymode(self.path, temp_path)
            shutil.move(temp_path, self.path)
        except BaseException as ex:
            logger.debug('JSON db move failed: %s', ex, exc_info=ex)
            # remove temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise

    def _temp_path(self) -> str:
        """
        Return a temporary path to write the json file to during "store".
        Includes a hash for uniqueness
        (in the cases where multiple temp files are written at once).
        """
        directory = os.path.dirname(self.path)
        filename = (
            f"_{str(uuid4())[:8]}"
            f"_{os.path.basename(self.path)}"
        )
        return os.path.join(directory, filename)

    def load(self) -> Optional[Root]:
        """
        Load database from stored path as a nested structure
        """
        with open(self.path) as fp:
            serialized = json.load(fp)

        return deserialize(Root, serialized)

    @property
    def root(self) -> Root:
        """Refresh the cache and return the root object"""
        with self._load_and_store_context():
            return self._root

    def get_entry(self, uuid: Union[UUID, str]) -> Entry:
        """Return the entry with ``uuid``"""
        with self._load_and_store_context() as db:
            if isinstance(uuid, str):
                uuid = UUID(uuid)
            return db.get(uuid)

    def save_entry(self, entry: Entry) -> None:
        """
        Save ``entry`` into database. Entry is expected to not already exist
        Assumes connections are made properly.
        """
        with self._load_and_store_context() as db:
            if db.get(entry.uuid):
                raise BackendError("Entry already exists, try updating the entry "
                                   "instead of saving it")
            self.flatten_and_cache(entry)
            self._root.entries.append(entry)

    def update_entry(self, entry: Entry) -> None:
        """Updates ``entry``.  Looks for references"""
        with self._load_and_store_context() as db:
            if not db.get(entry.uuid):
                raise BackendError("Entry does not exist, cannot update")

            db[entry.uuid] = entry

    def delete_entry(self, entry: Entry) -> None:
        """Delete meta_id from the system (all instances)"""
        with self._load_and_store_context() as db:
            db.pop(entry.uuid, None)

    def search(self, *search_terms: SearchTermType) -> Generator[Entry, None, None]:
        """
        Return entries that match all ``search_terms``.
        Keys are attributes on `Entry` subclasses, or special keywords.
        Values can be a single value or a tuple of values depending on operator.
        """
        reachable = cache(self._gather_reachable)
        with self._load_and_store_context() as db:
            for entry in db.values():
                conditions = []
                for attr, op, target in search_terms:
                    # TODO: search for child pvs?
                    if attr == "entry_type":
                        conditions.append(isinstance(entry, target))
                    elif attr == "ancestor":
                        conditions.append(entry.uuid in reachable(target))
                    else:
                        try:
                            # check entry attribute by name
                            value = getattr(entry, attr)
                            conditions.append(self.compare(op, value, target))
                        except AttributeError:
                            conditions.append(False)
                if all(conditions):
                    yield entry

    def _gather_reachable(self, ancestor: UUID) -> Container[UUID]:
        """
        Finds all entries accessible from ancestor, including ancestor, and returns
        their UUIDs. This makes it easy to check if one entry is hierarchically under another.
        """
        reachable = set()
        q = [ancestor]
        while len(q) > 0:
            cur = q.pop()
            if not isinstance(cur, Entry):
                cur = self._entry_cache[cur]
            reachable.add(cur.uuid)
            if isinstance(cur, Nestable):
                q.extend(cur.children)
        return reachable

    @contextlib.contextmanager
    def _load_and_store_context(self) -> Generator[Dict[UUID, Any], None, None]:
        """
        Context manager used to load, and optionally store the JSON database.
        Yields the flattened entry cache
        """
        db = self._load_or_initialize()
        yield db
        self.store()
