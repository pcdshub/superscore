import os
from pathlib import Path
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest

from superscore.backends.core import SearchTerm
from superscore.backends.directory import DirectoryBackend
from superscore.backends.filestore import FilestoreBackend
from superscore.backends.test import TestBackend
from superscore.client import Client
from superscore.control_layers import EpicsData
from superscore.errors import CommunicationError, EntryNotFoundError
from superscore.model import (Collection, Entry, Nestable, Parameter, Readback,
                              Root, Setpoint, Snapshot)
from superscore.tests.conftest import (MockTaskStatus, nest_depth,
                                       setup_test_stack)

SAMPLE_CFG = Path(__file__).parent / 'config.cfg'


@pytest.fixture(scope='function')
def xdg_config_patch(tmp_path):
    config_home = tmp_path / 'xdg_config_home'
    config_home.mkdir()
    return config_home


@pytest.fixture(scope='function')
def sscore_cfg(xdg_config_patch: Path):
    # patch config discovery paths
    xdg_cfg = os.environ.get("XDG_CONFIG_HOME", '')
    sscore_cfg = os.environ.get("SUPERSCORE_CFG", '')

    os.environ['XDG_CONFIG_HOME'] = str(xdg_config_patch)
    os.environ['SUPERSCORE_CFG'] = ''

    sscore_cfg_path = xdg_config_patch / "superscore.cfg"
    sscore_cfg_path.symlink_to(SAMPLE_CFG)

    yield str(sscore_cfg_path)

    # reset env vars
    os.environ["SUPERSCORE_CFG"] = str(sscore_cfg)
    os.environ["XDG_CONFIG_HOME"] = xdg_cfg


def test_gather_data(test_client, sample_database_fixture):
    snapshot = sample_database_fixture.entries[3]
    orig_pv = snapshot.children[0]
    dup_pv = Setpoint(
        uuid=orig_pv.uuid,
        description=orig_pv.description,
        pv_name=orig_pv.pv_name,
        data="You shouldn't see this",
    )
    snapshot.children.append(dup_pv)
    pvs, data_list = test_client._gather_data(snapshot)
    assert len(pvs) == len(data_list) == 3
    assert data_list[pvs.index("MY:PREFIX:mtr1.ACCL")] == 2


def test_apply(
    test_client: Client,
    sample_database_fixture: Root,
    setpoint_with_readback_fixture: Setpoint
):
    put_mock = test_client.cl.put
    put_mock.return_value = MockTaskStatus()
    snap = sample_database_fixture.entries[3]
    test_client.apply(snap)
    assert put_mock.call_count == 1
    call_args = put_mock.call_args[0]
    assert len(call_args[0]) == len(call_args[1]) == 3

    put_mock.reset_mock()

    test_client.apply(snap, sequential=True)
    assert put_mock.call_count == 3

    put_mock.reset_mock()
    test_client.apply(setpoint_with_readback_fixture, sequential=True)
    assert put_mock.call_count == 1


@patch('superscore.control_layers.core.ControlLayer._get_one')
@setup_test_stack(backend_type=[DirectoryBackend], mock_cl=False)
def test_snap(
    get_mock,
    test_client: Client,
    sample_database_fixture: Root,
    parameter_with_readback_fixture: Parameter
):
    # Testing get -> _get_one chain, must not mock control layer

    for entry in sample_database_fixture.entries:
        test_client.save(entry)
    test_client.save(parameter_with_readback_fixture)

    get_mock.side_effect = [EpicsData(i) for i in range(6)]
    snapshot = test_client.snap()
    assert get_mock.call_count == 6
    assert all([snapshot.children[i].data == i for i in range(4)])  # children saved in order
    setpoint = snapshot.children[-1]
    assert isinstance(setpoint, Setpoint)
    assert isinstance(setpoint.readback, Readback)
    assert setpoint.readback.data > 4  # readback saved after setpoint


@patch('superscore.control_layers.core.ControlLayer._get_one')
@setup_test_stack(backend_type=[DirectoryBackend], mock_cl=False)
def test_snap_exception(get_mock, test_client: Client, sample_database_fixture: Root):
    # Testing get -> _get_one chain, must not mock control layer
    for entry in sample_database_fixture.entries:
        test_client.save(entry)
    get_mock.side_effect = [EpicsData(0), EpicsData(1), CommunicationError,
                            EpicsData(3), EpicsData(4)]
    snapshot = test_client.snap()
    assert snapshot.children[2].data is None


@patch('superscore.control_layers.core.ControlLayer._get_one')
@setup_test_stack(backend_type=[DirectoryBackend], mock_cl=False)
def test_snap_RO(get_mock, test_client: Client, sample_database_fixture: Root):
    # Testing get -> _get_one chain, must not mock control layer
    for entry in sample_database_fixture.entries:
        test_client.save(entry)
    test_client.save(
        Parameter(
            pv_name="RO:PV",
            abs_tolerance=1,
            rel_tolerance=-.1,
            read_only=True
        )
    )

    get_mock.side_effect = [EpicsData(i) for i in range(5)]
    snapshot = test_client.snap()

    assert get_mock.call_count == 5
    assert sum(1 for entry in snapshot.children if isinstance(entry, Readback)) == 1
    assert sum(1 for entry in snapshot.children if isinstance(entry, Setpoint)) == 4


