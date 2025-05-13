"""Largely smoke tests for various pages"""

from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from pytestqt.qtbot import QtBot
from qtpy import QtCore, QtWidgets

from superscore.backends.filestore import FilestoreBackend
from superscore.client import Client
from superscore.control_layers._base_shim import EpicsData
from superscore.model import (Collection, Parameter, Readback, Setpoint,
                              Snapshot)
from superscore.tests.conftest import setup_test_stack
from superscore.widgets.page.collection_builder import CollectionBuilderPage
from superscore.widgets.page.diff import DiffPage
from superscore.widgets.page.entry import (BaseParameterPage, CollectionPage,
                                           ParameterPage, ReadbackPage,
                                           SetpointPage, SnapshotPage)
from superscore.widgets.page.restore import RestoreDialog, RestorePage
from superscore.widgets.page.search import SearchPage


@pytest.fixture(scope='function')
def collection_page(qtbot: QtBot, test_client: Client):
    data = Collection()
    page = CollectionPage(data=data, client=test_client)
    qtbot.addWidget(page)
    yield page

    view = page.sub_pv_table_view
    view._model.stop_polling()
    qtbot.wait_until(lambda: not view._model._poll_thread.isRunning())


@pytest.fixture(scope="function")
def snapshot_page(qtbot: QtBot, test_client: Client):
    data = Snapshot()
    page = SnapshotPage(data=data, client=test_client)
    qtbot.addWidget(page)
    yield page

    view = page.sub_pv_table_view
    view._model.stop_polling()
    qtbot.wait_until(lambda: not view._model._poll_thread.isRunning())


@pytest.fixture(scope="function")
def parameter_page(qtbot: QtBot, test_client: Client):
    data = Parameter()
    page = ParameterPage(data=data, client=test_client)
    qtbot.addWidget(page)
    return page


@pytest.fixture(scope="function")
def setpoint_page(qtbot: QtBot, test_client: Client):
    data = Setpoint()
    page = SetpointPage(data=data, client=test_client)
    qtbot.addWidget(page)
    return page


@pytest.fixture(scope="function")
def readback_page(qtbot: QtBot, test_client: Client):
    data = Readback()
    page = ReadbackPage(data=data, client=test_client)
    qtbot.addWidget(page)
    return page


@pytest.fixture(scope='function')
def search_page(qtbot: QtBot, test_client: Client):
    page = SearchPage(client=test_client)
    qtbot.addWidget(page)
    return page


@pytest.fixture(scope="function")
def collection_builder_page(qtbot: QtBot, test_client: Client):
    page = CollectionBuilderPage(client=test_client)
    qtbot.addWidget(page)
    yield page
    page.close()
    qtbot.waitUntil(lambda: page.sub_pv_table_view._model._poll_thread.isFinished())


@pytest.fixture(scope="function")
def restore_page(
    qtbot: QtBot,
    test_client: Client,
    simple_snapshot_fixture: Snapshot
):
    page = RestorePage(data=simple_snapshot_fixture, client=test_client)
    qtbot.addWidget(page)
    yield page
    page.close()


@pytest.fixture
def diff_page(qtbot: QtBot, test_client: Client):
    l_snapshot = Snapshot(
        title="l_snap",
        description="l desc",
        children=[
            Setpoint(pv_name="MY:SET", data=1),
            Readback(pv_name="MY:RBV", data=1),
        ]
    )
    r_snapshot = Snapshot(
        title="r_snap",
        description="r desc",
        children=[
            Setpoint(pv_name="MY:SET", data=2),
            Readback(pv_name="MY:RBV", data=1),
            Readback(pv_name="MY:RBV2", data=2),
        ]
    )
    page = DiffPage(
        client=test_client,
        l_entry=l_snapshot,
        r_entry=r_snapshot,
    )
    qtbot.addWidget(page)
    yield page
    page.close()


@pytest.mark.parametrize(
    'page',
    [
        "parameter_page",
        "setpoint_page",
        "readback_page",
        "collection_page",
        "snapshot_page",
        "search_page",
        "collection_builder_page",
        "restore_page",
        "diff_page",
    ]
)
def test_page_smoke(page: str, request: pytest.FixtureRequest):
    """smoke test, just create each page and see if they fail"""
    print(type(request.getfixturevalue(page)))


@setup_test_stack(sources=["db/filestore.json"], backend_type=FilestoreBackend)
def test_apply_filter(test_client, search_page: SearchPage):
    search_page.start_dt_edit.setDate(QtCore.QDate(2024, 5, 10))
    search_page.apply_filter_button.clicked.emit()
    assert search_page.results_table_view.model().rowCount() == 6

    search_page.snapshot_checkbox.setChecked(False)
    search_page.apply_filter_button.clicked.emit()
    assert search_page.results_table_view.model().rowCount() == 5

    search_page.readback_checkbox.setChecked(False)
    search_page.apply_filter_button.clicked.emit()
    assert search_page.results_table_view.model().rowCount() == 2

    search_page.setpoint_checkbox.setChecked(False)
    search_page.apply_filter_button.clicked.emit()
    assert search_page.results_table_view.model().rowCount() == 1

    # reset and try name filter
    for box in search_page.type_checkboxes:
        box.setChecked(True)
    search_page.apply_filter_button.clicked.emit()
    assert search_page.results_table_view.model().rowCount() == 6

    search_page.name_line_edit.setText('collection 1')
    search_page.apply_filter_button.clicked.emit()
    assert search_page.results_table_view.model().rowCount() == 1


