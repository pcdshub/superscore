"""
Core widget classes for qt-based GUIs.
"""
from __future__ import annotations

from pathlib import Path
from typing import ClassVar, List
from weakref import WeakValueDictionary

from pcdsutils.qt.designer_display import DesignerDisplay
from qtpy import QtWidgets

from superscore.qt_helpers import QDataclassBridge, QDataclassList
from superscore.type_hints import AnyDataclass
from superscore.utils import SUPERSCORE_SOURCE_PATH


class Display(DesignerDisplay):
    """Helper class for loading designer .ui files and adding logic"""

    ui_dir: Path = SUPERSCORE_SOURCE_PATH / 'ui'


class DataWidget(QtWidgets.QWidget):
    """
    Base class for widgets that manipulate dataclasses.

    Defines the init args for all data widgets and handles synchronization
    of the ``QDataclassBridge`` instances. This is done so that only data
    widgets need to consider how to handle bridges and the page classes
    simply need to pass in data structures, rather than needing to keep track
    of how two widgets editing the same data structure must share the same
    bridge object.

    Parameters
    ----------
    data : any dataclass
        The dataclass that the widget needs to manipulate. Most widgets are
        expecting either specific dataclasses or dataclasses that have
        specific matching fields.
    kwargs : QWidget kwargs
        Passed directly to QWidget's __init__. Likely unused in most cases.
        Even parent is unlikely to see use because parent is set automatically
        when a widget is inserted into a layout.
    """
    # QDataclassBridge for this widget, other bridges may live in TreeItem
    _bridge_cache: ClassVar[
        WeakValueDictionary[int, QDataclassBridge]
    ] = WeakValueDictionary()
    bridge: QDataclassBridge
    data: AnyDataclass

    def __init__(self, data: AnyDataclass, **kwargs):
        super().__init__(**kwargs)
        self.data = data
        try:
            # TODO figure out better way to cache these
            # TODO worried about strange deallocation timing race conditions
            self.bridge = self._bridge_cache[id(data)]
        except KeyError:
            bridge = QDataclassBridge(data)
            self._bridge_cache[id(data)] = bridge
            self.bridge = bridge
