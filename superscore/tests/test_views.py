import copy
from typing import Any
from unittest.mock import MagicMock

import apischema
import pytest
from pytestqt.qtbot import QtBot
from qtpy import QtCore, QtWidgets

from superscore.client import Client
from superscore.control_layers import EpicsData
from superscore.model import Collection, Parameter, Severity, Status
from superscore.widgets.views import (CustRoles, LivePVHeader,
                                      LivePVTableModel, LivePVTableView)


@pytest.fixture(scope='function')
def pv_poll_model(
    mock_client: Client,
    parameter_with_readback: Parameter,
    qtbot: QtBot
):
    """Minimal LivePVTableModel, containing only Parameters (no stored data)"""
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


@pytest.fixture(scope="function")
def pv_table_view(
    mock_client: Client,
    simple_snapshot: Collection,
    qtbot: QtBot,
):
    """
    LivePVTableView, holds three PVs with different types.  Stored data allowed.
    Mocks control layer to return realistic-ish EpicsData

    TODO: add string field examples once we properly handle strings
    """
    # Build side effect function:
    ret_vals = {
        "MY:FLOAT": EpicsData(data=0.5, precision=3,
                              upper_ctrl_limit=2, lower_ctrl_limit=-2),
        "MY:INT": EpicsData(data=1, upper_ctrl_limit=10, lower_ctrl_limit=-10),
        "MY:ENUM": EpicsData(data=0, enums=["OUT", "IN", "UNKNOWN"])
    }

    def simple_coll_return_vals(pv_name: str):
        return ret_vals[pv_name]

    mock_client.cl.get = MagicMock(side_effect=simple_coll_return_vals)

    view = LivePVTableView()
    view.client = mock_client
    view.set_data(simple_snapshot)

    qtbot.wait_until(lambda: view.model()._poll_thread.isRunning())
    yield view

    view.model().stop_polling()
    qtbot.wait_until(lambda: not view.model()._poll_thread.isRunning())


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


@pytest.mark.parametrize("row,widget_cls,", [
    (0, QtWidgets.QDoubleSpinBox),
    (1, QtWidgets.QSpinBox),
    (2, QtWidgets.QComboBox),
])
def test_pv_view_value_delegate_types(
    row: int,
    widget_cls: QtWidgets.QWidget,
    pv_table_view: LivePVTableView,
    qtbot: QtBot,
):
    model = pv_table_view.model()
    assert isinstance(model, LivePVTableModel)

    index = model.index(row, LivePVHeader.STORED_VALUE)

    # let the data populate before checking delegate type
    qtbot.wait_until(
        lambda: isinstance(model.data(index, CustRoles.EpicsDataRole), EpicsData)
    )

    edit_widget = pv_table_view.value_delegate.createEditor(pv_table_view, 0, index)
    assert isinstance(edit_widget, widget_cls)


@pytest.mark.parametrize("col,widget_cls,", [
    (LivePVHeader.PV_NAME, QtWidgets.QLineEdit),
    (LivePVHeader.STORED_SEVERITY, QtWidgets.QComboBox),
    (LivePVHeader.STORED_STATUS, QtWidgets.QComboBox),
])
def test_pv_view_common_delegate_types(
    col: int,
    widget_cls: QtWidgets.QWidget,
    pv_table_view: LivePVTableView,
):
    model = pv_table_view.model()
    assert isinstance(model, LivePVTableModel)

    index = model.index(0, col)

    # unlike previous test, no waiting needed, since we don't initialize the
    # widget with any live data

    edit_widget = pv_table_view.value_delegate.createEditor(pv_table_view, 0, index)
    assert isinstance(edit_widget, widget_cls)


@pytest.mark.parametrize("row,input_data,", [
    (0, 0.1),
    (1, 2),
    (2, 1),  # enum types get set as ints, viewed as strings
])
def test_set_data(
    row: int,
    input_data: Any,
    pv_table_view: LivePVTableView
):
    orig_data = copy.deepcopy(pv_table_view.data)
    orig_ser = apischema.serialize(type(pv_table_view.data), pv_table_view.data)

    model = pv_table_view.model()
    index = model.index(row, LivePVHeader.STORED_VALUE)

    model.setData(index, input_data, QtCore.Qt.EditRole)

    # round-trip ensures types translate properly
    new_ser = apischema.serialize(type(pv_table_view.data), pv_table_view.data)
    new_data = apischema.deserialize(type(pv_table_view.data), new_ser)
    assert pv_table_view.data == new_data

    # data should not be the same as at beginning of test
    assert orig_data != pv_table_view.data
    assert orig_ser != new_ser


def test_stat_sev_enums(pv_table_view: LivePVTableView):
    model = pv_table_view.model()
    sev_index = model.index(0, LivePVHeader.STORED_SEVERITY)
    sev_delegate = pv_table_view.value_delegate.createEditor(
        pv_table_view, 0, sev_index
    )

    assert isinstance(sev_delegate, QtWidgets.QComboBox)
    assert sev_delegate.count() == len(Severity)
    for sev in Severity:
        assert sev_delegate.itemText(sev.value).lower() == sev.name.lower()

    stat_index = model.index(0, LivePVHeader.STORED_STATUS)
    stat_delegate = pv_table_view.value_delegate.createEditor(
        pv_table_view, 0, stat_index
    )

    assert isinstance(sev_delegate, QtWidgets.QComboBox)
    assert stat_delegate.count() == len(Status)
    for stat in Status:
        assert stat_delegate.itemText(stat.value).lower() == stat.name.lower()