@setup_test_stack(sources=["db/filestore.json"], backend_type=FilestoreBackend)
def test_coll_builder_add(test_client, collection_builder_page: CollectionBuilderPage):
    page = collection_builder_page

    page.pv_line_edit.setText("THIS:PV")
    page.add_pvs_button.clicked.emit()

    assert len(page.data.children) == 1
    assert "THIS:PV" in page.data.children[0].pv_name
    assert isinstance(page.data.children[0], Parameter)
    assert page.sub_pv_table_view._model.rowCount() == 1

    page.coll_combo_box.setCurrentIndex(0)
    added_collection = page._coll_options[0]
    page.add_collection_button.clicked.emit()
    assert added_collection is page.data.children[1]
    assert page.sub_coll_table_view._model.rowCount() == 1


@setup_test_stack(sources=["db/filestore.json"], backend_type=FilestoreBackend)
def test_coll_builder_edit(
    test_client,
    collection_builder_page: CollectionBuilderPage,
    qtbot: QtBot
):
    page = collection_builder_page

    page.pv_line_edit.setText("THIS:PV")
    page.add_pvs_button.clicked.emit()

    pv_model = page.sub_pv_table_view.model()
    qtbot.waitUntil(lambda: pv_model.rowCount() == 1)
    assert "THIS:PV" in page.data.children[0].pv_name

    first_index = pv_model.createIndex(0, 0)
    pv_model.setData(first_index, "NEW:VP", role=QtCore.Qt.EditRole)

    assert "NEW:VP" in page.data.children[0].pv_name

    page.add_collection_button.clicked.emit()

    coll_model = page.sub_coll_table_view.model()
    qtbot.waitUntil(lambda: coll_model.rowCount() == 1)

    coll_model.setData(first_index, 'anothername', role=QtCore.Qt.EditRole)
    qtbot.waitUntil(lambda: "anothername" in page.data.children[1].title)


@pytest.mark.parametrize("page_fixture,", ["parameter_page", "setpoint_page"])
def test_open_page_slot(
    page_fixture: str,
    request: pytest.FixtureRequest,
):
    with patch("superscore.widgets.page.entry.BaseParameterPage.open_page_slot",
               new_callable=PropertyMock):
        page: BaseParameterPage = request.getfixturevalue(page_fixture)
        page.open_rbv_button.clicked.emit()
        assert page.open_page_slot.called


@pytest.mark.parametrize(
    "page_fixture,",
    ["parameter_page", "setpoint_page", "readback_page"]
)
def test_stored_widget_swap(
    page_fixture: str,
    request: pytest.FixtureRequest,
    qtbot: QtBot,
):
    ret_vals = {
        "MY:FLOAT": EpicsData(data=0.5, precision=3,
                              lower_ctrl_limit=-2, upper_ctrl_limit=2),
        "MY:INT": EpicsData(data=1, lower_ctrl_limit=-10, upper_ctrl_limit=10),
        "MY:ENUM": EpicsData(data=0, enums=["OUT", "IN", "UNKNOWN"])
    }

    def simple_coll_return_vals(pv_name: str):
        return ret_vals[pv_name]

    page: BaseParameterPage = request.getfixturevalue(page_fixture)
    page.set_editable(True)
    page.client.cl.get = MagicMock(side_effect=simple_coll_return_vals)
    qtbot.waitUntil(lambda: not page._edata_thread.isRunning())
    page.get_edata()
    qtbot.waitUntil(lambda: not page._edata_thread.isRunning())

    for pv, expected_widget in zip(
        ret_vals,
        (QtWidgets.QDoubleSpinBox, QtWidgets.QSpinBox, QtWidgets.QComboBox)
    ):
        page.pv_edit.setText(pv)
        qtbot.waitUntil(lambda: page.data.pv_name == pv)
        page.refresh_button.clicked.emit()

        qtbot.waitUntil(
            lambda: isinstance(page.value_stored_widget, expected_widget),
        )


def test_restore_page_toggle_live(qtbot: QtBot, restore_page):
    tableView = restore_page.tableView
    live_columns = tableView.live_headers
    toggle_live_button = restore_page.compareLiveButton

    toggle_live_button.click()
    qtbot.waitUntil(lambda: tableView._model._poll_thread.running)
    qtbot.waitUntil(lambda: all((not tableView.isColumnHidden(column) for column in live_columns)))

    toggle_live_button.click()
    qtbot.waitUntil(lambda: all((tableView.isColumnHidden(column) for column in live_columns)))


@setup_test_stack(sources=["db/filestore.json"], backend_type=FilestoreBackend)
def test_restore_dialog_restore(
    test_client: Client,
    simple_snapshot_fixture: Snapshot,
):
    put_mock = test_client.cl.put
    dialog = RestoreDialog(test_client, simple_snapshot_fixture)
    dialog.restore()
    assert put_mock.call_args.args == test_client._gather_data(simple_snapshot_fixture)


@setup_test_stack(sources=["db/filestore.json"], backend_type=FilestoreBackend)
def test_restore_dialog_remove_pv(
    test_client: Client,
    simple_snapshot_fixture: Snapshot
):
    dialog = RestoreDialog(test_client, simple_snapshot_fixture)
    tableWidget = dialog.tableWidget
    assert tableWidget.rowCount() == len(simple_snapshot_fixture.children)

    PV_COLUMN = 0
    REMOVE_BUTTON_COLUMN = 2
    item_to_remove = tableWidget.item(1, PV_COLUMN)
    tableWidget.setCurrentCell(1, REMOVE_BUTTON_COLUMN)
    dialog.delete_row()
    assert tableWidget.rowCount() == len(simple_snapshot_fixture.children) - 1
    items_left = [tableWidget.item(row, PV_COLUMN) for row in range(tableWidget.rowCount())]
    assert item_to_remove not in items_left
