from operator import attrgetter
from typing import Any
from uuid import uuid4

import pytest
from pytestqt.qtbot import QtBot

from superscore.model import Collection
from superscore.widgets.core import DataWidget, TagsWidget


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


def test_tags_widget(qtbot):
    tag_groups = {
        0: (
            "Dest",
            "Which endpoint the beam is directed towards",
            {
                0: "SXR",
                1: "HXR",
            }
        )
    }

    widget = TagsWidget(tag_groups=tag_groups, enabled=True)
    qtbot.addWidget(widget)

    assert widget.layout().count() == 1

    chip = widget.layout().itemAt(0).widget()
    assert len(chip.tags) == 0

    selection_model = chip.editor.choice_list.selectionModel()
    Select = selection_model.Select
    index = selection_model.model().index(0, 0)
    selection_model.select(index, Select)
    index = selection_model.model().index(1, 0)
    selection_model.select(index, Select)
    assert len(chip.tags) == 2
    assert "SXR" in chip.label.text()
    assert "HXR" in chip.label.text()

    Deselect = selection_model.Deselect
    selection_model.select(index, Deselect)
    assert len(chip.tags) == 1
    assert "SXR" in chip.label.text()
    assert "HXR" not in chip.label.text()

    chip.clear()
    assert len(chip.tags) == 0
    assert "SXR" not in chip.label.text()
    assert "HXR" not in chip.label.text()
