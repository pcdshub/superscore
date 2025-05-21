"""Page for inspecting, comparing, and restoring Snapshot values"""

import logging

from qtpy import QtCore

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
