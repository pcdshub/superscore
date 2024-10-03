"""Largely smoke tests for various pages"""

import pytest
from pytestqt.qtbot import QtBot
from qtpy import QtCore

from superscore.client import Client
from superscore.model import Collection, Parameter
from superscore.widgets.page.collection_builder import CollectionBuilderPage
from superscore.widgets.page.entry import CollectionPage
from superscore.widgets.page.search import SearchPage


@pytest.fixture(scope='function')
def collection_page(qtbot: QtBot):
    data = Collection()
    page = CollectionPage(data=data)
    qtbot.addWidget(page)
    return page


@pytest.fixture(scope='function')
def search_page(qtbot: QtBot, sample_client: Client):
    page = SearchPage(client=sample_client)
    qtbot.addWidget(page)
    return page


@pytest.fixture(scope="function")
def collection_builder_page(qtbot: QtBot, sample_client: Client):
    page = CollectionBuilderPage(client=sample_client)
    qtbot.addWidget(page)
    yield page
    page.close()
    qtbot.waitUntil(lambda: page.sub_pv_table_view._model._poll_thread.isFinished())


@pytest.mark.parametrize(
    'page',
    ["collection_page", "search_page", "collection_builder_page"]
)
def test_page_smoke(page: str, request: pytest.FixtureRequest):
    """smoke test, just create each page and see if they fail"""
    print(type(request.getfixturevalue(page)))


def test_apply_filter(search_page: SearchPage):
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


def test_coll_builder_add(collection_builder_page: CollectionBuilderPage):
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


def test_coll_builder_edit(
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
