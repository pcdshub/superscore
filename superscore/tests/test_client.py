from unittest.mock import patch

from superscore.client import Client
from superscore.model import Root

from .conftest import MockTaskStatus


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
