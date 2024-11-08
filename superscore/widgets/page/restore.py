"""Page for inspecting, comparing, and restoring Snapshot values"""

import logging
from functools import partial

from qtpy import QtCore, QtWidgets
from qtpy.QtGui import QCloseEvent

from superscore.client import Client
from superscore.model import Snapshot
from superscore.widgets.core import Display
from superscore.widgets.views import (LivePVHeader, LivePVTableModel,
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

    def set_live(self, is_live: bool):
        self.secondarySnapshotLabel.setVisible(is_live)
        self.secondarySnapshotTitle.setText("Live Data")
        self.secondarySnapshotTitle.setVisible(is_live)
        self.compareLiveButton.setChecked(is_live)

    def closeEvent(self, a0: QCloseEvent) -> None:
        logging.debug("Closing SnapshotTableView")
        self.tableView.close()
        super().closeEvent(a0)
