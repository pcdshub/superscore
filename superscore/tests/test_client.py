import os
from pathlib import Path
from unittest.mock import patch

import pytest

from superscore.backends.filestore import FilestoreBackend
from superscore.client import Client
from superscore.model import Root

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


@patch('superscore.control_layers.core.ControlLayer.put')
def test_apply(put_mock, mock_client: Client, sample_database: Root):
    put_mock.return_value = MockTaskStatus()
    snap = sample_database.entries[3]
    mock_client.apply(snap)
    assert put_mock.call_count == 1
    call_args = put_mock.call_args[0]
    assert len(call_args[0]) == len(call_args[1]) == 3

    put_mock.reset_mock()

    mock_client.apply(snap, sequential=True)
    assert put_mock.call_count == 3


def test_from_cfg(sscore_cfg: str):
    client = Client.from_config()
    assert isinstance(client.backend, FilestoreBackend)
    assert 'ca' in client.cl.shims


def test_find_config(sscore_cfg: str):
    assert sscore_cfg == Client.find_config()

    # explicit SUPERSCORE_CFG env var supercedes XDG_CONFIG_HOME
    os.environ['SUPERSCORE_CFG'] = 'other/cfg'
    assert 'other/cfg' == Client.find_config()
