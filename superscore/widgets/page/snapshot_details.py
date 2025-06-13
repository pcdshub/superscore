import qtawesome as qta
from qtpy import QtCore, QtWidgets

from superscore.client import Client
from superscore.model import Snapshot
from superscore.widgets.page.page import Page
from superscore.widgets.pv_table import PV_HEADER, PVTableModel
from superscore.widgets.snapshot_table import SnapshotTableModel


class SnapshotDetailsPage(Page):
    """Snapshot details page for displaying the details of a snapshot."""

    back_to_main_signal = QtCore.Signal()
    comparison_signal = QtCore.Signal(object, object)

    def __init__(self, parent: QtWidgets.QWidget, client: Client, init_snapshot: Snapshot):
        """Initialize the snapshot details page.

        Parameters
        ----------
        parent : QtWidgets.QWidget
            Parent widget for the snapshot details page.
        client : Client
            Client object for interacting with the server.
        init_snapshot : Snapshot
            Snapshot object to be displayed in the details page.
        """
        super().__init__(parent)
        self.client = client
        self.snapshot = init_snapshot

        self.init_ui()

    def init_ui(self) -> None:
        """Initialize the UI for the snapshot details page."""
        snapshot_details_layout = QtWidgets.QVBoxLayout()
        snapshot_details_layout.setContentsMargins(0, 11, 0, 0)
        self.setLayout(snapshot_details_layout)

        header_layout = QtWidgets.QHBoxLayout()
        back_button = QtWidgets.QPushButton()
        back_button.setIcon(qta.icon("ph.arrow-left"))
        back_button.setIconSize(QtCore.QSize(24, 24))
        back_button.setStyleSheet("border: none")
        back_button.clicked.connect(self.back_to_main_signal.emit)
        header_layout.addWidget(back_button)

        snapshot_label = QtWidgets.QLabel()
        snapshot_label.setText("Snapshot")
        header_layout.addWidget(snapshot_label)
        spacer_label1 = QtWidgets.QLabel()
        spacer_label1.setText("|")
        spacer_label1.setStyleSheet("font: bold 18px")
        header_layout.addWidget(spacer_label1)
        self.snapshot_title_label = QtWidgets.QLabel()
        self.snapshot_title_label.setText(self.snapshot.title)
        header_layout.addWidget(self.snapshot_title_label)
        spacer_label2 = QtWidgets.QLabel()
        spacer_label2.setText("|")
        spacer_label2.setStyleSheet("font: bold 18px")
        header_layout.addWidget(spacer_label2)
        self.snapshot_time_label = QtWidgets.QLabel()
        self.snapshot_time_label.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Preferred,)
        ts_str = self.snapshot.creation_time.strftime("%Y-%m-%d %H:%M:%S")
        self.snapshot_time_label.setText(ts_str)
        header_layout.addWidget(self.snapshot_time_label)
        snapshot_details_layout.addLayout(header_layout)

        interactions_layout = QtWidgets.QHBoxLayout()
        self.search_bar = QtWidgets.QLineEdit()
        self.search_bar.setClearButtonEnabled(True)
        self.search_bar.addAction(
            qta.icon("fa5s.search"),
            QtWidgets.QLineEdit.LeadingPosition,
        )
        interactions_layout.addWidget(self.search_bar)
        interactions_layout.addSpacerItem(QtWidgets.QSpacerItem(1, 1, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum))

        self.restore_button = QtWidgets.QPushButton(qta.icon("ph.arrow-clockwise"), "Restore", self)
        self.restore_button.clicked.connect(self.show_restore_dialog)
        interactions_layout.addWidget(self.restore_button)

        self.comparison_dialog = SnapshotComparisonDialog(self, self.client, self.snapshot)
        self.comparison_dialog.finished.connect(self.comparison_selected)
        self.comparison_dialog.set_snapshot(self.snapshot)
        self.compare_button = QtWidgets.QPushButton(qta.icon("ph.plus"), "Compare", self)
        self.compare_button.clicked.connect(self.open_comparison_selection)
        interactions_layout.addWidget(self.compare_button)
        snapshot_details_layout.addLayout(interactions_layout)

        # Create a snapshot details model, populated with first snapshot for initialization
        self.snapshot_details_model = PVTableModel(self.snapshot.uuid, self.client)
        self.pv_table_models[self.snapshot.uuid] = self.snapshot_details_model

        self.snapshot_details_table = QtWidgets.QTableView()
        self.snapshot_details_table.setModel(self.snapshot_details_model)
        self.snapshot_details_table.setShowGrid(False)
        self.snapshot_details_table.verticalHeader().hide()
        header_view = self.snapshot_details_table.horizontalHeader()
        header_view.setSectionResizeMode(header_view.Stretch)
        header_view.setSectionResizeMode(PV_HEADER.CHECKBOX.value, header_view.ResizeToContents)
        header_view.setSectionResizeMode(PV_HEADER.SEVERITY.value, header_view.ResizeToContents)
        header_view.setSectionResizeMode(PV_HEADER.DEVICE.value, header_view.ResizeToContents)
        header_view.setSectionResizeMode(PV_HEADER.PV.value, header_view.ResizeToContents)
        snapshot_details_layout.addWidget(self.snapshot_details_table)

    def set_snapshot(self, snapshot: Snapshot) -> None:
        """Set the snapshot to be displayed in the details page."""
        if not isinstance(snapshot, Snapshot):
            raise TypeError("snapshot must be a Snapshot object")
        if snapshot is self.snapshot:
            return
        self.snapshot = snapshot
        self.snapshot_title_label.setText(self.snapshot.title)

        ts_str = self.snapshot.creation_time.strftime("%Y-%m-%d %H:%M:%S")
        self.snapshot_time_label.setText(ts_str)

        if self.snapshot.uuid in self.pv_table_models:
            self.snapshot_details_model = self.pv_table_models[self.snapshot.uuid]
        else:
            self.snapshot_details_model = PVTableModel(self.snapshot.uuid, self.client)
            self.pv_table_models[self.snapshot.uuid] = self.snapshot_details_model
        self.snapshot_details_table.setModel(self.snapshot_details_model)

        self.comparison_dialog.set_snapshot(self.snapshot)

    @QtCore.Slot()
    def open_comparison_selection(self) -> None:
        """Select a comparison snapshot."""
        self.comparison_dialog.show()

    @QtCore.Slot(int)
    def comparison_selected(self, result: QtWidgets.QDialog.DialogCode) -> None:
        """Handle the selection of a comparison snapshot."""
        if result == QtWidgets.QDialog.Rejected:
            return
        comparison_snapshot = self.comparison_dialog.selected_snapshot
        if comparison_snapshot is None or comparison_snapshot == self.snapshot:
            self.metaObject().invokeMethod(
                self,
                "show_warning",
                QtCore.Qt.QueuedConnection,
            )
            return
        self.comparison_signal.emit(self.snapshot, comparison_snapshot)

    @QtCore.Slot()
    def show_warning(self):
        """Show a warning dialog if the selected entry is the main Snapshot. This
        has to be a separate slot to allow QDialog close events to process."""
        QtWidgets.QMessageBox.warning(
            self,
            "Invalid Selection",
            "Please select a Snapshot to compare to.",
        )

    def show_restore_dialog(self):
        """Prompt the user to confirm a restore action"""
        dialog = QtWidgets.QDialog(self)
        dialog.setLayout(QtWidgets.QHBoxLayout())
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        dialog.layout().addWidget(button_box)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        selected_pvs = self.snapshot_details_table.model().get_selected_pvs()
        if len(selected_pvs) == 0:
            dialog.setWindowTitle("Restore all PVs?")
        else:
            dialog.setWindowTitle("Restore selected PVs?")
        dialog.accepted.connect(self.restore_from_table)
        dialog.exec()

    def restore_from_table(self):
        """Restore checked setpoints from the PV table. If no PVs are selected, restore all."""
        selected_pvs = self.snapshot_details_table.model().get_selected_pvs()
        if len(selected_pvs) == 0:
            selected_pvs = self.snapshot_details_table.model()._data
        ephemeral_snapshot = Snapshot(children=selected_pvs)
        self.client.apply(ephemeral_snapshot)


