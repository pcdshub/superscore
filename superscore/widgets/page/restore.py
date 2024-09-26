"""Page for comparing and restoring Snapshot values"""

import logging
from uuid import UUID

from qtpy import QtCore, QtWidgets
from qtpy.QtGui import QCloseEvent

from superscore.client import Client
from superscore.model import Readback, Setpoint, Snapshot
from superscore.widgets.core import Display
from superscore.widgets.views import LivePVTableModel

logger = logging.getLogger(__name__)


class Restore(Display, QtWidgets.QWidget):
    """
    """

    filename = 'restore.ui'

    headerFrame: QtWidgets.QFrame
    snapshotLabel: QtWidgets.QLabel
    compareLiveButton: QtWidgets.QPushButton
    compareSnapshotButton: QtWidgets.QPushButton

    dockWidget: QtWidgets.QDockWidget
    tableView: QtWidgets.QTableView

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
        pv_list = self.gather_pvs(self.snapshot)
        logger.debug(f"RESTORE: Found {len(pv_list)} PVs in {self.snapshot.uuid}")
        self.model = Model(client=self.client, entries=pv_list)
        self.tableView.setModel(self.model)
        header = self.tableView.horizontalHeader()
        header.setSectionResizeMode(header.Stretch)

    def gather_pvs(self, snapshot: Snapshot):
        pvs = []
        seen = set()
        q = [snapshot]
        while len(q) > 0:
            entry = q.pop()
            uuid = entry if isinstance(entry, UUID) else entry.uuid
            if uuid in seen:
                continue
            elif isinstance(entry, UUID):
                entry = self.client.backend.get_entry(entry)
            seen.add(entry.uuid)

            if isinstance(entry, Snapshot):
                q.extend(reversed(entry.children))  # preserve execution order
            elif isinstance(entry, (Setpoint, Readback)):
                pvs.append(entry)
            else:
                raise TypeError(f"Found {type(entry).__name__} {entry.uuid} in a Snapshot")
        return pvs

    def closeEvent(self, a0: QCloseEvent) -> None:
        logger.debug("Stopping pv_model polling")
        self.model.stop_polling(wait_time=5000)
        super().closeEvent(a0)


class Model(LivePVTableModel):
    """"""
    def data(self, index: QtCore.QModelIndex, role: int):
        if role == QtCore.Qt.TextAlignmentRole:
            return QtCore.Qt.AlignCenter
        else:
            return super().data(index, role)
