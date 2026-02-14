import re
from copy import deepcopy
from dataclasses import fields, is_dataclass
from enum import Flag, auto
from typing import Any, Dict, Set
from uuid import UUID, uuid4

from superscore.model import Collection, Entry, Nestable

PLACEHOLDER_PATTERN = re.compile(r"\{\{(.*?)\}\}")


class TemplateMode(Flag):
    """Simple right/left side enum, where inversion `~` gives the other side"""
    CREATE_PLACEHOLDERS = auto()
    FILL_PLACEHOLDERS = auto()


def find_placeholders(obj: Any) -> Set[str]:
    """
    Recursively find all placeholders in the form of {{placeholder}}
    in string fields of the given object or its children.
    """
    placeholders = set()
    seen = set()

    def _search(item: Any):
        if id(item) in seen:
            return

        # Don't recurse into UUIDs or other basic types that aren't strings/containers
        if isinstance(item, (UUID, int, float, bool, type(None))):
            return

        seen.add(id(item))

        if isinstance(item, str):
            placeholders.update(PLACEHOLDER_PATTERN.findall(item))
        elif isinstance(item, list):
            for i in item:
                _search(i)
        elif isinstance(item, set):
            for i in item:
                _search(i)
        elif isinstance(item, dict):
            for v in item.values():
                _search(v)
        elif hasattr(item, "__dict__"):
            # dataclasses and other objects
            for v in vars(item).values():
                _search(v)

    _search(obj)
    return placeholders


def substitute_placeholders(
    obj: Any,
    substitutions: Dict[str, str],
    mode: TemplateMode = TemplateMode.FILL_PLACEHOLDERS
) -> Any:
    """
    Perform simple key-value substitution on all string fields of the object.
    Returns a new object if it was a string, or modifies the object in place
    if it's a mutable container.

    This does not yet handle tags (sets), which will need additional verification
    """
    if isinstance(obj, str):
        result = obj
        for key, value in substitutions.items():
            if mode == TemplateMode.FILL_PLACEHOLDERS:
                result = result.replace(f"{{{{{key}}}}}", value)
            else:
                result = result.replace(key, f"{{{{{value}}}}}")
        return result
    elif isinstance(obj, list):
        for i in range(len(obj)):
            obj[i] = substitute_placeholders(obj[i], substitutions, mode)
    elif isinstance(obj, dict):
        for k in obj:
            obj[k] = substitute_placeholders(obj[k], substitutions, mode)
    elif is_dataclass(obj):
        # Skip UUID fields
        for field in fields(obj):
            if fields == 'uuid':
                continue
            value = getattr(obj, field.name)
            setattr(obj, field.name, substitute_placeholders(value, substitutions, mode))
    return obj


def fill_template_collection(
    collection: Collection,
    substitutions: Dict[str, str],
    new_uuids: bool = True,
    mode: TemplateMode = TemplateMode.FILL_PLACEHOLDERS,
) -> Collection:
    """
    Create a filled Collection from a template Collection.
    If new_uuids is True, all entries in the tree will get new UUIDs.
    """
    # Deep copy to avoid modifying the template
    filled_collection = deepcopy(collection)

    if new_uuids:
        def _assign_new_uuids(item: Any):
            if isinstance(item, Entry):
                item.uuid = uuid4()
            if isinstance(item, Nestable):
                for child in item.children:
                    _assign_new_uuids(child)
        _assign_new_uuids(filled_collection)

    substitute_placeholders(filled_collection, substitutions, mode=mode)
    return filled_collection
