"""Page for inspecting, comparing, and restoring Snapshot values"""

import logging
from enum import auto
from functools import partial

from qtpy import QtCore, QtWidgets
from qtpy.QtGui import QCloseEvent

from superscore.client import Client
from superscore.model import Setpoint, Snapshot
from superscore.widgets.core import Display
from superscore.widgets.views import (BaseDataTableView, HeaderEnum,
                                      LivePVHeader, LivePVTableModel,
                                      LivePVTableView)

logger = logging.getLogger(__name__)


class SnapshotTableModel(LivePVTableModel):
    """Model specific to showing and comparing PVs in Snapshots"""
    def data(self, index: QtCore.QModelIndex, role: int):
        if role == QtCore.Qt.TextAlignmentRole:
            return QtCore.Qt.AlignCenter
        else:
            return super().data(index, role)


class SnapshotTableView(LivePVTableView):
    """Table view specific to showing and comparing PVs in Snapshots"""
    live_headers = {LivePVHeader.LIVE_VALUE, LivePVHeader.LIVE_STATUS, LivePVHeader.LIVE_SEVERITY}

    turnOnLive = QtCore.Signal()
    turnOffLive = QtCore.Signal()

    def __init__(self, *args, start_live: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self._model_cls = SnapshotTableModel
        self._is_live = start_live
        self.setColumnHidden(LivePVHeader.STORED_SEVERITY, True)
        self.setColumnHidden(LivePVHeader.STORED_STATUS, True)

    def gather_sub_entries(self) -> None:
        self.sub_entries = self.client._gather_leaves(self.data)

    @QtCore.Slot()
    def set_live(self, state: bool):
        self._is_live = state
        for live_header in self.live_headers:
            self.setColumnHidden(live_header, not self._is_live)
        if self._is_live:
            self.turnOnLive.emit()
        else:
            self.turnOffLive.emit()

    @QtCore.Slot()
    def toggle_live(self):
        self.set_live(not self._is_live)


class RestoreDialog(Display, QtWidgets.QWidget):
    """A dialog for selecting PVs to write to the EPICS system"""

    filename = "restore_dialog.ui"

    cancelButton: QtWidgets.QPushButton
    restoreButton: QtWidgets.QPushButton

    tableWidget: QtWidgets.QTableWidget

    def __init__(self, client: Client, snapshot: Snapshot = None):
        super().__init__()
        self.client = client
        if snapshot is None:
            self.entries = []
        else:
            self.entries = [entry for entry in client._gather_leaves(snapshot) if isinstance(entry, Setpoint)]

        self.tableWidget.setRowCount(len(self.entries))
        self.tableWidget.setColumnCount(3)
        for row, entry in enumerate(self.entries):
            pv_item = QtWidgets.QTableWidgetItem(entry.pv_name)
            self.tableWidget.setItem(row, 0, pv_item)

            value_item = QtWidgets.QTableWidgetItem(str(entry.data))
            value_item.setTextAlignment(QtCore.Qt.AlignCenter)
            self.tableWidget.setItem(row, 1, value_item)

            remove_item = QtWidgets.QPushButton("Remove")
            remove_item.clicked.connect(self.delete_row)
            self.tableWidget.setCellWidget(row, 2, remove_item)

        self.restoreButton.clicked.connect(self.restore)
        self.cancelButton.clicked.connect(self.deleteLater)

    def restore(self):
        ephemeral_snapshot = Snapshot(children=self.entries)
        self.client.apply(ephemeral_snapshot)
        self.close()

    def delete_row(self) -> None:
        row = self.tableWidget.currentRow()
        self.entries.pop(row)
        self.tableWidget.removeRow(row)


class CompareHeader(HeaderEnum):
    PV_NAME = 0
    PRIMARY_VALUE = auto()
    SECONDARY_VALUE = auto()
    PRIMARY_TIMESTAMP = auto()
    SECONDARY_TIMESTAMP = auto()
    # TODO: Find another way to represent status and severity
    #   Potentially as a border color or icon
    PRIMARY_STATUS = auto()
    SECONDARY_STATUS = auto()
    PRIMARY_SEVERITY = auto()
    SECONDARY_SEVERITY = auto()
    PRIMARY_OPEN = auto()
    SECONDARY_OPEN = auto()


class CompareSnapshotTableModel(QtCore.QAbstractTableModel):

    def __init__(
        self,
        *args,
        client: Client,
        primary_snapshot: Snapshot = None,
        comparison_snapshot: Snapshot = None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.headers = [h.header_name() for h in CompareHeader]
        self.client = client
        self._primary_data = primary_snapshot
        self._secondary_data = comparison_snapshot
        self.entries = []

    def _collate_pvs(self) -> None:
        self.entries = []
        # for each PV in primary snapshot, find partner in secondary snapshot
        pvs = self.client.search(
            ("entry_type", "eq", Setpoint),
            ("ancestor", "eq", self._primary_data.uuid),
        )
        seen = set()
        for primary in pvs:
            secondary_generator = self.client.search(
                ("pv_name", "eq", primary.pv_name),
                ("ancestor", "eq", self._secondary_data.uuid),
            )
            secondary = tuple(secondary_generator)[0]  # assumes at most one match
            self.entries.append((primary, secondary))
            seen.add(secondary.uuid)
        # for each PV in secondary with no partner in primary, add row with 'None' partner
        pvs = self.client.search(
            ("entry_type", "eq", Setpoint),
            ("ancestor", "eq", self._secondary_data.uuid),
        )
        for secondary in pvs:
            if secondary.uuid not in seen:
                self.entries.append((None, secondary))

    def data(self, index: QtCore.QModelIndex, role: int):
        if role == QtCore.Qt.TextAlignmentRole:
            return QtCore.Qt.AlignCenter
        elif role == QtCore.Qt.DisplayRole:
            primary, secondary = self.entries[index.row()]
            match index.column():
                case CompareHeader.PV_NAME:
                    return primary.pv_name
                case CompareHeader.PRIMARY_VALUE:
                    return primary.data
                case CompareHeader.SECONDARY_VALUE:
                    return secondary.data
                case CompareHeader.PRIMARY_TIMESTAMP:
                    return primary.creation_time
                case CompareHeader.SECONDARY_TIMESTAMP:
                    return secondary.creation_time
                case CompareHeader.PRIMARY_STATUS:
                    return primary.status
                case CompareHeader.SECONDARY_STATUS:
                    return secondary.status
                case CompareHeader.PRIMARY_SEVERITY:
                    return primary.severity
                case CompareHeader.SECONDARY_SEVERITY:
                    return secondary.severity
                case CompareHeader.PRIMARY_OPEN:
                    return None
                case CompareHeader.SECONDARY_OPEN:
                    return None
        else:
            return None

    def rowCount(self):
        return len(self.entries)

    def columnCount(self):
        return len(self.headers)

    def headerData(
        self,
        section: int,
        orientation: QtCore.Qt.Orientation,
        role: QtCore.Qt.ItemDataRole = QtCore.Qt.DisplayRole
    ) -> str:
        """
        Returns the header data for the model.
        Currently only displays horizontal header data
        """
        if role != QtCore.Qt.DisplayRole:
            return

        if orientation == QtCore.Qt.Horizontal:
            return self.headers[section]

    @QtCore.Slot()
    def set_comparison_snapshot(self, comparison_snapshot: Snapshot) -> None:
        self._secondary_data = comparison_snapshot
        self._collate_pvs()


class CompareSnapshotTableView(BaseDataTableView):

    setCompareSnapshot = QtCore.Signal(Snapshot)

    def __init__(self, *args, **kwargs):
        pass

    def gather_sub_entries(self):
        model = self.model()
        model._collate_pvs()
        self.sub_entries = model.entries


class LiveButton(QtWidgets.QPushButton):
    """A button for toggling the status of live data on a SnapshotTableModel"""
    labels = ["Compare to Live", "Turn off Live"]

    def setChecked(self, state: bool):
        """Set button's check status. Check status is semantically connected to
        whether the button turns a SnapshotTableView's live data on or off"""
        super().setChecked(state)
        new_label = self.labels[int(state)]
        self.setText(new_label)


class RestorePage(Display, QtWidgets.QWidget):
    """A page for inspecting, comparing, and restoring Snapshot PV values"""

    filename = 'restore_page.ui'

    headerFrame: QtWidgets.QFrame
    primarySnapshotLabel: QtWidgets.QLabel
    primarySnapshotTitle: QtWidgets.QLabel
    secondarySnapshotLabel: QtWidgets.QLabel
    secondarySnapshotTitle: QtWidgets.QLabel
    compareLiveButton: QtWidgets.QPushButton
    compareSnapshotButton: QtWidgets.QPushButton
    restoreButton: QtWidgets.QPushButton

    tableView: SnapshotTableView

    def __init__(
        self,
        *args,
        data: Snapshot,
        client: Client,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.client = client

        self.snapshot = data
        self.tableView.client = self.client
        self.tableView.set_data(data)
        self.tableView.hideColumn(LivePVHeader.REMOVE)

        self.compareLiveButton.clicked.connect(self.tableView.toggle_live)
        self.tableView.turnOnLive.connect(partial(self.set_live, True))
        self.tableView.turnOffLive.connect(partial(self.set_live, False))
        self.tableView.set_live(False)

        header = self.tableView.horizontalHeader()
        header.setSectionResizeMode(header.Stretch)

        self.primarySnapshotLabel.setText("Viewing:")
        self.primarySnapshotTitle.setText(data.title)
        self.secondarySnapshotLabel.setText("Comparing:")
        self.secondarySnapshotLabel.hide()
        self.secondarySnapshotTitle.hide()

        self.restoreButton.clicked.connect(self.launch_dialog)

    def set_live(self, is_live: bool):
        self.secondarySnapshotLabel.setVisible(is_live)
        self.secondarySnapshotTitle.setText("Live Data")
        self.secondarySnapshotTitle.setVisible(is_live)
        self.compareLiveButton.setChecked(is_live)

    def launch_dialog(self):
        self.dialog = RestoreDialog(self.client, self.snapshot)
        self.dialog.restoreButton.clicked.connect(partial(self.tableView.set_live, True))
        self.dialog.show()

    def closeEvent(self, a0: QCloseEvent) -> None:
        logging.debug("Closing SnapshotTableView")
        self.tableView.close()
        super().closeEvent(a0)
