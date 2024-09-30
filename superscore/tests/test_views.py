from unittest.mock import MagicMock

import pytest
from pytestqt.qtbot import QtBot
from qtpy import QtCore

from superscore.client import Client
from superscore.control_layers import EpicsData
from superscore.model import Parameter
from superscore.widgets.views import LivePVTableModel


@pytest.fixture(scope='function')
def pv_poll_model(
    mock_client: Client,
    parameter_with_readback: Parameter,
    qtbot: QtBot
) -> LivePVTableModel:
    model = LivePVTableModel(
        client=mock_client,
        entries=[parameter_with_readback],
        poll_period=1.0
    )

    # Make sure we never actually call EPICS
    model.client.cl.get = MagicMock(return_value=EpicsData(1))
    qtbot.wait_until(lambda: model._poll_thread.running)
    yield model

    model.stop_polling()

    qtbot.wait_until(lambda: not model._poll_thread.isRunning())


def test_pvmodel_polling(pv_poll_model: LivePVTableModel, qtbot: QtBot):
    thread = pv_poll_model._poll_thread
    pv_poll_model.stop_polling()
    qtbot.wait_until(lambda: thread.isFinished(), timeout=10000)
    assert not thread.running


def test_pvmodel_update(pv_poll_model: LivePVTableModel, qtbot: QtBot):
    assert pv_poll_model._data_cache

    # make the mock cl return a new value
    pv_poll_model.client.cl.get = MagicMock(return_value=EpicsData(3))

    qtbot.wait_signal(pv_poll_model.dataChanged)

    data_index = pv_poll_model.index_from_item(pv_poll_model.entries[0], 'Live Value')
    qtbot.wait_until(
        lambda: pv_poll_model.data(data_index, QtCore.Qt.DisplayRole) == '3'
    )
