import sys
from dataclasses import dataclass

from qtpy.QtCore import Qt
from qtpy.QtGui import QDoubleValidator, QFont
from qtpy.QtWidgets import (QApplication, QBoxLayout, QDialog, QGridLayout,
                            QHBoxLayout, QLabel, QLineEdit, QPushButton,
                            QVBoxLayout, QWidget)

from superscore.type_hints import TagDef, TagSet
from superscore.widgets.tag import TagChip, TagsWidget


@dataclass
class PVDetails:
    """Class to represent the details of a PV (Process Variable). Used to populate the PV details popups."""

    pv_name: str
    readback_name: str
    description: str
    tolerance_abs: float
    tolerance_rel: float
    lolo: float
    low: float
    high: float
    hihi: float
    tags: TagSet


class PVDetailsTitleBar(QWidget):
    """Title bar for the PV details popup. Allows dragging and closing the popup."""

    def __init__(self, text: str, parent: QWidget):
        super().__init__(parent)
        self.drag_position = None

        self.setContentsMargins(0, 0, 0, 0)

        layout = QHBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # Title label
        self.title_label = QLabel(text)
        self.title_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.title_label)

        # Spacer and close button
        layout.addStretch()
        close_button = QPushButton("✕")
        close_button.setFixedSize(24, 24)
        close_button.setStyleSheet("border: none;")
        close_button.clicked.connect(self.parent().close)
        layout.addWidget(close_button)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.parent().frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() & Qt.LeftButton and self.drag_position is not None:
            self.parent().move(event.globalPos() - self.drag_position)
            event.accept()


class PVDetailsRow(QBoxLayout):
    """A row in the PV details popup."""

    def __init__(
        self,
        label: str,
        content: QWidget = None,
        indent: int = 0,
        direction: QBoxLayout.Direction = QBoxLayout.LeftToRight,
        parent: QWidget = None,
    ) -> None:
        """Initialize a row with a label and optional content.

        :param label: The label text for the row.
        :param content: The content widget to display in the row.
        :param indent: The indentation level for the row.
        :param direction: The layout direction (horizontal or vertical).
        :param parent: The parent widget for the layout.
        """
        super().__init__(direction, parent)
        self.tab_width = 20

        if indent > 0 and (direction == QBoxLayout.LeftToRight or direction == QBoxLayout.RightToLeft):
            self.addSpacing(self.tab_width * indent)

        label_widget = QLabel(label)
        label_font = QFont()
        label_font.setPointSize(10)
        label_widget.setFont(label_font)
        label_widget.setStyleSheet("color: #555555;")
        self.addWidget(label_widget)

        if content:
            if hasattr(content, "setFont"):
                content_font = QFont()
                content_font.setPointSize(12)
                content.setStyleSheet("color: #222222;")
                content.setFont(content_font)
            self.addWidget(content)


class PVDetailsPopup(QWidget):
    """Read-only popup displaying PV details."""

    def __init__(self, tag_groups: TagDef, pv_details: PVDetails, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.Popup)

        layout = QVBoxLayout(self)

        title_widget = PVDetailsTitleBar("DETAILS", self)
        layout.addWidget(title_widget)

        layout.addLayout(PVDetailsRow("PV Name", QLabel(pv_details.pv_name), direction=QBoxLayout.TopToBottom))
        layout.addLayout(
            PVDetailsRow("Readback Name", QLabel(pv_details.readback_name), direction=QBoxLayout.TopToBottom)
        )

        description = QLabel(pv_details.description)
        description.setWordWrap(True)
        layout.addLayout(PVDetailsRow("Description", description, direction=QBoxLayout.TopToBottom))

        layout.addLayout(PVDetailsRow("Tolerance", None))
        layout.addLayout(PVDetailsRow("Absolute:", QLabel(str(pv_details.tolerance_abs)), indent=1))
        layout.addLayout(PVDetailsRow("Relative:", QLabel(str(pv_details.tolerance_rel)), indent=1))

        layout.addLayout(PVDetailsRow("PV Limits", None))
        layout.addLayout(PVDetailsRow("LOLO:", QLabel(str(pv_details.lolo)), indent=1))
        layout.addLayout(PVDetailsRow("LOW:", QLabel(str(pv_details.low)), indent=1))
        layout.addLayout(PVDetailsRow("HIGH:", QLabel(str(pv_details.high)), indent=1))
        layout.addLayout(PVDetailsRow("HIHI:", QLabel(str(pv_details.hihi)), indent=1))

        tags_widget = TagsWidget(tag_groups=tag_groups, enabled=True)
        for tag_group in tag_groups.keys():
            if tag_group in pv_details.tags:
                tags_widget.findChildren(TagChip)[tag_group].set_tags(tag_set[tag_group])
        layout.addLayout(PVDetailsRow("Tags", tags_widget, direction=QBoxLayout.TopToBottom))
        layout.addStretch()


