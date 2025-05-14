from enum import Enum, auto
from typing import Any

from qtpy import QtCore

from superscore.model import Parameter

NO_DATA = "--"


class PV_BROWSER_HEADER(Enum):
    DEVICE = 0
    PV = auto()
    READBACK = auto()
    TAGS = auto()

    def display_string(self) -> str:
        return self._strings[self]


# Must be added outside class def to avoid processing as an enum member
PV_BROWSER_HEADER._strings = {
    PV_BROWSER_HEADER.DEVICE: "Device",
    PV_BROWSER_HEADER.PV: "PV Name",
    PV_BROWSER_HEADER.READBACK: "Readback",
    PV_BROWSER_HEADER.TAGS: "Tags",
}


class PVBrowserTableModel(QtCore.QAbstractTableModel):
    def __init__(self, client, parent=None):
        super().__init__(parent=parent)
        self.client = client
        self._data = list(self.client.search(
            ("entry_type", "eq", Parameter),
        ))

    def rowCount(self, _=QtCore.QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, _=QtCore.QModelIndex()) -> int:
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
        if not index.isValid():
            return None
        elif role == QtCore.Qt.TextAlignmentRole and index.data() == NO_DATA:
            return QtCore.Qt.AlignCenter
        elif role == QtCore.Qt.ToolTipRole:
            entry = self._data[index.row()]
            return entry.pv_name
        elif role == QtCore.Qt.DisplayRole:
            entry = self._data[index.row()]
            column = PV_BROWSER_HEADER(index.column())
            if column == PV_BROWSER_HEADER.DEVICE:
                return None
            elif column == PV_BROWSER_HEADER.PV:
                return entry.pv_name
            elif column == PV_BROWSER_HEADER.READBACK:
                return entry.readback.pv_name if entry.readback else NO_DATA
            elif column == PV_BROWSER_HEADER.TAGS:
                return None
        return None


class PVBrowserFilterProxyModel(QtCore.QSortFilterProxyModel):
    def __init__(self, parent=None, tags=None):
        super().__init__(parent=parent)
        self.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.setFilterKeyColumn(PV_BROWSER_HEADER.PV.value)

        self.tags = tags

    def setTags(self, tags) -> None:
        self.tags = tags
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QtCore.QModelIndex) -> bool:
        # TODO: Implement filtering logic based on tags
        return super().filterAcceptsRow(source_row, source_parent)
