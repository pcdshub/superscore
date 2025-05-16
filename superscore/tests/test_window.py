from uuid import UUID

import pytest
from pytestqt.qtbot import QtBot
from qtpy import QtWidgets

from superscore.backends.filestore import FilestoreBackend
from superscore.client import Client
from superscore.tests.conftest import setup_test_stack
from superscore.widgets.pv_browser_table import PVBrowserTableModel
from superscore.widgets.window import Window


def count_visible_items(tree_view):
    count = 0
    index = tree_view.model().index(0, 0)
    while index.isValid():
        count += 1
        print(type(index.internalPointer()._data).__name__)
        index = tree_view.indexBelow(index)
    return count


@setup_test_stack(sources=["db/filestore.json"], backend_type=FilestoreBackend)
def test_main_window(qtbot: QtBot, test_client: Client):
    """Pass if main window opens successfully"""
    window = Window(client=test_client)
    qtbot.addWidget(window)


@pytest.mark.skip(reason="Needs a working snapshot table to test, plus refactor")
@setup_test_stack(sources=["db/filestore.json"], backend_type=FilestoreBackend)
def test_take_snapshot(qtbot, test_client):
    window = Window(client=test_client)
    qtbot.addWidget(window)
    collection = tuple(test_client.search(("uuid", "eq", UUID("a9f289d4-3421-4107-8e7f-2fe0daab77a5"))))[0]
    snapshot = tuple(test_client.search(("uuid", "eq", UUID("ffd668d3-57d9-404e-8366-0778af7aee61"))))[0]

    collection_page = window.open_page(collection)
    new_snapshot = collection_page.take_snapshot()
    collection_page.children()[-1].done(1)
    search_result = tuple(test_client.search(("uuid", "eq", new_snapshot.uuid)))
    assert new_snapshot == search_result[0]

    snapshot_page = window.open_page(snapshot)
    result = snapshot_page.take_snapshot()
    assert result is None
    snapshot_page.close()

    snapshot.origin_collection = collection.uuid
    snapshot_page = window.open_page(snapshot)
    new_snapshot = snapshot_page.take_snapshot()
    snapshot_page.children()[-1].done(1)
    search_result = tuple(test_client.search(("uuid", "eq", new_snapshot.uuid)))
    assert new_snapshot == search_result[0]


@setup_test_stack(sources=["db/filestore.json"], backend_type=FilestoreBackend)
def test_pv_browser_model(test_client):
    pv_browser_model = PVBrowserTableModel(client=test_client)

    assert pv_browser_model.rowCount() == 4
    assert pv_browser_model.columnCount() == 4


@setup_test_stack(sources=["db/filestore.json"], backend_type=FilestoreBackend)
def test_pv_browser_search(qtbot, test_client):
    window = Window(client=test_client)
    qtbot.addWidget(window)

    pv_browser_filter = window.pv_browser_table.model()
    search_bar = window.pv_browser_page.findChild(QtWidgets.QLineEdit)
    assert isinstance(search_bar, QtWidgets.QLineEdit)

    assert pv_browser_filter.rowCount() == 4

    search_bar.setText("PREFIX")
    assert pv_browser_filter.rowCount() == 3
    search_bar.setText("test_str")
    assert pv_browser_filter.rowCount() == 0


@setup_test_stack(sources=["db/filestore.json"], backend_type=FilestoreBackend)
def test_nav_panel_expanded(qtbot, test_client):
    window = Window(client=test_client)
    qtbot.addWidget(window)

    window.navigation_panel.set_expanded(True)

    assert window.navigation_panel.view_snapshots_button.text() == "View Snapshots"
    assert window.navigation_panel.view_snapshots_button.property("icon-only") is False


@setup_test_stack(sources=["db/filestore.json"], backend_type=FilestoreBackend)
def test_nav_panel_collapsed(qtbot, test_client):
    window = Window(client=test_client)
    qtbot.addWidget(window)

    window.navigation_panel.set_expanded(False)

    assert window.navigation_panel.view_snapshots_button.text() == ""
    assert window.navigation_panel.view_snapshots_button.property("icon-only") is True


@setup_test_stack(sources=["db/filestore.json"], backend_type=FilestoreBackend)
def test_nav_panel_selected(qtbot, test_client):
    window = Window(client=test_client)
    qtbot.addWidget(window)

    assert window.navigation_panel.view_snapshots_button.property("selected") is True
    assert window.navigation_panel.browse_pvs_button.property("selected") is False

    window.navigation_panel.browse_pvs_button.click()

    assert window.navigation_panel.view_snapshots_button.property("selected") is False
    assert window.navigation_panel.browse_pvs_button.property("selected") is True
