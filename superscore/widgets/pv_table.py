from enum import Enum, auto
from uuid import UUID

from qtpy import QtCore, QtGui

import superscore.color
from superscore.model import Readback, Setpoint
from superscore.widgets import SEVERITY_ICONS
from superscore.widgets.views import LivePVTableModel


class PV_HEADER(Enum):
    CHECKBOX = 0
    SEVERITY = auto()
    DEVICE = auto()
    PV = auto()
    SETPOINT = auto()
    LIVE_SETPOINT = auto()
    READBACK = auto()
    LIVE_READBACK = auto()
    CONFIG = auto()

    def display_string(self) -> str:
        return self._strings[self]


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
    """
    A table model for representing PV data within a Snapshot. Includes live data and checkboxes
    for selecting rows.
    """

    def __init__(self, snapshot_id: UUID, client, parent=None):
        self.client = client
        self._data = list(self.client.search(
            ("ancestor", "eq", snapshot_id),
            ("entry_type", "eq", (Setpoint, Readback)),
        ))
        self._checked = set()
        super().__init__(client=client, entries=self._data, parent=parent)

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(PV_HEADER)

    def headerData(
        self,
        section: int,
        orientation: QtCore.Qt.Orientation,
        role: QtCore.Qt.ItemDataRole = QtCore.Qt.DisplayRole
    ):
        if orientation == QtCore.Qt.Horizontal:
            if role == QtCore.Qt.DisplayRole:
                return PV_HEADER(section).display_string()

    def flags(self, index) -> QtCore.Qt.ItemFlags:
        column = PV_HEADER(index.column())
        if column == PV_HEADER.CHECKBOX:
            return QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled
        else:
            return super().flags(index)

    def data(
        self,
        index: QtCore.QModelIndex,
        role: QtCore.Qt.ItemDataRole = QtCore.Qt.DisplayRole
    ):
        entry = self._data[index.row()]
        column = PV_HEADER(index.column())
        if role == QtCore.Qt.DisplayRole:
            if isinstance(entry, Setpoint):
                if column == PV_HEADER.CHECKBOX:
                    pass
                elif column == PV_HEADER.SEVERITY:
                    return None
                elif column == PV_HEADER.DEVICE:
                    return None
                elif column == PV_HEADER.PV:
                    return entry.pv_name
                elif column == PV_HEADER.SETPOINT:
                    return entry.data
                elif column == PV_HEADER.LIVE_SETPOINT:
                    return self._get_live_data_field(entry, 'data')
                elif column == PV_HEADER.READBACK:
                    return entry.readback.data if entry.readback else None
                elif column == PV_HEADER.LIVE_READBACK:
                    return self._get_live_data_field(entry.readback, 'data') if entry.readback else None
                elif column == PV_HEADER.CONFIG:
                    return None
                else:
                    return None
            else:
                if column == PV_HEADER.SEVERITY:
                    return None
                elif column == PV_HEADER.DEVICE:
                    return None
                elif column == PV_HEADER.PV:
                    return entry.pv_name
                elif column == PV_HEADER.SETPOINT:
                    return None
                elif column == PV_HEADER.LIVE_SETPOINT:
                    return None
                elif column == PV_HEADER.READBACK:
                    return entry.data
                elif column == PV_HEADER.LIVE_READBACK:
                    return self._get_live_data_field(entry, 'data')
                elif column == PV_HEADER.CONFIG:
                    return None
                else:
                    return None
        elif role == QtCore.Qt.CheckStateRole and column == PV_HEADER.CHECKBOX:
            return index.row() in self._checked
        elif role == QtCore.Qt.DecorationRole and column == PV_HEADER.SEVERITY:
            icon = SEVERITY_ICONS[entry.severity]
            if icon is None:
                icon = SEVERITY_ICONS[entry.status]
            return icon
        elif role == QtCore.Qt.ForegroundRole and column in [PV_HEADER.LIVE_SETPOINT, PV_HEADER.LIVE_READBACK]:
            return QtGui.QColor(superscore.color.BLUE)
        elif role == QtCore.Qt.BackgroundRole and column == PV_HEADER.LIVE_SETPOINT:
            stored_data = getattr(entry, 'data', None)
            is_close = self.is_close(entry, stored_data)
            if stored_data is not None and not is_close:
                return QtGui.QColor(superscore.color.RED)
            else:
                return None
        elif role == QtCore.Qt.TextAlignmentRole and column not in [PV_HEADER.DEVICE, PV_HEADER.PV]:
            return QtCore.Qt.AlignCenter
        else:
            return None

    def setData(self, index, value, role) -> bool:
        if role == QtCore.Qt.CheckStateRole and PV_HEADER(index.column()) == PV_HEADER.CHECKBOX:
            try:
                self._checked.remove(index.row())
            except KeyError:
                self._checked.add(index.row())
            self.dataChanged.emit(index, index)
        return True
