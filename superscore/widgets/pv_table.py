from uuid import UUID

from qtpy import QtCore

from superscore.model import Readback, Setpoint

HEADER = [
    "Severity",
    "Device",
    "PV Name",
    "Saved Value",
    "Live Value",
    "Saved Readback",
    "Live Readback",
    "CON",
]


class PVTableModel(QtCore.QAbstractTableModel):
    """"""

    def __init__(self, snapshot_id: UUID, client, parent=None):
        super().__init__(parent)
        self.client = client
        self._data = list(self.client.search(
            ("ancestor", "eq", snapshot_id),
            ("entry_type", "eq", (Setpoint, Readback)),
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
            if isinstance(entry, Setpoint):
                if (column := index.column()) == 0:
                    return None
                elif column == 1:
                    return None
                elif column == 2:
                    return entry.pv_name
                elif column == 3:
                    return entry.data
                elif column == 4:
                    return None
                elif column == 5:
                    return entry.readback.data if entry.readback else None
                elif column == 6:
                    return None
                elif column == 7:
                    return None
                else:
                    return None
            else:
                if (column := index.column()) == 0:
                    return None
                elif column == 1:
                    return None
                elif column == 2:
                    return entry.pv_name
                elif column == 3:
                    return None
                elif column == 4:
                    return None
                elif column == 5:
                    return entry.data
                elif column == 6:
                    return None
                elif column == 7:
                    return None
                else:
                    return None
        elif role == QtCore.Qt.TextAlignmentRole and index.column() > 2:
            return QtCore.Qt.AlignCenter
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
