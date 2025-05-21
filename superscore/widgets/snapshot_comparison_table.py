from enum import Enum, auto
from uuid import UUID

from qtpy import QtCore

from superscore.model import Readback, Setpoint, Snapshot


class COMPARE_HEADER(Enum):
    CHECKBOX = 0
    SEVERITY = auto()
    COMPARE_SEVERITY = auto()
    DEVICE = auto()
    PV = auto()
    SETPOINT = auto()
    COMPARE_SETPOINT = auto()
    READBACK = auto()
    COMPARE_READBACK = auto()

    def display_string(self) -> str:
        return self._strings[self]


COMPARE_HEADER._strings = {
    COMPARE_HEADER.CHECKBOX: "",
    COMPARE_HEADER.SEVERITY: "",
    COMPARE_HEADER.COMPARE_SEVERITY: "",
    COMPARE_HEADER.DEVICE: "Device",
    COMPARE_HEADER.PV: "PV Name",
    COMPARE_HEADER.SETPOINT: "Saved Value",
    COMPARE_HEADER.COMPARE_SETPOINT: "Comparison Value",
    COMPARE_HEADER.READBACK: "Saved Readback",
    COMPARE_HEADER.COMPARE_READBACK: "Comparison Readback",
}


class SnapshotComparisonTableModel(QtCore.AbstractTableModel):
    """
    A table model for representing PV data within a Snapshot. Includes live data and checkboxes
    for selecting rows.
    """
    def __init__(self, main_snapshot: Snapshot, client, parent=None):
        super().__init__(parent)
        self.client = client
        self._data = []

        self.main_snapshot = main_snapshot
        self.comparison_snapshot = None

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(COMPARE_HEADER)

    def headerData(
        self,
        section: int,
        orientation: QtCore.Qt.Orientation,
        role: QtCore.Qt.ItemDataRole = QtCore.Qt.DisplayRole
    ) -> str:
        if orientation == QtCore.Qt.Horizontal:
            if role == QtCore.Qt.DisplayRole:
                return COMPARE_HEADER(section).display_string()

    def _collate_pvs(self) -> None:
        """Get all PVs for the snapshots to be compared."""
        self.beginResetModel()
        self._data = []
        # for each PV in primary snapshot, find partner in secondary snapshot
        pvs = self.client.search(
            ("entry_type", "eq", (Setpoint, Readback)),
            ("ancestor", "eq", self.main_snapshot.uuid),
        )
        seen = set()
        for primary in tuple(pvs):
            secondary_generator = self.client.search(
                ("pv_name", "eq", primary.pv_name),
                ("entry_type", "eq", type(primary)),
                ("ancestor", "eq", self.comparison_snapshot.uuid),
            )
            try:
                secondary = tuple(secondary_generator)[0]  # assumes at most one match
            except IndexError:
                secondary = None

            self._data.append((primary, secondary))
            if secondary:
                seen.add(secondary.uuid)
        # for each PV in secondary with no partner in primary, add row with 'None' partner
        pvs = self.client.search(
            ("entry_type", "eq", (Setpoint, Readback)),
            ("ancestor", "eq", self.comparison_snapshot.uuid),
        )
        for secondary in pvs:
            if secondary.uuid not in seen:
                self._data.append((None, secondary))
        self.endResetModel()

    def set_main_snapshot(self, main_snapshot: UUID) -> None:
        """Set the main snapshot and update the model."""
        self.main_snapshot = main_snapshot
        self._collate_pvs()

    def set_comparison_snapshot(self, comparison_snapshot: UUID) -> None:
        """Set the comparison snapshot and update the model."""
        self.comparison_snapshot = comparison_snapshot
        self._collate_pvs()
