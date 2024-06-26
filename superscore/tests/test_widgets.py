from operator import attrgetter
from typing import Any
from uuid import uuid4

import pytest
from pytestqt.qtbot import QtBot

from superscore.model import Collection, Root
from superscore.widgets.core import DataWidget
from superscore.widgets.tree import RootTree


@pytest.mark.parametrize(
    'attr, signal, value',
    [
        ('title', 'changed_value', 'new_title'),
        ('title', 'updated', 'new_title'),
        ('children', 'updated', [Collection(), Collection()]),
        ('uuid', 'changed_value', uuid4()),
    ]
)
def test_collection_datawidget_bridge(
    qtbot: QtBot,
    attr: str,
    signal: str,
    value: Any
):
    data = Collection()
    widget1 = DataWidget(data=data)
    widget2 = DataWidget(data=data)

    assert getattr(data, attr) != value

    signal = attrgetter('.'.join((attr, signal)))(widget2.bridge)
    with qtbot.waitSignal(signal):
        getattr(widget1.bridge, attr).put(value)

    assert getattr(data, attr) == value

    qtbot.addWidget(widget1)
    qtbot.addWidget(widget2)


def test_roottree_setup(sample_database: Root):
    tree_model = RootTree(base_entry=sample_database)
    root_index = tree_model.index_from_item(tree_model.root_item)
    # Check that the entire tree was created
    assert tree_model.rowCount(root_index) == 4
    assert tree_model.root_item.child(3).childCount() == 3
