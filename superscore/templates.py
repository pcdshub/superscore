import re
from copy import deepcopy
from dataclasses import fields, is_dataclass
from enum import Flag, auto
from typing import Any, Dict, Set
from uuid import UUID, uuid4

from superscore.model import Collection, Entry, Nestable

# For simplicity we assume there are no nested double {{*}}, else we need lexical
# parsing
PLACEHOLDER_STRING = r"\{\{(.*?)\}\}"
PLACEHOLDER_PATTERN = re.compile(PLACEHOLDER_STRING)


class TemplateMode(Flag):
    """Simple right/left side enum, where inversion `~` gives the other side"""
    CREATE_PLACEHOLDERS = auto()
    FILL_PLACEHOLDERS = auto()


def safe_replace(
    text: str,
    target: str,
    replacement: str,
    safe_pattern: str = PLACEHOLDER_STRING
) -> str:
    """
    Replace `target` in `text` with `replacement`, ignoring anything in the
    PLACEHOLDER_PATTERN.
    """
    # Pattern explanation:
    # {{.*?}}  -> Matches anything inside double braces (non-greedy)
    # |        -> OR
    # target   -> Matches the substring you actually want to change
    pattern = safe_pattern + "|" + re.escape(target)

    def substitute(match: re.Match):
        group = match.group(0)
        # If the match starts with {{, it's a protected area; return it as-is
        if group.startswith('{{'):
            return group
        # Otherwise, it's our target; replace it
        return replacement

    return re.sub(pattern, substitute, text)


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
            for it in item:
                _search(it)
        elif isinstance(item, set):
            for it in item:
                _search(it)
        elif isinstance(item, dict):
            for val in item.values():
                _search(val)
        elif hasattr(item, "__dict__"):
            # dataclasses and other objects
            for val in vars(item).values():
                _search(val)

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
                result = safe_replace(result, key, f"{{{{{value}}}}}")
        return result
    elif isinstance(obj, list):
        for idx in range(len(obj)):
            obj[idx] = substitute_placeholders(obj[idx], substitutions, mode)
    elif isinstance(obj, dict):
        for key in obj:
            obj[key] = substitute_placeholders(obj[key], substitutions, mode)
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
