from uuid import UUID

import pytest
from pytestqt.qtbot import QtBot

from superscore.backends.filestore import FilestoreBackend
from superscore.client import Client
from superscore.tests.conftest import setup_test_stack
from superscore.widgets.page.collection_builder import CollectionBuilderPage
from superscore.widgets.page.entry import (CollectionPage, ParameterPage,
                                           SetpointPage, SnapshotPage)
from superscore.widgets.views import EntryItem
from superscore.widgets.window import Window


def count_visible_items(tree_view):
    count = 0
    index = tree_view.model().index(0, 0)
    while index.isValid():
        count += 1
        print(type(index.internalPointer()._data).__name__)
        index = tree_view.indexBelow(index)
    return count


@setup_test_stack(sources=['db/filestore.json'], backend_type=FilestoreBackend)
def test_main_window(qtbot: QtBot, test_client: Client):
    """Pass if main window opens successfully"""
    window = Window(client=test_client)
    qtbot.addWidget(window)


@setup_test_stack(sources=['db/filestore.json'], backend_type=FilestoreBackend)
def test_sample_window(qtbot: QtBot, test_client: Client):
    window = Window(client=test_client)
    qtbot.addWidget(window)

    assert count_visible_items(window.tree_view) == 4

    def get_last_index(index):
        curr_index = index
        while curr_index.isValid():
            new_index = window.tree_view.indexBelow(curr_index)
            if not new_index.isValid():
                break
            curr_index = new_index
        return curr_index

    first_index = window.tree_view.model().index(0, 0)
    last_index = get_last_index(first_index)
    # expand does not fetch more data by itself
    window.tree_view.expand(last_index)
    window.tree_view.model().fetchMore(last_index)

    assert count_visible_items(window.tree_view) == 7

    # get new last index after expansion, and signal view has been updated
    new_last_index = get_last_index(first_index)
    window.tree_view.dataChanged(first_index, new_last_index)

    # check that all exposed entries have been filled
    index = first_index
    while index.isValid():
        assert not isinstance(index.internalPointer()._data, UUID)
        index = window.tree_view.indexBelow(index)


@setup_test_stack(sources=['db/filestore.json'], backend_type=FilestoreBackend)
def test_add_collection_refresh(qtbot: QtBot, test_client: Client):
    window = Window(client=test_client)
    qtbot.addWidget(window)

    window.open_collection_builder()

    coll_builder_page = window.tab_widget.widget(1)
    assert isinstance(coll_builder_page, CollectionBuilderPage)
    orig_entry_item: EntryItem = window.tree_view.model().root_item
    orig_top_level_entries = orig_entry_item.childCount()

    coll_builder_page.save_collection()

    new_entry_item: EntryItem = window.tree_view.model().root_item
    new_top_level_entries = new_entry_item.childCount()

    assert new_top_level_entries > orig_top_level_entries
    coll_builder_page.close()
    qtbot.waitUntil(coll_builder_page.sub_pv_table_view._model._poll_thread.isFinished)


@setup_test_stack(sources=["db/filestore.json"], backend_type=FilestoreBackend)
def test_take_snapshot(qtbot: QtBot, test_client):
    window = Window(client=test_client)
    qtbot.addWidget(window)
    collection = tuple(test_client.search(("uuid", "eq", UUID("a9f289d4-3421-4107-8e7f-2fe0daab77a5"))))[0]
    snapshot = tuple(test_client.search(("uuid", "eq", UUID("ffd668d3-57d9-404e-8366-0778af7aee61"))))[0]

    collection_page = window.open_page(collection)
    new_snapshot = collection_page.take_snapshot()
    collection_page.children()[-1].done(1)
    search_result = tuple(test_client.search(("uuid", 'eq', new_snapshot.uuid)))
    assert new_snapshot == search_result[0]

    snapshot_page = window.open_page(snapshot)
    assert isinstance(snapshot_page, SnapshotPage)
    result = snapshot_page.take_snapshot()
    assert result is None
    snapshot_page.close()
    qtbot.waitUntil(snapshot_page.sub_pv_table_view._model._poll_thread.isFinished)

    snapshot.origin_collection = collection.uuid
    snapshot_page = window.open_page(snapshot)
    assert isinstance(snapshot_page, SnapshotPage)
    new_snapshot = snapshot_page.take_snapshot()
    snapshot_page.children()[-1].done(1)
    search_result = tuple(test_client.search(("uuid", 'eq', new_snapshot.uuid)))
    assert new_snapshot == search_result[0]
    snapshot_page.close()
    qtbot.waitUntil(snapshot_page.sub_pv_table_view._model._poll_thread.isFinished)


@pytest.mark.parametrize("editable,", [True, False])
@setup_test_stack(sources=["db/filestore.json"], backend_type=FilestoreBackend)
def test_open_page_editability(qtbot, test_client: Client, editable: bool,):
    """Test that opened pages respect the editability provided by the client"""
    test_client.enable_editing_past = editable
    window = Window(client=test_client)
    qtbot.addWidget(window)
    collection = tuple(test_client.search(
        ("uuid", "eq", UUID("a9f289d4-3421-4107-8e7f-2fe0daab77a5"))
    ))[0]
    snapshot = tuple(test_client.search(
        ("uuid", "eq", UUID("ffd668d3-57d9-404e-8366-0778af7aee61"))
    ))[0]
    setpoint = tuple(test_client.search(
        ("uuid", "eq", UUID("be3c5e5c-faca-4b19-ab6c-70323abc9f24"))
    ))[0]
    parameter = tuple(test_client.search(
        ("uuid", "eq", UUID("514790d9-3261-4583-a326-9be08d7edf48"))
    ))[0]

    for entry, page_cls in zip(
        [collection, snapshot, setpoint, parameter],
        [CollectionPage, SnapshotPage, SetpointPage, ParameterPage]
    ):
        page = window.open_page(entry)
        assert isinstance(page, page_cls)
        assert page.editable == editable
        # close the polling loops so we don't wait for them all at once
        page.close()
