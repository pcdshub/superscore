from qtpy import QtCore

from superscore.model import Snapshot

HEADER = [
    "TIMESTAMP",
    "SNAPSHOT TITLE",
]


class SnapshotTableModel(QtCore.QAbstractTableModel):
    """A table model containing all of the Snapshots available in a client"""

    def __init__(self, client, parent=None):
        super().__init__(parent)
        self.client = client
        self._data = list(self.client.search(
            ("entry_type", "eq", Snapshot),
        ))

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(HEADER)

    def data(
        self,
        index: QtCore.QModelIndex,
        role: QtCore.Qt.ItemDataRole = QtCore.Qt.DisplayRole
    ):
        if role == QtCore.Qt.DisplayRole:
            entry = self._data[index.row()]
            if (column := index.column()) == 0:
                return entry.creation_time.strftime("%Y-%m-%d %H:%M:%S")
            elif column == 1:
                return entry.title
            else:
                return None
        else:
            return None

    def headerData(
        self,
        section: int,
        orientation: QtCore.Qt.Orientation,
        role: QtCore.Qt.ItemDataRole = QtCore.Qt.DisplayRole
    ):
        if orientation == QtCore.Qt.Horizontal:
            if role == QtCore.Qt.DisplayRole:
                return HEADER[section]
