"""Page for inspecting, comparing, and restoring Snapshot values"""

import logging
from functools import partial
from typing import Any, Optional

from qtpy import QtCore, QtWidgets
from qtpy.QtGui import QCloseEvent

from superscore.client import Client
from superscore.model import Setpoint, Snapshot
from superscore.widgets.core import Display
from superscore.widgets.manip_helpers import insert_widget
from superscore.widgets.views import (ButtonDelegate, LivePVHeader,
                                      LivePVTableModel, LivePVTableView)

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


class RestoreDialogModel(QtCore.QAbstractTableModel):
    headers = ["PV Name", "Value to Restore", "Remove"]

    def __init__(self, *args, entries: list[Setpoint], **kwargs):
        super().__init__(*args, **kwargs)
        self.entries = entries

    def rowCount(self, parent: Optional[QtCore.QModelIndex] = None):
        return len(self.entries)

    def columnCount(self, parent: Optional[QtCore.QModelIndex] = None):
        return 3

    def headerData(
        self,
        section: int,
        orientation: QtCore.Qt.Orientation,
        role: int = QtCore.Qt.DisplayRole
    ) -> Any:
        """
        Returns the header data for the model.
        Currently only displays horizontal header data
        """
        if role != QtCore.Qt.DisplayRole:
            return

        if orientation == QtCore.Qt.Horizontal:
            return self.headers[section]

    def data(self, index: QtCore.QModelIndex, role: int = QtCore.Qt.DisplayRole) -> Any:
        entry = self.entries[index.row()]

        if role != QtCore.Qt.DisplayRole:
            return

        match index.column():
            case 0:
                return entry.pv_name
            case 1:
                return entry.data
            case 2:
                return "Click to Remove"

    def flags(self, index: QtCore.QModelIndex) -> QtCore.Qt.ItemFlags:
        """
        Returns the item flags for the given ``index``.  Set delegates editable
        """
        if index.column() != 2:
            return QtCore.Qt.ItemIsEnabled

        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable

    def removeRow(self, row: int, parent: QtCore.QModelIndex = ...) -> bool:
        self.beginRemoveRows(QtCore.QModelIndex(), row, row)
        self.entries.pop(row)
        self.endRemoveRows()


class RestoreDialogView(QtWidgets.QTableView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setup_ui()

    def setup_ui(self):
        self.remove_delegate = ButtonDelegate(button_text='Remove')
        self.setItemDelegateForColumn(2, self.remove_delegate)
        self.remove_delegate.clicked.connect(self.remove_row)
        self.horizontalHeader().setStretchLastSection(True)

    def remove_row(self, index: QtCore.QModelIndex) -> None:
        self.model().removeRow(index.row())


class RestoreDialog(Display, QtWidgets.QWidget):
    """A dialog for selecting PVs to write to the EPICS system"""

    filename = "restore_dialog.ui"

    cancel_button: QtWidgets.QPushButton
    restore_all_button: QtWidgets.QPushButton
    restore_batch_button: QtWidgets.QPushButton

    batch_size_spinbox: QtWidgets.QSpinBox

    table_view_placeholder: QtWidgets.QWidget
    table_view: QtWidgets.QTableView

    def __init__(self, client: Client, snapshot: Snapshot = None):
        super().__init__()
        self.client = client
        if snapshot is None:
            self.entries = []
        else:
            self.entries = [entry for entry in client._gather_leaves(snapshot)
                            if isinstance(entry, Setpoint)]
        self._set_batch_limits()

        self.table_view = RestoreDialogView()
        self.table_view.setModel(RestoreDialogModel(entries=self.entries))

        insert_widget(self.table_view, self.table_view_placeholder)

        self.cancel_button.clicked.connect(self.deleteLater)
        self.restore_all_button.clicked.connect(self.restore_all)
        self.restore_batch_button.clicked.connect(self.restore_batch)

    def restore_all(self):
        ephemeral_snapshot = Snapshot(children=self.entries)
        self.client.apply(ephemeral_snapshot)
        self.close()

    def _set_batch_limits(self):
        self.batch_size_spinbox.setMinimum(1)
        self.batch_size_spinbox.setMaximum(len(self.entries))

    def restore_batch(self):
        batch_size = self.batch_size_spinbox.value()
        ephemeral_snapshot = Snapshot(children=self.entries[:batch_size])
        self.client.apply(ephemeral_snapshot)
        for _ in range(batch_size):
            self.table_view.model().removeRow(0)


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
        self.dialog.restore_all_button.clicked.connect(partial(self.tableView.set_live, True))
        self.dialog.show()

    def closeEvent(self, a0: QCloseEvent) -> None:
        logging.debug("Closing SnapshotTableView")
        self.tableView.close()
        super().closeEvent(a0)
