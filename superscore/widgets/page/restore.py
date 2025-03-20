"""Page for inspecting, comparing, and restoring Snapshot values"""

import logging
from enum import auto
from functools import partial
from typing import Dict, List, Optional, Union

from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtGui import QCloseEvent

from superscore.client import Client
from superscore.model import Entry, Readback, Setpoint, Snapshot
from superscore.widgets.core import Display
from superscore.widgets.views import (BaseDataTableView, BaseTableEntryModel,
                                      HeaderEnum, LivePVHeader,
                                      LivePVTableModel, LivePVTableView,
                                      RootTree)

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
        self.setColumnHidden(LivePVHeader.REMOVE, True)

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


class SnapshotSelectionDialog(QtWidgets.QDialog):
    def __init__(self, parent: QtCore.QObject, client: Client, exclude_snapshot: Snapshot = None):
        super().__init__(parent)

        self._selectedSnapshot = None

        if exclude_snapshot:
            header_text = "Select a snapshot to compare to:"
        else:
            header_text = "Select a snapshot:"
        header_lbl = QtWidgets.QLabel(header_text)

        self.tree_model = RootTree(base_entry=client.backend.root,
                                   client=client)
        self.tree_view = QtWidgets.QTreeView(self)
        self.tree_view.setModel(self.tree_model)
        self.tree_view.setExpandsOnDoubleClick(False)
        self.tree_view.doubleClicked.connect(self.accept)

        btns = QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        buttonBox = QtWidgets.QDialogButtonBox(btns)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(header_lbl)
        layout.addWidget(self.tree_view)
        layout.addWidget(buttonBox)
        self.setLayout(layout)

    @property
    def selectedSnapshot(self):
        try:
            selected_index = self.tree_view.selectedIndexes()[0]
        except IndexError:
            return None
        self._selectedSnapshot = selected_index.internalPointer()._data
        return self._selectedSnapshot


class CompareHeader(HeaderEnum):
    PV_NAME = 0
    VALUE = auto()
    COMPARE_VALUE = auto()
    TIMESTAMP = auto()
    COMPARE_TIMESTAMP = auto()
    # TODO: Find another way to represent status and severity
    #   Potentially as a border color or icon
    STATUS = auto()
    COMPARE_STATUS = auto()
    SEVERITY = auto()
    COMPARE_SEVERITY = auto()


