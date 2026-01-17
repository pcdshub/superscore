from operator import attrgetter
from typing import Any
from uuid import uuid4

import pytest
from pytestqt.qtbot import QtBot

from superscore.model import Collection
from superscore.widgets.core import DataWidget


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

    # signals inside of widget are called
    signal1 = attrgetter('.'.join((attr, signal)))(widget1.bridge)
    # but other widgets referencing the "same data" are not called
    signal2 = attrgetter('.'.join((attr, signal)))(widget2.bridge)
    with qtbot.assertNotEmitted(signal2):
        with qtbot.waitSignal(signal1):
            getattr(widget1.bridge, attr).put(value)

    # widgets maintain their own deep copies, so DataWidget referencing same data
    # will need to be independently updated
    assert getattr(data, attr) != value

    qtbot.addWidget(widget1)
    qtbot.addWidget(widget2)