class PVDetailsPopupEditable(QDialog):
    """Editable popup for creating or editing PVs."""

    def __init__(self, tag_groups: TagDef, initial_data: PVDetails = None) -> None:
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setWindowModality(Qt.ApplicationModal)
        self.setMinimumWidth(300)
        self.pv_details = None

        layout = QVBoxLayout(self)

        title_text = f"Edit PV: {initial_data.pv_name}" if initial_data else "Create New PV"
        title_bar = PVDetailsTitleBar(title_text, self)
        layout.addWidget(title_bar)

        form_layout = QGridLayout()

        self.pv_name_input = QLineEdit()
        self.readback_name_input = QLineEdit()
        self.description_input = QLineEdit()
        self.tolerance_abs_input = QLineEdit()
        self.tolerance_rel_input = QLineEdit()

        self.tags_input = TagsWidget(tag_groups=tag_groups, enabled=True)
        if initial_data:
            for tag_group in tag_groups.keys():
                if tag_group in initial_data.tags:
                    self.tags_input.findChildren(TagChip)[tag_group].set_tags(tag_set[tag_group])

        validator = QDoubleValidator(bottom=0.0, top=1e10, decimals=4)
        self.tolerance_abs_input.setValidator(validator)
        self.tolerance_rel_input.setValidator(validator)

        if initial_data:
            self.pv_name_input.setText(initial_data.pv_name)
            self.readback_name_input.setText(initial_data.readback_name)
            self.description_input.setText(initial_data.description)
            self.tolerance_abs_input.setText(str(initial_data.tolerance_abs))
            self.tolerance_rel_input.setText(str(initial_data.tolerance_rel))

        form_layout.addWidget(QLabel("PV Name"), 0, 0)
        form_layout.addWidget(self.pv_name_input, 0, 1)

        form_layout.addWidget(QLabel("Readback Name"), 1, 0)
        form_layout.addWidget(self.readback_name_input, 1, 1)

        form_layout.addWidget(QLabel("Description"), 2, 0)
        form_layout.addWidget(self.description_input, 2, 1)

        tolerance_group_label = QLabel("Tolerance")
        tolerance_group_label.setStyleSheet("font-weight: bold;")
        form_layout.addWidget(tolerance_group_label, 3, 0)

        tolerance_abs_label_layout = QHBoxLayout()
        tolerance_abs_label_layout.addSpacing(20)
        tolerance_abs_label_layout.addWidget(QLabel("Absolute"))
        form_layout.addLayout(tolerance_abs_label_layout, 4, 0)
        form_layout.addWidget(self.tolerance_abs_input, 4, 1)

        tolerance_rel_label_layout = QHBoxLayout()
        tolerance_rel_label_layout.addSpacing(20)
        tolerance_rel_label_layout.addWidget(QLabel("Relative"))
        form_layout.addLayout(tolerance_rel_label_layout, 5, 0)
        form_layout.addWidget(self.tolerance_rel_input, 5, 1)

        tags_label = QLabel("Tags")
        tags_label.setStyleSheet("font-weight: bold;")
        form_layout.addWidget(tags_label, 6, 0)
        form_layout.addWidget(self.tags_input, 7, 0, 1, 2)

        layout.addLayout(form_layout)

        submit_text = "Save Changes" if initial_data else "Create PV"
        create_button = QPushButton(submit_text)
        create_button.setStyleSheet("background-color: grey;")
        create_button.clicked.connect(self.handle_submit)
        layout.addWidget(create_button)

        layout.addStretch()
        self.setLayout(layout)

    def handle_submit(self) -> None:
        """Handle save button press."""
        try:
            self.pv_details = PVDetails(
                pv_name=self.pv_name_input.text(),
                readback_name=self.readback_name_input.text(),
                description=self.description_input.text(),
                tolerance_abs=float(self.tolerance_abs_input.text() or 0),
                tolerance_rel=float(self.tolerance_rel_input.text() or 0),
                tags=self.tags_input,
            )
            self.accept()
        except ValueError as e:
            print(f"Invalid input: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    tag_groups: TagDef
    tag_groups = {0: ["Dest", "Which endpoint...", {0: "SXR", 1: "HXR", 2: "ASDF"}]}

    tag_set: TagSet
    tag_set = {0: {0, 2}}

    pv_details = PVDetails(
        pv_name="QUAD:LI21:401:EDES",
        readback_name="QUAD:LI21:401:EACT",
        description="This will be the description of the PV",
        tolerance_abs=0.1,
        tolerance_rel=0.01,
        lolo=0.0,
        low=0.1,
        high=0.9,
        hihi=1.0,
        tags=tag_set,
    )

    # Show read-only popup first
    readonly_popup = PVDetailsPopup(tag_groups=tag_groups, pv_details=pv_details)
    readonly_popup.show()

    def show_editable_popup():
        editable_popup = PVDetailsPopupEditable(tag_groups=tag_groups, initial_data=pv_details)
        if editable_popup.exec_() == QDialog.Accepted:
            print("PV Details Submitted:")
            print(f"PV Name: {editable_popup.pv_details.pv_name}")
            print(f"Readback Name: {editable_popup.pv_details.readback_name}")
            print(f"Description: {editable_popup.pv_details.description}")
            print(f"Absolute Tolerance: {editable_popup.pv_details.tolerance_abs}")
            print(f"Relative Tolerance: {editable_popup.pv_details.tolerance_rel}")

    # Launch editable popup after readonly popup is closed
    readonly_popup.destroyed.connect(show_editable_popup)

    # Keep the application running until the user closes the popup
    input("Press Enter after closing the readonly popup to open the editable popup...")
    sys.exit(0)
