import qtawesome as qta
from qtpy import QtCore, QtWidgets

from superscore.client import Client
from superscore.model import Snapshot
from superscore.widgets.page.page import Page
from superscore.widgets.pv_table import PV_HEADER, PVTableModel


class SnapshotDetailsPage(Page):
    """Snapshot details page for displaying the details of a snapshot."""

    back_to_main_signal = QtCore.Signal()

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
        self.set_snapshot(init_snapshot)

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
        header_layout.addWidget(self.snapshot_title_label)
        spacer_label2 = QtWidgets.QLabel()
        spacer_label2.setText("|")
        spacer_label2.setStyleSheet("font: bold 18px")
        header_layout.addWidget(spacer_label2)
        self.snapshot_time_label = QtWidgets.QLabel()
        self.snapshot_time_label.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Preferred,)
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
        self.restore_button.setEnabled(False)    # TODO: connect to restore function
        # restore_button.clicked.connect()
        interactions_layout.addWidget(self.restore_button)
        self.compare_button = QtWidgets.QPushButton(qta.icon("ph.plus"), "Compare", self)
        # compare_button.clicked.connect()    # TODO: connect to compare function
        interactions_layout.addWidget(self.compare_button)
        snapshot_details_layout.addLayout(interactions_layout)

        # Create a snapshot details model, populated with first snapshot for initialization
        self.snapshot_details_model = PVTableModel(self.snapshot.uuid, self.client)
        self.live_models.add(self.snapshot_details_model)

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

        self.snapshot_details_model.set_snapshot(self.snapshot.uuid)