class SnapshotComparisonDialog(QtWidgets.QDialog):
    """Dialog for selecting a comparison snapshot."""

    def __init__(self, parent: QtWidgets.QWidget, client: Client, snapshot: Snapshot):
        """Initialize the snapshot comparison dialog.

        Parameters
        ----------
        parent : QtWidgets.QWidget
            Parent widget for the dialog.
        client : Client
            Client object for interacting with the server.
        """
        super().__init__(parent)
        self.client = client
        self.snapshot = None

        self.init_ui()
        self.set_snapshot(snapshot)

    def init_ui(self) -> None:
        self.setWindowTitle("Select Comparison Snapshot")

        main_layout = QtWidgets.QVBoxLayout()
        self.setLayout(main_layout)

        self.header_label = QtWidgets.QLabel()
        main_layout.addWidget(self.header_label)

        self.proxy_model = ExcludeCurrentSnapshotProxyModel(self, self.snapshot)
        try:
            main_window = self.parent().parent()
            snapshot_table_model = main_window.snapshot_table.model()
        except AttributeError:
            snapshot_table_model = SnapshotTableModel(self.client)
        finally:
            self.proxy_model.setSourceModel(snapshot_table_model)
        self.table_view = QtWidgets.QTableView()
        self.table_view.setShowGrid(False)
        self.table_view.setModel(self.proxy_model)
        self.table_view.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table_view.doubleClicked.connect(self.accept)
        self.table_view.verticalHeader().hide()
        header_view = self.table_view.horizontalHeader()
        header_view.setSectionResizeMode(header_view.ResizeToContents)
        header_view.setSectionResizeMode(1, header_view.Stretch)
        main_layout.addWidget(self.table_view)

        btns = QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        buttonBox = QtWidgets.QDialogButtonBox(btns)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        main_layout.addWidget(buttonBox)

        self.resize(450, 300)

    @property
    def selected_snapshot(self):
        try:
            selected_index = self.table_view.selectedIndexes()[0]
        except IndexError:
            return None
        return self.proxy_model.index_to_snapshot(selected_index)

    def set_snapshot(self, snapshot: Snapshot) -> None:
        """Set the snapshot to be displayed in the details page."""
        if snapshot is self.snapshot:
            return

        self.snapshot = snapshot

        header_text = f"Main Snapshot:\n    {self.snapshot.title}\n\n" \
                      "Select a snapshot to compare to:"
        self.header_label.setText(header_text)

        self.proxy_model.set_snapshot(self.snapshot)


class ExcludeCurrentSnapshotProxyModel(QtCore.QSortFilterProxyModel):
    """A proxy model that excludes the current snapshot from the source model."""

    def __init__(self, parent, snapshot: Snapshot):
        super().__init__(parent)
        self.snapshot = snapshot

    def filterAcceptsRow(self, source_row: int, source_parent: QtCore.QModelIndex) -> bool:
        source_index = self.sourceModel().index(source_row, 0, source_parent)
        source_snapshot = self.sourceModel().index_to_snapshot(source_index)
        if source_snapshot == self.snapshot:
            return False
        return True

    def set_snapshot(self, snapshot: Snapshot) -> None:
        """Set the snapshot to be displayed in the details page."""
        if snapshot == self.snapshot:
            return
        self.snapshot = snapshot
        self.invalidateFilter()

    def index_to_snapshot(self, index: QtCore.QModelIndex) -> Snapshot:
        """Convert a QModelIndex to a Snapshot object."""
        source_index = self.mapToSource(index)
        return self.sourceModel().index_to_snapshot(source_index)
