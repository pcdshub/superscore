from datetime import datetime
from typing import List
from uuid import UUID

import pytest

from superscore.backends.core import SearchTerm
from superscore.backends.filestore import FilestoreBackend
from superscore.client import Client
from superscore.compare import (AttributePath, DiffItem, EntryDiff,
                                walk_find_diff)
from superscore.model import (Collection, Entry, Parameter, Readback, Setpoint,
                              Severity, Snapshot, Status)
from superscore.tests.conftest import setup_test_stack


def simplify_path(path: AttributePath) -> AttributePath:
    """swap objects for their type, for ease of testing"""
    simplified_path = []
    for seg in path:
        if isinstance(seg[0], Entry):
            item = type(seg[0])
        else:
            item = seg[0]

        if isinstance(seg[1], Entry):
            val = type(seg[1])
        else:
            val = seg[1]

        simplified_path.append((item, val))

    return simplified_path


def simplify_diff(diff: DiffItem) -> DiffItem:
    if isinstance(diff.original_value, Entry):
        orig_val = type(diff.original_value)
    else:
        orig_val = diff.original_value

    if isinstance(diff.new_value, Entry):
        new_val = type(diff.new_value)
    else:
        new_val = diff.new_value

    return DiffItem(original_value=orig_val, new_value=new_val,
                    path=simplify_path(diff.path))


@pytest.mark.parametrize("orig,new,expected_diffs,", [
    (Parameter(), Parameter(), []),
    (Parameter(pv_name="orig"), Parameter(), [
        DiffItem(
            path=[(Parameter, "pv_name")], original_value="orig", new_value=""
        ),
    ]),
    (Parameter(pv_name=""), Parameter(pv_name="new"), [
        DiffItem(
            path=[(Parameter, "pv_name")], original_value="", new_value="new"
        ),
    ]),
    (Parameter(), Readback(), [
        DiffItem(path=[], original_value=Parameter, new_value=Readback)
    ]),
    (Setpoint(severity=Severity.MAJOR), Setpoint(status=Status.HIGH), [
        DiffItem(path=[(Setpoint, "status")],
                 original_value=Status.UDF, new_value=Status.HIGH),
        DiffItem(path=[(Setpoint, "severity")],
                 original_value=Severity.MAJOR, new_value=Severity.INVALID)
    ]),
    (Collection(tags=set(["z", "c"])), Collection(tags=set(["a", "b", "z"])), [
        DiffItem(path=[(Collection, "tags"), ("__set__", "a")],
                 original_value=None, new_value="a"),
        DiffItem(path=[(Collection, "tags"), ("__set__", "b")],
                 original_value=None, new_value="b"),
        DiffItem(path=[(Collection, "tags"), ("__set__", "c")],
                 original_value="c", new_value=None),
    ]),
    (Collection(children=[]), Collection(children=[Parameter()]), [
        DiffItem(path=[(Collection, "children"), ("__list__", 1)],
                 original_value=None, new_value=Parameter),
    ]),
    (Collection(children=[Readback(), Readback()]), Collection(children=[Parameter()]), [
        DiffItem(path=[(Collection, "children"), ("__list__", 0)],
                 original_value=Readback, new_value=Parameter),
        DiffItem(path=[(Collection, "children"), ("__list__", 1)],
                 original_value=Readback, new_value=None),
    ]),
])
def test_basic_diff(orig: Entry, new: Entry, expected_diffs: List[DiffItem]):
    """
    Compare expected paths to discovered.
    Also verifies values in a simplified form (type of Entry's)
    """
    raw_found_diff = walk_find_diff(orig, new)

    found_diff = [simplify_diff(diff) for diff in raw_found_diff
                  if not isinstance(diff.original_value, (UUID, datetime))]
    assert len(found_diff) == len(expected_diffs)

    # Note: sets make no guarantees about order, so we have to check all diffs
    # We could make some cross mapping, but iterating is simpler and I don't
    # care to optimize for performance here (can't index on unhashable list)
    for f_diff in found_diff:
        match_found = False
        for e_diff in expected_diffs:
            if f_diff.path == e_diff.path:
                match_found = True
                assert f_diff.original_value == e_diff.original_value
                assert f_diff.new_value == e_diff.new_value
        assert match_found, "Matching path not found in expected paths"
        print(f_diff)


date_format = "%Y-%m-%dT"


@pytest.mark.parametrize("l_uuid,r_uuid,expected_diffs,", [
    (  # Same snapshot, no differences
        "ffd668d3-57d9-404e-8366-0778af7aee61",
        "ffd668d3-57d9-404e-8366-0778af7aee61",
        []
    ),
    (  # different initial type
        "ffd668d3-57d9-404e-8366-0778af7aee61",
        "8e380e15-5489-41db-a8a7-bc47a731f099",
        [DiffItem(
            path=[],
            original_value=Snapshot,
            new_value=Readback
        )]
    ),
    (  # two different readbacks
        "ecb42cdb-b703-4562-86e1-45bd67a2ab1a",
        "8e380e15-5489-41db-a8a7-bc47a731f099",
        [
            DiffItem(
                path=[],
                original_value=UUID("ecb42cdb-b703-4562-86e1-45bd67a2ab1a"),
                new_value=UUID("8e380e15-5489-41db-a8a7-bc47a731f099"),
            ),
            DiffItem(
                path=[],
                original_value=datetime.fromisoformat("2024-05-10T16:49:34.574951+00:00"),
                new_value=datetime.fromisoformat("2024-05-10T16:49:34.574987+00:00"),
            ),
            DiffItem(
                path=[],
                original_value="MY:PREFIX:mtr1.ACCL",
                new_value="MY:PREFIX:mtr1.VELO",
            ),

        ]
    ),
])
@setup_test_stack(sources=["db/filestore.json"], backend_type=FilestoreBackend)
def test_client_diff(
    test_client: Client,
    l_uuid: str,
    r_uuid: str,
    expected_diffs: list[DiffItem]
):
    """Run comparison tests based on filestore backend.  Ignore paths"""
    l_entry = list(test_client.search(
        SearchTerm(operator='eq', attr='uuid', value=UUID(l_uuid))
    ))[0]
    r_entry = list(test_client.search(
        SearchTerm(operator='eq', attr='uuid', value=UUID(r_uuid))
    ))[0]
    diff: EntryDiff = test_client.compare(l_entry, r_entry)
    print(diff)
    assert len(expected_diffs) == len(diff.diffs)
    for found_diff, expected_diff in zip(diff.diffs, expected_diffs):
        if isinstance(found_diff.original_value, Entry):
            assert type(found_diff.original_value) is expected_diff.original_value
            assert type(found_diff.new_value) is expected_diff.new_value
        else:
            assert found_diff.original_value == expected_diff.original_value
            assert found_diff.new_value == expected_diff.new_value
