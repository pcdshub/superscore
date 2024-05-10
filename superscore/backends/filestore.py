"""
Backend for configurations backed by files
"""

import contextlib
import json
import logging
import os
import shutil
from collections import defaultdict
from dataclasses import fields, replace
from typing import Any, DefaultDict, Dict, Generator, Optional, Set, Union
from uuid import UUID, uuid4

from apischema import deserialize, serialize

from superscore.backends.core import _Backend
from superscore.errors import BackendError
from superscore.model import Entry, Root
from superscore.utils import build_abs_path

logger = logging.getLogger(__name__)


class FilestoreBackend(_Backend):
    """
    Filestore configuration backend.
    Unique aspects:
    entry cache, filled with _load_or_initialize type method
    save method saves entire file, and therefore all Entries
    default method here is to store everything as a flattened dictionary for
    easier access, but serialization must keep Node structure (UUID references
    result in missing data)
    """
    _entry_cache: Dict[UUID, Entry] = {}
    _uuid_link_cache: DefaultDict[UUID, Set[UUID]] = defaultdict(set)
    _root: Root

    def __init__(
        self,
        path: str,
        initialize: bool = False,
        cfg_path: Optional[str] = None
    ) -> None:
        self._root = None
        self.path = path
        if cfg_path is not None:
            cfg_dir = os.path.dirname(cfg_path)
            self.path = build_abs_path(cfg_dir, path)
        else:
            self.path = path

        if initialize:
            self.initialize()

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
        for entry in self._root.entries:
            self.flatten_and_cache(entry)

        return self._entry_cache

    def flatten_and_cache(self, entry: Union[Entry, UUID]) -> None:
        """
        Flatten ``node`` recursively, adding them to ``self._entry_cache``.
        Does not replace any dataclass with its uuid
        Currently hard codes structure of Entry's, could maybe refactor later
        """
        if isinstance(entry, UUID):
            return

        for child in getattr(entry, 'children', []):
            self.maybe_add_to_cache(child)
            self.flatten_and_cache(child)

        uuid_refs = entry.swap_to_uuids()
        self._uuid_link_cache[entry.uuid].update(uuid_refs)
        self.maybe_add_to_cache(entry)

    def maybe_add_to_cache(self, item: Union[Entry, UUID]) -> None:
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
        # Dump an empty dictionary
        self.store({})

    def reconstruct_root(self) -> Root:
        """
        Reconstruct `Root` given the entries in the entry cache
        """
        new_root = Root()

        new_children = []
        for root_child in self._root.entries:
            if root_child.uuid in self._entry_cache:
                new_children.append(self.fill_uuids(root_child))

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

    def store(self, root_node: Optional[Root] = None) -> None:
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
        if root_node is None:
            serialized = serialize(Root, self._root)
        else:
            serialized = serialize(Root, Root())

        try:
            with open(temp_path, 'w') as fd:
                json.dump(serialized, fd, indent=2)

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
        Load database from stored path as a nested structure (deserialize as Root)
        """
        with open(self.path) as fp:
            serialized = json.load(fp)

        return deserialize(Root, serialized)

    @property
    def root(self) -> Root:
        with _load_and_store_context(self):
            return self._root

    def get_entry(self, meta_id: UUID) -> Entry:
        """Return the entry"""
        with _load_and_store_context(self) as db:
            return db.get(meta_id)

    def save_entry(self, entry: Entry) -> None:
        """
        Save specific entry into database. Entry is expected to not already exist
        Assumes connections are made properly.
        """
        with _load_and_store_context(self) as db:
            if db.get(entry.uuid):
                raise BackendError("Entry already exists, try updating the entry "
                                   "instead of saving it")
            db[entry.uuid] = entry
            self._root.entries.append(entry)

    def update_entry(self, entry: Entry) -> None:
        """Updates ``entry``.  Looks for references"""
        with _load_and_store_context(self) as db:
            if not db.get(entry.uuid):
                raise BackendError("Entry does not exist, cannot update")

            db[entry.uuid] = entry

    def delete_entry(self, entry: Entry) -> None:
        """Delete meta_id from the system (all instances)"""
        with _load_and_store_context(self) as db:
            db.pop(entry.uuid, None)

    def search(self, **search_kwargs) -> Generator[Entry, None, None]:
        """Search given ``search_kwargs``"""
        for entry in self._entry_cache.values():
            match = (getattr(entry, key, None) == value
                     for key, value in search_kwargs.items())
            if all(match):
                yield entry

    def clear_cache(self) -> None:
        """Clear the loaded cache and stored root"""
        self._entry_cache = {}
        self._root = None


@contextlib.contextmanager
def _load_and_store_context(
    backend: FilestoreBackend
) -> Generator[Dict[UUID, Any], None, None]:
    """
    Context manager used to load, and optionally store the JSON database.
    Yields the flattened entry cache
    """
    db = backend._load_or_initialize()
    yield db
    backend.store()
