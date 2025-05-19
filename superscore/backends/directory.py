"""
Backend for configurations backed by files within a directory
"""

import json
import logging
import os
from functools import cache
from typing import Container, Generator, Optional, Union
from uuid import UUID

from apischema import deserialize, serialize

from superscore.backends.core import SearchTermType, _Backend
from superscore.errors import (BackendError, EntryExistsError,
                               EntryNotFoundError)
from superscore.model import Entry, Nestable, Root
from superscore.type_hints import TagDef
from superscore.utils import build_abs_path

logger = logging.getLogger(__name__)

RADIX_DEPTH = 3


class DirectoryBackend(_Backend):
    """
    Backend that stores each Entry as an individual file. Files are distributed into directories
    according to the UUID of their Entry, to keep the number of files in each directory
    reasonably small.
    """

    def __init__(
        self,
        path: str,
        cfg_path: Optional[str] = None,
    ) -> None:
        self.path = path
        if cfg_path is not None:
            cfg_dir = os.path.dirname(cfg_path)
            self.path = build_abs_path(cfg_dir, path)
        try:
            self.initialize()
        except PermissionError:
            pass

    def get_entry(self, uuid: Union[UUID, str]) -> Entry:
        path = self._find_entry_path(uuid)
        try:
            with open(path, 'r') as f:
                serialized = json.load(f)
        except FileNotFoundError as e:
            raise EntryNotFoundError(e)
        return deserialize(Entry, serialized, coerce=True)

    def save_entry(self, entry: Entry, top_level: bool = True) -> None:
        children = entry.swap_to_uuids()
        for child in children:
            if isinstance(child, Entry):
                try:
                    self.save_entry(child, top_level=False)
                except FileExistsError:
                    self.update_entry(child)

        if top_level:
            self.add_to_root(entry)

        serialized = serialize(Entry, entry)
        path = self._find_entry_path(entry.uuid)
        try:
            dir_path = os.path.dirname(path)
            os.makedirs(dir_path, exist_ok=True)
            with open(path, 'x') as f:
                json.dump(serialized, f, indent=2)
        except FileExistsError as e:
            if top_level:
                raise EntryExistsError(e)
            else:
                self.update_entry(entry)
        except Exception:
            # catch specific exceptions, not FileExistsError
            # remove empty dirs in dir_path
            raise

    def delete_entry(self, entry: Entry) -> None:
        # TODO: delete children
        path = self._find_entry_path(entry.uuid)
        os.remove(path)
        dirname = os.path.dirname(path)
        if len(os.listdir(dirname)) == 0:
            os.removedirs(dirname)

    def update_entry(self, entry: Entry) -> None:
        # try to save children, then update; or vice-versa
        try:
            self.delete_entry(entry)
        except FileNotFoundError as e:
            raise BackendError(e)
        self.save_entry(entry, top_level=False)

    def search(self, *search_terms: SearchTermType) -> Generator[Entry, None, None]:
        reachable = cache(self._gather_reachable)
        for _, _, filenames in os.walk(self.path):
            for filename in filenames:
                if filename == "root.json":
                    continue
                uuid, _ = os.path.splitext(filename)
                entry = self.get_entry(uuid)
                conditions = []
                for attr, op, target in search_terms:
                    if attr == "entry_type":
                        conditions.append(isinstance(entry, target))
                    elif attr == "ancestor":
                        # `target` must be UUID since `reachable` is cached
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

    def _gather_reachable(self, ancestor: Union[Entry, UUID]) -> Container[UUID]:
        """
        Finds all entries accessible from ancestor, including ancestor, and returns
        their UUIDs. This makes it easy to check if one entry is hierarchically under another.
        """
        reachable = set()
        q = [ancestor]
        while len(q) > 0:
            cur = q.pop()
            if not isinstance(cur, Entry):
                cur = self.get_entry(cur)
            reachable.add(cur.uuid)
            if isinstance(cur, Nestable):
                q.extend(cur.children)
        return reachable

    @property
    def root(self) -> Root:
        with open(os.path.join(self.path, "root.json"), 'r') as f:
            serialized = json.load(f)
        return deserialize(Root, serialized, coerce=True)

    def add_to_root(self, entry: Entry):
        root = self.root
        root.entries.append(entry)
        serialized = serialize(Root, root)
        with open(os.path.join(self.path, "root.json"), 'w') as f:
            json.dump(serialized, f, indent=2)

    def initialize(self) -> None:
        try:
            os.mkdir(self.path)
        except FileExistsError:
            if os.path.exists(os.path.join(self.path, "root.json")):
                raise PermissionError(f"Directory {self.path} already exists. Can not initialize "
                                      "a new database.")

        try:
            with open(os.path.join(self.path, "root.json"), 'x') as f:
                json.dump(serialize(Root, Root()), f, indent=2)
        except Exception as e:
            logger.debug("Failed to initialize db", exc_info=e)

    def _find_entry_path(self, uuid: Union[UUID, str]) -> str:
        uuid = str(uuid)
        segments = list(uuid.replace('-', ''))
        internal_path = os.path.join(*segments[:RADIX_DEPTH])
        return os.path.join(self.path, internal_path, f"{uuid}.json")

    def get_tags(self) -> TagDef:
        return self.root.tag_groups

    def set_tags(self, tags: TagDef) -> None:
        root = self.root
        root.tag_groups = tags
        serialized = serialize(Root, root)
        with open(os.path.join(self.path, "root.json"), 'w') as f:
            json.dump(serialized, f, indent=2)

    def reset(self) -> None:
        for entry in self.search():
            self.delete_entry(entry)
        os.remove(os.path.join(self.path, "root.json"))
        os.rmdir(self.path)
        self.initialize()
