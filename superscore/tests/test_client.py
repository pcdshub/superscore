import os
from pathlib import Path
from unittest.mock import patch
from uuid import UUID

import pytest

from superscore.backends.core import SearchTerm
from superscore.backends.filestore import FilestoreBackend
from superscore.client import Client
from superscore.control_layers import EpicsData
from superscore.errors import CommunicationError
from superscore.model import (Collection, Entry, Nestable, Parameter, Readback,
                              Root, Setpoint)

from .conftest import MockTaskStatus

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


def test_gather_data(mock_client, sample_database):
    snapshot = sample_database.entries[3]
    orig_pv = snapshot.children[0]
    dup_pv = Setpoint(
        uuid=orig_pv.uuid,
        description=orig_pv.description,
        pv_name=orig_pv.pv_name,
        data="You shouldn't see this",
    )
    snapshot.children.append(dup_pv)
    pvs, data_list = mock_client._gather_data(snapshot)
    assert len(pvs) == len(data_list) == 3
    assert data_list[pvs.index("MY:PREFIX:mtr1.ACCL")] == 2


@patch('superscore.control_layers.core.ControlLayer.put')
def test_apply(put_mock, mock_client: Client, sample_database: Root, setpoint_with_readback):
    put_mock.return_value = MockTaskStatus()
    snap = sample_database.entries[3]
    mock_client.apply(snap)
    assert put_mock.call_count == 1
    call_args = put_mock.call_args[0]
    assert len(call_args[0]) == len(call_args[1]) == 3

    put_mock.reset_mock()

    mock_client.apply(snap, sequential=True)
    assert put_mock.call_count == 3

    put_mock.reset_mock()
    mock_client.apply(setpoint_with_readback, sequential=True)
    assert put_mock.call_count == 1


@patch('superscore.control_layers.core.ControlLayer._get_one')
def test_snap(
    get_mock,
    mock_client: Client,
    sample_database: Root,
    parameter_with_readback: Parameter
):
    coll = sample_database.entries[2]
    coll.children.append(parameter_with_readback)

    get_mock.side_effect = [EpicsData(i) for i in range(5)]
    snapshot = mock_client.snap(coll)
    assert get_mock.call_count == 5
    assert all([snapshot.children[i].data == i for i in range(4)])  # children saved in order
    setpoint = snapshot.children[-1]
    assert isinstance(setpoint, Setpoint)
    assert isinstance(setpoint.readback, Readback)
    assert setpoint.readback.data == 4  # readback saved after setpoint


@patch('superscore.control_layers.core.ControlLayer._get_one')
def test_snap_exception(get_mock, mock_client: Client, sample_database: Root):
    coll = sample_database.entries[2]
    get_mock.side_effect = [EpicsData(0), EpicsData(1), CommunicationError,
                            EpicsData(3), EpicsData(4)]
    snapshot = mock_client.snap(coll)
    assert snapshot.children[2].data is None


@patch('superscore.control_layers.core.ControlLayer._get_one')
def test_snap_RO(get_mock, mock_client: Client, sample_database: Root):
    coll: Collection = sample_database.entries[2]
    coll.children.append(
        Parameter(pv_name="RO:PV",
                  abs_tolerance=1,
                  rel_tolerance=-.1,
                  read_only=True)
    )
    get_mock.side_effect = [EpicsData(i) for i in range(5)]
    snapshot = mock_client.snap(coll)

    assert get_mock.call_count == 4
    for coll_child, snap_child in zip(coll.children, snapshot.children):
        if coll_child.read_only:
            assert isinstance(snap_child, Readback)
        else:
            assert isinstance(snap_child, Setpoint)


def test_from_cfg(sscore_cfg: str):
    client = Client.from_config()
    assert isinstance(client.backend, FilestoreBackend)
    assert 'ca' in client.cl.shims


def test_find_config(sscore_cfg: str):
    assert sscore_cfg == Client.find_config()

    # explicit SUPERSCORE_CFG env var supercedes XDG_CONFIG_HOME
    os.environ['SUPERSCORE_CFG'] = 'other/cfg'
    assert 'other/cfg' == Client.find_config()


def test_search(sample_client):
    results = list(sample_client.search(
        ('data', 'isclose', (4, 0, 0))
    ))
    assert len(results) == 0

    results = list(sample_client.search(
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
def test_fill(sample_client: Client, entry_uuid: str):
    entry = list(sample_client.search(
        ("uuid", "eq", UUID(entry_uuid))
    ))[0]

    # often entries have uuids in children, but ensure they're all uuids
    entry.swap_to_uuids()
    assert uuids_in_entry(entry)

    sample_client.fill(entry)
    assert not uuids_in_entry(entry)
