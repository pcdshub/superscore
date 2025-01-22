import copy
from typing import Any
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import apischema
import pytest
from pytestqt.qtbot import QtBot
from qtpy import QtCore, QtWidgets

from superscore.backends.test import TestBackend
from superscore.client import Client
from superscore.control_layers import EpicsData
from superscore.model import (Collection, Nestable, Parameter, Root, Severity,
                              Status)
from superscore.tests.conftest import nest_depth, setup_test_stack
from superscore.widgets.views import (CustRoles, EntryItem, LivePVHeader,
                                      LivePVTableModel, LivePVTableView,
                                      NestableTableView, RootTree,
                                      RootTreeView)


@pytest.fixture(scope='function')
def pv_poll_model(
    test_client: Client,
    parameter_with_readback: Parameter,
    qtbot: QtBot
):
    """Minimal LivePVTableModel, containing only Parameters (no stored data)"""
    model = LivePVTableModel(
        client=test_client,
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
    test_client: Client,
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
                              lower_ctrl_limit=-2, upper_ctrl_limit=2),
        "MY:INT": EpicsData(data=1, lower_ctrl_limit=-10, upper_ctrl_limit=10),
        "MY:ENUM": EpicsData(data=0, enums=["OUT", "IN", "UNKNOWN"])
    }

    def simple_coll_return_vals(pv_name: str):
        return ret_vals[pv_name]

    test_client.cl.get = MagicMock(side_effect=simple_coll_return_vals)

    view = LivePVTableView()
    view.client = test_client
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


def test_fill_uuids_pvs(
    test_client: Client,
    simple_snapshot: Collection,
    qtbot: QtBot,
):
    """Verify UUID data gets filled, and dataclass gets modified"""
    simple_snapshot.swap_to_uuids()
    assert all(isinstance(c, UUID) for c in simple_snapshot.children)
    view = LivePVTableView()
    # mock client does not ever return None, as if entries are always found
    # in the backend
    view.client = test_client
    view.set_data(simple_snapshot)

    assert all(not isinstance(c, UUID) for c in simple_snapshot.children)
    print(view.model()._poll_thread)
    view.model().stop_polling()
    print(view.model()._poll_thread)
    qtbot.wait_until(lambda: not view.model()._poll_thread.isRunning())


def test_fill_uuids_nestable(
    test_client: Client,
    linac_backend: TestBackend,
):
    """Verify UUID data gets filled, and dataclass gets modified"""
    nested_coll = linac_backend.get_entry("441ff79f-4948-480e-9646-55a1462a5a70")
    nested_coll.swap_to_uuids()
    assert all(isinstance(c, UUID) for c in nested_coll.children)
    view = NestableTableView()
    # mock client does not ever return None, as if entries are always found
    # in the backend.  (entries will be "filled" with mock data)
    view.client = test_client
    view.set_data(nested_coll)

    assert all(not isinstance(c, UUID) for c in nested_coll.children)


@setup_test_stack(sources=['linac_data'], backend_type=TestBackend)
def test_fill_uuids_entry_item(test_client: Client, qtbot: QtBot):
    nested_coll = test_client.backend.get_entry("441ff79f-4948-480e-9646-55a1462a5a70")
    assert not all(isinstance(c, UUID) for c in nested_coll.children)
    # should have a nest depth of 4
    nested_coll.swap_to_uuids()
    assert all(isinstance(c, UUID) for c in nested_coll.children)

    # hack: make all of linac_backend flat
    for entry in test_client.backend._entry_cache.values():
        entry.swap_to_uuids()

    tree_model = RootTree(base_entry=nested_coll, client=test_client)
    original_depth = nest_depth(tree_model.root_item)
    # default fill depth is 2, so children and their children get EntryItems
    assert original_depth == 2

    # fill just the first child
    # fill depth can depend on how the backend returns data.  Backend may not
    # be lazy, so we assert only child1's children have EntryItems
    root_item = tree_model.root_item
    child1 = root_item.child(0)
    assert child1.child(0).childCount() == 0
    child1.fill_uuids(test_client)
    assert child1.child(0).childCount() > 0
    assert root_item.child(1).child(0).childCount() == 0
    assert root_item.child(2).child(0).childCount() == 0

    # filling only occurs if direct children are UUIDs, does nothing here
    # since it was originally filled by RootTree
    root_item.fill_uuids(test_client)
    assert root_item.child(0).child(0).childCount() > 0
    assert root_item.child(1).child(0).childCount() == 0
    assert root_item.child(2).child(0).childCount() == 0


def test_roottree_setup(sample_database: Root):
    tree_model = RootTree(base_entry=sample_database)
    root_index = tree_model.index_from_item(tree_model.root_item)
    # Check that the entire tree was created
    assert tree_model.rowCount(root_index) == 4
    assert tree_model.root_item.child(3).childCount() == 3


@setup_test_stack(sources=['db/filestore.json'], backend_type=TestBackend)
def test_root_tree_view_setup_init_args(test_client: Client):
    tree_view = RootTreeView(
        client=test_client,
        entry=test_client.backend.root
    )
    assert isinstance(tree_view.model().root_item, EntryItem)
    assert isinstance(tree_view.model(), RootTree)


@setup_test_stack(sources=['db/filestore.json'], backend_type=TestBackend)
def test_root_tree_view_setup_post_init(test_client: Client):
    tree_view = RootTreeView()
    tree_view.client = test_client
    tree_view.set_data(test_client.backend.root)

    assert isinstance(tree_view.model().root_item, EntryItem)
    assert isinstance(tree_view.model(), RootTree)


@setup_test_stack(sources=['db/filestore.json'], backend_type=TestBackend)
def test_root_tree_fetchmore(test_client: Client):
    tree_view = RootTreeView()
    tree_view.client = test_client
    for entry in test_client.backend.root.entries:
        entry.swap_to_uuids()
    tree_view.set_data(test_client.backend.root)

    model: RootTree = tree_view.model()
    child_index = model.index_from_item(model.root_item.child(2))
    # check that we have filling to do
    assert isinstance(child_index.internalPointer()._data, Nestable)
    assert any(isinstance(child, UUID) for child
               in child_index.internalPointer()._data.children)

    assert model.canFetchMore(child_index)
    model.fetchMore(child_index)
    assert not model.canFetchMore(child_index)

    # Swap EntryItem children to uuids, confirm we re-attempt to fetch
    for child in child_index.internalPointer()._children:
        child._data = uuid4()

    assert model.canFetchMore(child_index)
    model.fetchMore(child_index)
    assert not model.canFetchMore(child_index)

    # Swap dataclass children to uuids, confirm we re-attempt to fetch
    child_index.internalPointer()._data.swap_to_uuids()

    assert model.canFetchMore(child_index)
    model.fetchMore(child_index)
    assert not model.canFetchMore(child_index)
