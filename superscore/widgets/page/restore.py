"""Page for inspecting, comparing, and restoring Snapshot values"""

import logging
from functools import partial

from qtpy import QtWidgets
from qtpy.QtGui import QCloseEvent

from superscore.client import Client
from superscore.model import Snapshot
from superscore.widgets.core import Display
from superscore.widgets.views import LivePVHeader, LivePVTableView

logger = logging.getLogger(__name__)


class SnapshotTableView(LivePVTableView):
    """Table view specific to showing and comparing PVs in Snapshots"""
    live_headers = {LivePVHeader.LIVE_VALUE, LivePVHeader.LIVE_STATUS, LivePVHeader.LIVE_SEVERITY}

    def gather_sub_entries(self) -> None:
        self.sub_entries = self.client._gather_leaves(self.data)


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
        self.set_live(False)
        header = self.tableView.horizontalHeader()
        header.setSectionResizeMode(header.Stretch)

        self.primarySnapshotLabel.setText("Viewing:")
        self.primarySnapshotTitle.setText(data.title)
        self.secondarySnapshotLabel.setText("Comparing:")
        self.secondarySnapshotLabel.hide()
        self.secondarySnapshotTitle.hide()

    def set_live(self, is_live: bool):
        for live_header in self.tableView.live_headers:
            self.tableView.setColumnHidden(live_header, not is_live)

        self.compareLiveButton.setText(["Compare to Live", "Turn off Live"][int(is_live)])
        self.compareLiveButton.clicked.connect(partial(self.set_live, not is_live))

        self.secondarySnapshotLabel.setVisible(is_live)
        self.secondarySnapshotTitle.setText("Live Data")
        self.secondarySnapshotTitle.setVisible(is_live)

    def closeEvent(self, a0: QCloseEvent) -> None:
        logging.debug("Closing SnapshotTableView")
        self.tableView.close()
        super().closeEvent(a0)
