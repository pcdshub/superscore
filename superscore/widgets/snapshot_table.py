from qtpy import QtCore

from superscore.model import Snapshot


class SnapshotTableModel(QtCore.QAbstractTableModel):
    """A table model containing all of the Snapshots available in a client"""

    HEADER = [
        "TIMESTAMP",
        "SNAPSHOT TITLE",
    ]

    def __init__(self, client, parent=None):
        super().__init__(parent)
        self.client = client
        self._data = []
        self.fetch()

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        meta_pvs = self.client.backend.get_meta_pvs()
        return len(self.HEADER) + len(meta_pvs)

    def data(
        self,
        index: QtCore.QModelIndex,
        role: QtCore.Qt.ItemDataRole = QtCore.Qt.DisplayRole
    ):
        column = index.column()
        if role == QtCore.Qt.DisplayRole:
            snapshot = self._data[index.row()]
            if column == 0:
                return snapshot.creation_time.strftime("%Y-%m-%d %H:%M:%S")
            elif column == 1:
                return snapshot.title
            else:
                try:
                    return snapshot.meta_pvs[column - len(self.HEADER)].data
                except IndexError:
                    return None
        elif role == QtCore.Qt.ToolTipRole and column >= 2:
            snapshot = self._data[index.row()]
            try:
                return snapshot.meta_pvs[column - len(self.HEADER)].pv_name
            except IndexError:
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
                try:
                    return self.HEADER[section]
                except IndexError:
                    meta_pvs = self.client.backend.get_meta_pvs()
                    return meta_pvs[section - len(self.HEADER)].description

    def fetch(self):
        """Fetch all snapshots from the backend"""
        self._data = sorted(
            self.client.search(("entry_type", "eq", Snapshot)),
            key=lambda s: s.creation_time,
            reverse=True,
        )

    def index_to_snapshot(self, index: QtCore.QModelIndex) -> Snapshot:
        """Convert a QModelIndex to a Snapshot object."""
        if not (index and index.isValid()):
            return None
        return self._data[index.row()]
