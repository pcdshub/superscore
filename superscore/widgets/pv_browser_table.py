from enum import Enum, auto
from typing import Any

from qtpy import QtCore

from superscore.model import Parameter


class PV_BROWSER_HEADER(Enum):
    DEVICE = 0
    PV = auto()
    DES = auto()
    TAGS = auto()

    def display_string(self) -> str:
        return self._strings[self]


# Must be added outside class def to avoid processing as an enum member
PV_BROWSER_HEADER._strings = {
    PV_BROWSER_HEADER.DEVICE: "Device",
    PV_BROWSER_HEADER.PV: "PV Name",
    PV_BROWSER_HEADER.DES: "DES",
    PV_BROWSER_HEADER.TAGS: "Tags",
}


class PVBrowserTableModel(QtCore.QAbstractTableModel):
    def __init__(self, client, parent=None):
        super().__init__(parent=parent)
        self.client = client
        self._data = list(self.client.search(
            ("entry_type", "eq", Parameter),
        ))

    def rowCount(self, parent=None) -> int:
        return len(self._data)

    def columnCount(self, parent=None) -> int:
        return len(PV_BROWSER_HEADER)

    def headerData(
        self,
        section: int,
        orientation: QtCore.Qt.Orientation,
        role: QtCore.Qt.ItemDataRole = QtCore.Qt.DisplayRole
    ) -> Any:
        if orientation == QtCore.Qt.Horizontal:
            if role == QtCore.Qt.DisplayRole:
                return PV_BROWSER_HEADER(section).display_string()
        return None

    def data(
        self,
        index: QtCore.QModelIndex,
        role: QtCore.Qt.ItemDataRole = QtCore.Qt.DisplayRole
    ) -> Any:
        if role not in (QtCore.Qt.DisplayRole, QtCore.Qt.ToolTipRole):
            return None

        entry = self._data[index.row()]
        column = PV_BROWSER_HEADER(index.column())
        if column == PV_BROWSER_HEADER.DEVICE:
            return None
        elif column == PV_BROWSER_HEADER.PV:
            return entry.pv_name
        elif column == PV_BROWSER_HEADER.DES:
            return None
        elif column == PV_BROWSER_HEADER.TAGS:
            return None
        return None