def test_from_cfg(sscore_cfg: str):
    client = Client.from_config()
    assert isinstance(client.backend, FilestoreBackend)
    assert 'ca' in client.cl.shims


def test_find_config(sscore_cfg: str):
    assert sscore_cfg == Client.find_config()

    # explicit SUPERSCORE_CFG env var supercedes XDG_CONFIG_HOME
    os.environ['SUPERSCORE_CFG'] = 'other/cfg'
    assert 'other/cfg' == Client.find_config()


@setup_test_stack(sources=["db/filestore.json"], backend_type=FilestoreBackend)
def test_search(test_client):
    results = list(test_client.search(
        ('data', 'isclose', (4, 0, 0))
    ))
    assert len(results) == 0

    results = list(test_client.search(
        SearchTerm(operator='isclose', attr='data', value=(4, .5, 1))
    ))
    assert len(results) == 4


def uuids_in_entry(entry: Entry):
    """
    Returns True if there is a UUID in a spot where an Entry could be,
    False otherwise.
    """
    if isinstance(entry, Nestable):
        for child in entry.children:
            if isinstance(child, UUID):
                return True

    return False


@pytest.mark.parametrize("entry_uuid", [
    "a9f289d4-3421-4107-8e7f-2fe0daab77a5",
    "ffd668d3-57d9-404e-8366-0778af7aee61",
])
@setup_test_stack(sources=["db/filestore.json"], backend_type=FilestoreBackend)
def test_fill(test_client: Client, entry_uuid: str):
    entry = list(test_client.search(
        ("uuid", "eq", UUID(entry_uuid))
    ))[0]

    # often entries have uuids in children, but ensure they're all uuids
    entry.swap_to_uuids()
    assert uuids_in_entry(entry)

    test_client.fill(entry)
    assert not uuids_in_entry(entry)


@pytest.mark.parametrize("fill_depth,", list(range(1, 11)))
def test_fill_depth(fill_depth: int):
    deep_coll = Collection()
    prev_coll = deep_coll
    # Be sure more depth exists than the requested depth
    for i in range(20):
        child_coll = Collection(title=f"collection {i}")
        prev_coll.children.append(child_coll)
        prev_coll = child_coll
    bknd = TestBackend(Root(entries=[deep_coll]))
    client = Client(backend=bknd)

    assert nest_depth(deep_coll) == 20
    deep_coll.swap_to_uuids()
    # for this test we want everything to be UUIDS
    for entry in bknd._entry_cache.values():
        entry.swap_to_uuids()

    assert nest_depth(deep_coll) == 1

    client.fill(deep_coll, fill_depth)

    assert nest_depth(deep_coll) == fill_depth


@setup_test_stack(
    sources=["linac_with_comparison_snapshot"],
    backend_type=FilestoreBackend
)
def test_search_entries_by_ancestor(test_client: Client):
    entries = tuple(test_client.search(
        ("entry_type", "eq", Setpoint),
        ("pv_name", "eq", "LASR:GUNB:TEST1"),
    ))
    assert len(entries) == 2
    entries = tuple(test_client.search(
        ("entry_type", "eq", Setpoint),
        ("pv_name", "eq", "LASR:GUNB:TEST1"),
        ("ancestor", "eq", UUID("06282731-33ea-4270-ba14-098872e627dc")),  # top-level snapshot
    ))
    assert len(entries) == 1
    entries = tuple(test_client.search(
        ("entry_type", "eq", Setpoint),
        ("pv_name", "eq", "LASR:GUNB:TEST1"),
        ("ancestor", "eq", UUID("2f709b4b-79da-4a8b-8693-eed2c389cb3a")),  # direct parent
    ))
    assert len(entries) == 1


@setup_test_stack(
    sources=["linac_with_comparison_snapshot"],
    backend_type=FilestoreBackend
)
def test_search_caching(test_client: Client):
    entry = test_client.backend.get_entry(UUID("2f709b4b-79da-4a8b-8693-eed2c389cb3a"))
    result = test_client.search(
        ("ancestor", "eq", UUID("2f709b4b-79da-4a8b-8693-eed2c389cb3a")),
    )
    assert len(tuple(result)) == 3
    entry.children = []
    test_client.backend.update_entry(entry)
    result = test_client.search(
        ("ancestor", "eq", UUID("2f709b4b-79da-4a8b-8693-eed2c389cb3a")),
    )
    assert len(tuple(result)) == 1  # update is picked up in new search


def test_parametrized_filestore_empty(test_client: Client):
    assert len(list(test_client.search())) == 0


@setup_test_stack(backend_type=TestBackend)
def test_find_origin_collection(test_client):
    collection = Collection()
    snapshot = Snapshot()
    test_client.save(collection)
    test_client.save(snapshot)

    assert test_client.find_origin_collection(collection) == collection
    with pytest.raises(ValueError):
        test_client.find_origin_collection(snapshot)
    snapshot.origin_collection = uuid4()
    with pytest.raises(EntryNotFoundError):
        test_client.find_origin_collection(snapshot)
    snapshot.origin_collection = collection.uuid
    assert test_client.find_origin_collection(snapshot) == collection
