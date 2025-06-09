import qtawesome as qta
from qtpy import QtCore, QtWidgets

from superscore.client import Client
from superscore.model import Snapshot
from superscore.widgets.page.page import Page
from superscore.widgets.snapshot_comparison_table import (
    COMPARE_HEADER, SnapshotComparisonTableModel)


class SnapshotComparisonPage(Page):
    """Page for comparing snapshots"""

    remove_comparison_signal = QtCore.Signal()

    def __init__(self, client: Client, parent: QtWidgets.QWidget = None):
        super().__init__(parent)
        self.client = client
        self.main_snapshot = None
        self.comparison_snapshot = None

        self.setup_ui()

    def setup_ui(self) -> None:
        # Set up the layout
        snapshot_comparison_layout = QtWidgets.QVBoxLayout()
        snapshot_comparison_layout.setContentsMargins(0, 11, 0, 0)
        self.setLayout(snapshot_comparison_layout)

        # Set up the header
        header_layout = QtWidgets.QGridLayout()
        snapshot_comparison_layout.addLayout(header_layout)

        back_button = QtWidgets.QPushButton()
        back_button.setIcon(qta.icon("ph.arrow-left"))
        back_button.setIconSize(QtCore.QSize(24, 24))
        back_button.setStyleSheet("border: none")
        back_button.clicked.connect(self.remove_comparison_signal.emit)
        header_layout.addWidget(back_button, 0, 0)

        main_snapshot_label = QtWidgets.QLabel()
        main_snapshot_label.setText("Main Snapshot")
        header_layout.addWidget(main_snapshot_label, 0, 1)

        spacer_label1 = QtWidgets.QLabel()
        spacer_label1.setText("|")
        spacer_label1.setStyleSheet("font: bold 18px")
        header_layout.addWidget(spacer_label1, 0, 2)

        self.main_snapshot_title_label = QtWidgets.QLabel()
        header_layout.addWidget(self.main_snapshot_title_label, 0, 3)

        spacer_label2 = QtWidgets.QLabel()
        spacer_label2.setText("|")
        spacer_label2.setStyleSheet("font: bold 18px")
        header_layout.addWidget(spacer_label2, 0, 4)

        self.main_snapshot_time_label = QtWidgets.QLabel()
        self.main_snapshot_time_label.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Preferred,)
        header_layout.addWidget(self.main_snapshot_time_label, 0, 5)

        # Second row of the header
        comp_snapshot_label = QtWidgets.QLabel()
        comp_snapshot_label.setText("Comparison Snapshot")
        header_layout.addWidget(comp_snapshot_label, 1, 1)

        spacer_label3 = QtWidgets.QLabel()
        spacer_label3.setText("|")
        spacer_label3.setStyleSheet("font: bold 18px")
        header_layout.addWidget(spacer_label3, 1, 2)

        self.comp_snapshot_title_label = QtWidgets.QLabel()
        header_layout.addWidget(self.comp_snapshot_title_label, 1, 3)

        spacer_label4 = QtWidgets.QLabel()
        spacer_label4.setText("|")
        spacer_label4.setStyleSheet("font: bold 18px")
        header_layout.addWidget(spacer_label4, 1, 4)

        self.comp_snapshot_time_label = QtWidgets.QLabel()
        self.comp_snapshot_time_label.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Preferred,)
        header_layout.addWidget(self.comp_snapshot_time_label, 1, 5)

        remove_button = QtWidgets.QPushButton(qta.icon("ei.remove"), "Remove Comparison", self)
        remove_button.clicked.connect(self.remove_comparison_signal.emit)
        header_layout.addWidget(remove_button, 1, 6)

        # Add a table to show the comparison result
        self.comparison_table_model = SnapshotComparisonTableModel(self.client, self)
        self.comparison_table = QtWidgets.QTableView()
        self.comparison_table.setSelectionBehavior(self.comparison_table.SelectionBehavior.SelectRows)
        self.comparison_table.setModel(self.comparison_table_model)
        self.comparison_table.verticalHeader().hide()
        header_view = self.comparison_table.horizontalHeader()
        header_view.setSectionResizeMode(header_view.Stretch)
        header_view.setSectionResizeMode(COMPARE_HEADER.CHECKBOX.value, header_view.ResizeMode.Fixed)
        header_view.setSectionResizeMode(COMPARE_HEADER.SEVERITY.value, header_view.ResizeMode.Fixed)
        header_view.setSectionResizeMode(COMPARE_HEADER.COMPARE_SEVERITY.value, header_view.ResizeMode.Fixed)
        header_view.setSectionResizeMode(COMPARE_HEADER.DEVICE.value, header_view.ResizeMode.Fixed)
        header_view.setSectionResizeMode(COMPARE_HEADER.PV.value, header_view.ResizeMode.Fixed)
        self.comparison_table.resizeColumnsToContents()
        snapshot_comparison_layout.addWidget(self.comparison_table)

    def set_main_snapshot(self, snapshot: Snapshot):
        """Set the main snapshot for comparison."""
        self.main_snapshot = snapshot
        self.main_snapshot_title_label.setText(snapshot.title)
        self.main_snapshot_time_label.setText(snapshot.creation_time.strftime("%Y-%m-%d %H:%M:%S"))
        self.comparison_table_model.set_main_snapshot(snapshot)

    def set_comparison_snapshot(self, snapshot: Snapshot):
        """Set the comparison snapshot."""
        self.comparison_snapshot = snapshot
        self.comp_snapshot_title_label.setText(snapshot.title)
        self.comp_snapshot_time_label.setText(snapshot.creation_time.strftime("%Y-%m-%d %H:%M:%S"))
        self.comparison_table_model.set_comparison_snapshot(snapshot)