class CompareSnapshotTableModel(BaseTableEntryModel):
    _diff_color = QtGui.QColor('#ffbbbb')
    _header_to_field: Dict[CompareHeader, str] = {
        CompareHeader.PV_NAME: 'pv_name',
        CompareHeader.VALUE: 'data',
        CompareHeader.COMPARE_VALUE: 'data',
        CompareHeader.STATUS: 'status',
        CompareHeader.COMPARE_STATUS: 'status',
        CompareHeader.SEVERITY: 'severity',
        CompareHeader.COMPARE_SEVERITY: 'severity',
    }

    def __init__(
        self,
        *args,
        client: Client,
        primary_snapshot: Snapshot = None,
        secondary_snapshot: Snapshot = None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.headers = [h.header_name() for h in CompareHeader]
        self.header_enum = CompareHeader
        self.client = client
        self._primary_data = primary_snapshot
        self._secondary_data = secondary_snapshot
        self.entries: List[Entry] = []

    def _collate_pvs(self) -> None:
        self.beginResetModel()
        self.entries = []
        # for each PV in primary snapshot, find partner in secondary snapshot
        pvs = self.client.search(
            ("entry_type", "eq", (Setpoint, Readback)),
            ("ancestor", "eq", self._primary_data.uuid),
        )
        seen = set()
        for primary in tuple(pvs):
            secondary_generator = self.client.search(
                ("pv_name", "eq", primary.pv_name),
                ("ancestor", "eq", self._secondary_data.uuid),
            )
            secondary = tuple(secondary_generator)[0]  # assumes at most one match
            self.entries.append((primary, secondary))
            seen.add(secondary.uuid)
        # for each PV in secondary with no partner in primary, add row with 'None' partner
        pvs = self.client.search(
            ("entry_type", "eq", (Setpoint, Readback)),
            ("ancestor", "eq", self._secondary_data.uuid),
        )
        for secondary in pvs:
            if secondary.uuid not in seen:
                self.entries.append((None, secondary))
        self.endResetModel()

    def data(self, index: QtCore.QModelIndex, role: int):
        if role not in (QtCore.Qt.TextAlignmentRole, QtCore.Qt.DisplayRole,
                        QtCore.Qt.BackgroundRole, QtCore.Qt.ToolTipRole):
            return None

        if role == QtCore.Qt.TextAlignmentRole:
            return QtCore.Qt.AlignCenter

        if not self.is_compare_column(index):
            entry, compare = self.entries[index.row()]
        elif self.is_compare_column(index):
            compare, entry = self.entries[index.row()]

        if not entry:
            return "--"

        column = index.column()
        if column == CompareHeader.PV_NAME and role in (QtCore.Qt.DisplayRole, QtCore.Qt.ToolTipRole):
            return entry.pv_name
        elif column in (CompareHeader.VALUE, CompareHeader.COMPARE_VALUE):
            if role in (QtCore.Qt.DisplayRole, QtCore.Qt.ToolTipRole):
                return entry.data
            elif role == QtCore.Qt.BackgroundRole and self.is_compare_column(index):
                return self._diff_color if entry.data != compare.data else None
        elif column in (CompareHeader.TIMESTAMP, CompareHeader.COMPARE_TIMESTAMP):
            if role in (QtCore.Qt.DisplayRole, QtCore.Qt.ToolTipRole):
                return entry.creation_time.strftime('%Y/%m/%d %H:%M')
            elif role == QtCore.Qt.BackgroundRole and self.is_compare_column(index):
                return self._diff_color if entry.creation_time != compare.creation_time else None
        elif column in (CompareHeader.STATUS, CompareHeader.COMPARE_STATUS):
            if role in (QtCore.Qt.DisplayRole, QtCore.Qt.ToolTipRole):
                status = getattr(entry, 'status', '--')
                return getattr(status, 'name', status)
            elif role == QtCore.Qt.BackgroundRole and self.is_compare_column(index):
                return self._diff_color if entry.status != compare.status else None
        elif column in (CompareHeader.SEVERITY, CompareHeader.COMPARE_SEVERITY):
            if role in (QtCore.Qt.DisplayRole, QtCore.Qt.ToolTipRole):
                severity = getattr(entry, 'severity', '--')
                return getattr(severity, 'name', severity)
            elif role == QtCore.Qt.BackgroundRole and self.is_compare_column(index):
                return self._diff_color if entry.severity != compare.severity else None

    def rowCount(self, parent_index: Optional[QtCore.QModelIndex] = None):
        return len(self.entries)

    def columnCount(self, parent_index: Optional[QtCore.QModelIndex] = None):
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

    def is_compare_column(self, index: Union[int, QtCore.QModelIndex]):
        if isinstance(index, QtCore.QModelIndex):
            index = index.column()
        hdr = self.headers[index]
        return hdr.startswith("Compare")

    @QtCore.Slot()
    def set_comparison_snapshot(self, comparison_snapshot: Snapshot) -> None:
        self._secondary_data = comparison_snapshot
        self._collate_pvs()


class CompareSnapshotTableView(BaseDataTableView):

    setCompareSnapshot = QtCore.Signal(Snapshot)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._model_cls = CompareSnapshotTableModel
        self._primary = None
        self._secondary = None

    def setup_ui(self):
        """initialize basic ui elements for this table"""
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.create_context_menu_at_pos)

    def set_primary(self, primary: Snapshot):
        """Set the data for this view, re-setup ui"""
        if not isinstance(primary, Snapshot):
            raise ValueError(
                f"Attempted to set an incompatable data type ({type(primary)})"
            )
        self._primary = primary
        self.maybe_setup_model()

    def set_secondary(self, secondary: Snapshot):
        """Set the data for this view, re-setup ui"""
        if not isinstance(secondary, Snapshot):
            raise ValueError(
                f"Attempted to set an incompatable data type ({type(secondary)})"
            )
        if self._model is None:
            self.maybe_setup_model()
        try:
            self._model.set_comparison_snapshot(secondary)
        except AttributeError:
            logger.debug(f"{self._model_cls} cannot be initialized")

    def maybe_setup_model(self):
        if self.client is None:
            logger.debug("Client not set, cannot initialize model")
            return

        if self._primary is None:
            logger.debug("data not set, cannot initialize model")
            return

        if self._model is None:
            self._model = self._model_cls(
                client=self.client,
                primary_snapshot=self._primary,
                **self.model_kwargs
            )
            self.setModel(self._model)
        else:
            self._model.set_comparison_snapshot(self._secondary)


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
    compareTableView: CompareSnapshotTableView

    def __init__(
        self,
        *args,
        data: Snapshot,
        client: Client,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.client = client

        self.show_compare = False
        self.snapshot = data
        self.tableView.client = self.client
        self.tableView.set_data(data)
        self.compareTableView.client = self.client
        self.compareTableView.set_primary(data)

        self.compareLiveButton.clicked.connect(self.tableView.toggle_live)
        self.tableView.turnOnLive.connect(partial(self.set_live, True))
        self.tableView.turnOffLive.connect(partial(self.set_live, False))
        self.tableView.set_live(False)

        for table in (self.tableView, self.compareTableView):
            header = table.horizontalHeader()
            header.setSectionResizeMode(header.Stretch)

        self.primarySnapshotLabel.setText("Viewing:")
        self.primarySnapshotTitle.setText(data.title)
        self.secondarySnapshotLabel.setText("Comparing:")

        self.compareDialog = SnapshotSelectionDialog(self, client, data)
        self.set_comparison()

        self.compareDialog.finished.connect(self.set_comparison)
        self.compareSnapshotButton.clicked.connect(self.compareDialog.exec_)
        self.restoreButton.clicked.connect(self.launch_dialog)

    def set_live(self, is_live: bool):
        self.secondarySnapshotLabel.setVisible(is_live)
        self.secondarySnapshotTitle.setText("Live Data")
        self.secondarySnapshotTitle.setVisible(is_live)
        self.compareLiveButton.setChecked(is_live)

    def set_comparison(self, accepted: bool = False):
        result = self.compareDialog.selectedSnapshot
        self.show_compare = accepted and isinstance(result, Snapshot)

        if self.show_compare:
            self.secondarySnapshotTitle.setText(result.title)
            self.compareTableView.set_secondary(result)

        self.secondarySnapshotLabel.setVisible(self.show_compare)
        self.secondarySnapshotTitle.setVisible(self.show_compare)

        self.swap_table_views(self.show_compare)

    def swap_table_views(self, show_compare: bool = None):
        if show_compare is None:
            show_compare = self.show_compare

        self.tableView.setVisible(not show_compare)
        self.compareTableView.setVisible(show_compare)

    def launch_dialog(self):
        self.dialog = RestoreDialog(self.client, self.snapshot)
        self.dialog.restoreButton.clicked.connect(partial(self.tableView.set_live, True))
        self.dialog.show()

    def closeEvent(self, a0: QCloseEvent) -> None:
        logging.debug("Closing SnapshotTableView")
        self.tableView.close()
        super().closeEvent(a0)
