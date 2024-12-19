from uuid import UUID

from pytestqt.qtbot import QtBot

from superscore.backends.filestore import FilestoreBackend
from superscore.client import Client
from superscore.tests.conftest import setup_test_stack
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
