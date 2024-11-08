from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from typing import Any, Generator, Iterable, List, Optional, Tuple, Union

from superscore.model import Entry

# An attribute access path chain leading to the item of interest
# simple fields:        (object, "field_name")
# dictionary values:    ("__dict__", "key_name")   ... not used?
# list entry:           ("__list__", list_index: int)
# enum value:           ("__enum__", Enum.member_object)
# set entry:            ("__set__", "set_member")
AttributePath = List[Tuple[Any, Any]]


@dataclass
class DiffItem:
    """
    A single difference, represented by a path to the changed fielid and the
    new/old values of said field
    """
    original_value: Any
    new_value: Any
    path: AttributePath

    def __repr__(self) -> str:
        # assume the first segment is an object
        if not self.path:
            repr_str = "()"
        else:
            repr_str = f"{type(self.path[0][0]).__name__}"

        for segment in self.path:
            if segment[0] == "__list__":
                repr_str += f"[{segment[1]}]"
            else:
                # handle simple field
                repr_str += f".{segment[1]}"

        if isinstance(self.original_value, Entry):
            orig_val_str = type(self.original_value).__name__
            new_val_str = type(self.new_value).__name__
        else:
            orig_val_str = self.original_value or "(None)"
            new_val_str = self.new_value or "(None)"

        repr_str += f": ({orig_val_str}->{new_val_str})"

        return repr_str


@dataclass
class EntryDiff:
    """
    The difference between original_entry and new_entry, represented by DiffItem's
    """
    original_entry: Entry
    new_entry: Entry
    diffs: Iterable[DiffItem]

    def __repr__(self) -> str:
        repr_str = "Diff: {\n"
        for diff in self.diffs:
            repr_str += f"    {str(diff)}\n"
        repr_str += "}"

        return repr_str


def walk_find_diff(
    orig_item: Union[Entry, Any],
    new_item: Union[Entry, Any],
    curr_path: Optional[AttributePath] = None,
) -> Generator[DiffItem, None, None]:
    if curr_path is None:
        curr_path = []

    if type(orig_item) is not type(new_item):
        yield DiffItem(
            original_value=orig_item,
            new_value=new_item,
            path=curr_path,
        )
    elif is_dataclass(orig_item):
        # get fields, recurse through fields
        orig_fields = {field.name: getattr(orig_item, field.name)
                       for field in fields(orig_item)}

        new_fields = {field.name: getattr(new_item, field.name)
                      for field in fields(new_item)}
        for field_name, field_value in orig_fields.items():
            if field_name not in new_fields:
                yield DiffItem(
                    original_value=field_value,
                    new_value=None,
                    path=curr_path + [(orig_item, field_name)],
                )
            else:
                # field name present in both
                yield from walk_find_diff(
                    orig_item=getattr(orig_item, field_name),
                    new_item=getattr(new_item, field_name),
                    curr_path=curr_path + [(orig_item, field_name)],
                )

        for new_field_name, new_field_value in new_fields.items():
            if field_name not in orig_fields:
                yield DiffItem(
                    original_value=None,
                    new_value=new_field_value,
                    path=curr_path + [(orig_item, new_field_name)],
                )

    elif isinstance(orig_item, list):
        num_orig = len(orig_item)
        num_new = len(new_item)
        # walk through as long as indexes exist in both
        for idx in range(min(num_orig, num_new)):
            # TODO: py3.10 allows isinstance with Unions
            yield from walk_find_diff(
                orig_item=orig_item[idx],
                new_item=new_item[idx],
                curr_path=curr_path + [("__list__", idx)]
            )

        # when list sizes don't match, items are either added or removed
        if num_orig > num_new:
            for idx in range(num_new, num_orig):
                yield DiffItem(
                    original_value=orig_item[idx],
                    new_value=None,
                    path=curr_path + [("__list__", idx)],
                )
        elif num_orig < num_new:
            for idx in range(num_orig, num_new):
                yield DiffItem(
                    original_value=None,
                    new_value=new_item[idx],
                    path=curr_path + [("__list__", num_orig + idx + 1)],
                )

    elif isinstance(orig_item, set):
        for new_member in new_item - orig_item:
            yield DiffItem(
                original_value=None,
                new_value=new_member,
                path=curr_path + [("__set__", new_member)],
            )
        for missing_member in orig_item - new_item:
            yield DiffItem(
                original_value=missing_member,
                new_value=None,
                path=curr_path + [("__set__", missing_member)],
            )

    # simple equality covers enums
    elif orig_item != new_item:
        yield DiffItem(
            original_value=orig_item,
            new_value=new_item,
            path=curr_path,
        )
