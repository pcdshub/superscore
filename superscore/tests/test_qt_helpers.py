from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

import pytest
from pytestqt.qtbot import QtBot

from superscore.qt_helpers import (QDataclassBridge, QDataclassList,
                                   QDataclassValue)


@pytest.fixture(scope='function')
def bridge() -> QDataclassBridge:

    @dataclass
    class MyDataclass:
        int_field: int = 2
        bool_field: bool = True
        str_field: str = 'stringy'

        list_field: List[str] = field(default_factory=list)
        dict_field: Dict[str, Any] = field(default_factory=dict)
        optional_field: Optional[int] = None

        union_field: Union[str, int] = 'two'

    return QDataclassBridge(MyDataclass())


def test_bridge_creation(bridge: QDataclassBridge):
    # check correct bridge types were generated
    assert isinstance(bridge.int_field, QDataclassValue)
    assert 'int' in str(type(bridge.int_field))

    assert isinstance(bridge.bool_field, QDataclassValue)
    assert 'bool' in str(type(bridge.bool_field))

    assert isinstance(bridge.str_field, QDataclassValue)
    assert 'str' in str(type(bridge.str_field))

    assert isinstance(bridge.list_field, QDataclassList)
    assert 'str' in str(type(bridge.list_field))

    assert isinstance(bridge.dict_field, QDataclassValue)
    assert 'object' in str(type(bridge.dict_field))

    assert isinstance(bridge.optional_field, QDataclassValue)
    assert 'object' in str(type(bridge.optional_field))

    assert isinstance(bridge.union_field, QDataclassValue)
    assert 'object' in str(type(bridge.union_field))


def test_value_signals(qtbot: QtBot, bridge: QDataclassBridge):
    val = bridge.int_field

    assert val.get() == 2
    with qtbot.waitSignals([val.changed_value, val.updated]):
        val.put(3)

    assert val.get() == 3


def test_list_signals(qtbot: QtBot, bridge: QDataclassBridge):
    val = bridge.list_field

    assert val.get() == []

    with qtbot.waitSignals([val.added_value, val.added_index, val.updated]):
        val.append('one')
    assert val.get() == ['one']
    val.append('end')
    assert val.get() == ['one', 'end']

    with qtbot.waitSignals([val.changed_value, val.changed_index, val.updated]):
        val.put_to_index(0, 'zero')
    assert val.get() == ['zero', 'end']

    with qtbot.waitSignals([val.removed_value, val.removed_index, val.updated]):
        val.remove_index(0)
    assert val.get() == ['end']

    with qtbot.waitSignals([val.removed_value, val.removed_index, val.updated]):
        val.remove_value('end')
    assert val.get() == []
