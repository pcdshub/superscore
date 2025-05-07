from uuid import UUID

from qtpy import QtCore, QtGui

import superscore.color
from superscore.model import Readback, Setpoint
from superscore.widgets import SEVERITY_ICONS
from superscore.widgets.views import LivePVTableModel

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


# Must be added outside class def to avoid processing as an enum member
PV_HEADER._strings = {
    PV_HEADER.CHECKBOX: "",
    PV_HEADER.SEVERITY: "",
    PV_HEADER.DEVICE: "Device",
    PV_HEADER.PV: "PV Name",
    PV_HEADER.SETPOINT: "Saved Value",
    PV_HEADER.LIVE_SETPOINT: "Live Value",
    PV_HEADER.READBACK: "Saved Readback",
    PV_HEADER.LIVE_READBACK: "Live Readback",
    PV_HEADER.CONFIG: "CON",
}


class PVTableModel(LivePVTableModel):
    """A table model for representing PV data within a Snapshot. Includes live data."""

    def __init__(self, snapshot_id: UUID, client, parent=None):
        self.client = client
        self._data = list(self.client.search(
            ("ancestor", "eq", snapshot_id),
            ("entry_type", "eq", (Setpoint, Readback)),
        ))
        super().__init__(client=client, entries=self._data, parent=parent)

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(HEADER)

    def data(
        self,
        index: QtCore.QModelIndex,
        role: QtCore.Qt.ItemDataRole = QtCore.Qt.DisplayRole
    ):
        entry = self._data[index.row()]
        if role == QtCore.Qt.DisplayRole:
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
                    return self._get_live_data_field(entry, 'data')
                elif column == 5:
                    return entry.readback.data if entry.readback else None
                elif column == 6:
                    return self._get_live_data_field(entry.readback, 'data') if entry.readback else None
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
                    return self._get_live_data_field(entry, 'data')
                elif column == 7:
                    return None
                else:
                    return None
        elif role == QtCore.Qt.DecorationRole and index.column() == 0:
            icon = SEVERITY_ICONS[entry.severity]
            if icon is None:
                icon = SEVERITY_ICONS[entry.status]
            return icon
        elif role == QtCore.Qt.ForegroundRole and (index.column() == 4 or index.column() == 6):
            return QtGui.QColor(superscore.color.BLUE)
        elif role == QtCore.Qt.BackgroundRole and index.column() == 4:
            stored_data = getattr(entry, 'data', None)
            is_close = self.is_close(entry, stored_data)
            if stored_data is not None and not is_close:
                return QtGui.QColor(superscore.color.RED)
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
