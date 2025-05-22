import qtawesome as qta
from qtpy import QtCore, QtWidgets

from superscore.client import Client
from superscore.model import Snapshot
from superscore.widgets.page.page import Page
from superscore.widgets.snapshot_comparison_table import \
    SnapshotComparisonTableModel


class SnapshotComparisonPage(Page):
    """Page for comparing snapshots"""

    remove_comparison_signal = QtCore.Signal()

    def __init__(self, parent: QtWidgets.QWidget, client: Client):
        super().__init__(parent)
        self.client = client
        self.main_snapshot = None
        self.comparison_snapshot = None

        self.setup_ui()

    def setup_ui(self) -> None:
        # Set up the layout
        snapshot_comparison_layout = QtWidgets.QVBoxLayout()
        self.setLayout(snapshot_comparison_layout)

        # Add a label to show the comparison result
        main_header_layout = QtWidgets.QHBoxLayout()
        main_snapshot_label = QtWidgets.QLabel()
        main_snapshot_label.setText("Main Snapshot")
        main_header_layout.addWidget(main_snapshot_label)

        spacer_label1 = QtWidgets.QLabel()
        spacer_label1.setText("|")
        spacer_label1.setStyleSheet("font: bold 18px")
        main_header_layout.addWidget(spacer_label1)

        self.main_snapshot_title_label = QtWidgets.QLabel()
        main_header_layout.addWidget(self.main_snapshot_title_label)

        spacer_label2 = QtWidgets.QLabel()
        spacer_label2.setText("|")
        spacer_label2.setStyleSheet("font: bold 18px")
        main_header_layout.addWidget(spacer_label2)

        self.main_snapshot_time_label = QtWidgets.QLabel()
        self.main_snapshot_time_label.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Preferred,)
        main_header_layout.addWidget(self.main_snapshot_time_label)

        snapshot_comparison_layout.addLayout(main_header_layout)

        # Add a label to show the comparison result
        comp_header_layout = QtWidgets.QHBoxLayout()
        comp_snapshot_label = QtWidgets.QLabel()
        comp_snapshot_label.setText("Comparison Snapshot")
        comp_header_layout.addWidget(comp_snapshot_label)

        spacer_label3 = QtWidgets.QLabel()
        spacer_label3.setText("|")
        spacer_label3.setStyleSheet("font: bold 18px")
        comp_header_layout.addWidget(spacer_label3)

        self.comp_snapshot_title_label = QtWidgets.QLabel()
        comp_header_layout.addWidget(self.comp_snapshot_title_label)

        spacer_label4 = QtWidgets.QLabel()
        spacer_label4.setText("|")
        spacer_label4.setStyleSheet("font: bold 18px")
        comp_header_layout.addWidget(spacer_label4)

        self.comp_snapshot_time_label = QtWidgets.QLabel()
        self.comp_snapshot_time_label.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Preferred,)
        comp_header_layout.addWidget(self.comp_snapshot_time_label)
        comp_header_layout.addSpacerItem(QtWidgets.QSpacerItem(1, 1, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum))
        remove_button = QtWidgets.QPushButton(qta.icon("ei.remove"), "Remove Comparison", self)
        remove_button.clicked.connect(self.remove_comparison_signal.emit)
        comp_header_layout.addWidget(remove_button)

        snapshot_comparison_layout.addLayout(comp_header_layout)

        # Add a table to show the comparison result
        self.comparison_table_model = SnapshotComparisonTableModel(self.client, self)
        self.comparison_table = QtWidgets.QTableView()
        self.comparison_table.setModel(self.comparison_table_model)
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

    def update_comparison_table(self):
        """Update the comparison table with the differences between the two snapshots."""
        if self.main_snapshot is None or self.comparison_snapshot is None:
            return
