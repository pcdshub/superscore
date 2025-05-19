from typing import Any

from qtpy import QtCore, QtWidgets

from superscore.type_hints import TagDef
from superscore.widgets import FlowLayout


class TagsWidget(QtWidgets.QWidget):
    """
    A container for TagChips arranged in a flow layout.

    This widget manages a collection of tag elements, each of which manages the
    addition, removal, and display of tags in its tag group. To freeze the set
    of tags in the TagChips, set enabled to False on this widget. The tags are
    arranged using a custom FlowLayout that automatically wraps the tags when
    they reach the edge of the widget.

    Attributes
    ----------
    tag_list_layout : FlowLayout
        The layout containing the widget's tag elements.
    """
    def __init__(
        self,
        *args: Any,
        tag_groups: TagDef = {},
        enabled: bool = False,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the TagsWidget.

        Parameters
        ----------
        tag_groups : TagDef
            A data structure containing tag group indices, names, and members
        *args : Any
            Additional positional arguments passed to the base QWidget.
        **kwargs : Any
            Additional keyword arguments passed to the base QWidget.
        """
        super().__init__(*args, **kwargs)
        self.setEnabled(enabled)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Fixed,
            QtWidgets.QSizePolicy.Fixed
        )

        self.setLayout(FlowLayout(margin=0, spacing=5))
        self.layout().setObjectName("TagChipFlowLayout")

        self.set_tag_groups(tag_groups)

    def set_tag_groups(self, tag_groups: TagDef) -> None:
        while self.layout().count() > 0:
            self.layout().takeAt(0)
        for tag_group, details in tag_groups.items():
            chip = TagChip(
                tag_group,
                details[2],
                details[0],
                desc=details[1],
                enabled=self.isEnabled())
            self.layout().addWidget(chip)


class TagChip(QtWidgets.QWidget):
    """
    A UI element representing active tags for one tag group. TagsWidget uses multiple to
    represent a full TagSet.

    This widget display the tag group name and the name of all its active tags. If enabled,
    clicking this widget opens a popup to activate or deactivate tags, and it exposes a button
    to clear all active tags.

    Parameters
    ----------
    tag_group : int
        The index of this widget's tag group.
    choices : dict[int, str]
        A map relating tag indices and names.
    tag_name : str
        The name of this widget's tag group.
    desc : str
        The description of this widget's tag group. Only shown via tooltip.
    enabled : bool
        Whether this widget is editable or its set of active tags is frozen.
    **kwargs : Any
        Additional keyword arguments to pass to the base QWidget.
    """
    def __init__(self, tag_group: int, choices: dict[int, str], tag_name: str, desc: str = "", enabled: bool = False, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        self.tag_group = tag_group
        self.tag_name = tag_name
        self.choices = choices
        self.tags = set()
        self.setToolTip(desc)

        self.label = QtWidgets.QLabel()
        self.refresh_label()

        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().setContentsMargins(5, 2, 5, 2)
        self.layout().setSpacing(5)
        self.layout().addWidget(self.label)

        self.clear_button = QtWidgets.QToolButton()
        self.clear_button.setText("X")
        self.clear_button.setToolTip("Reset this tag")

        self.layout().insertWidget(0, self.clear_button)
        self.clear_button.clicked.connect(self.clear)

        self.editor = TagEditor(self.choices, self.tags, parent=self)
        self.editor.tagsChanged.connect(self.set_tags)
        self.editor.hide()

        self.setEnabled(enabled)

    def setEnabled(self, enabled: bool):
        self.clear_button.setVisible(enabled)
        super().setEnabled(enabled)

    def refresh_label(self) -> None:
        """Refresh this widget's displayed text"""
        tag_strings = {self.choices[tag] for tag in self.tags}
        text = f"{self.tag_name}|{', '.join(sorted(tag_strings))}"
        self.label.setText(text)

    def set_tags(self, tags: set[int]) -> None:
        """Set this widget's active tags and trigger a text refresh."""
        self.tags = tags
        self.refresh_label()

    def clear(self) -> None:
        """Clear this widget's active tags."""
        self.tags = set()
        self.editor.choice_list.clearSelection()
        self.refresh_label()

    def mouseReleaseEvent(self, event):
        self.editor.show()
        super().mouseReleaseEvent(event)


class TagEditor(QtWidgets.QWidget):
    """
    Popup for selecting a TagChip's active tags.

    Parameters
    ----------
    choices : dict[int, str]
        Map of tag indices to names; received from TagChip. Used to display the correct tag
        names while sending the correct tag indices back to the TagChip.
    selected : set[int]
        Set of tag indices representing active tags from the TagChip. These will be selected
        when this widget is initially shown.
    parent : QWidget
        This widget's parent; typically a TagChip. Only used for positioning, data is
        transferred via signals.

    Attributes
    ----------
    tagsChanged : QtCore.Signal(set)
        Signal emitted when the set of selected tags is changed.
    """

    tagsChanged = QtCore.Signal(set)

    def __init__(self, choices: dict[int, str], selected: set[int], parent: QtWidgets.QWidget = None) -> None:
        """
        Initialize the TagEditor widget.
        """
        super().__init__(parent=parent)
        self.setWindowFlags(QtCore.Qt.Popup)

        layout = QtWidgets.QVBoxLayout()
        layout.setObjectName("TagEditorLayout")
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.choice_list = QtWidgets.QListWidget()
        self.choice_list.setSelectionMode(self.choice_list.MultiSelection)
        self.layout().addWidget(self.choice_list)
        self.set_choices(choices)

        self.choice_list.itemSelectionChanged.connect(self.emitTagsChanged)

    def emitTagsChanged(self):
        """
        Emits self.tagsChanged with the new set of selected tag indices. Needed so that
        self.tagsChanged can emit the required data despite being connected to the data-less
        QListWidget.itemSelectionChanged signal.
        """
        selected = {item.data(QtCore.Qt.UserRole) for item in self.choice_list.selectedItems()}
        self.tagsChanged.emit(selected)

    def set_choices(self, choices: dict[int, str]) -> None:
        """
        Set this widget's tag choices. Clears and then re-populates choice_list, with each
        list item containing both the tag index and name.
        """
        self.choice_list.clear()
        for tag, string in choices.items():
            self.choice_list.addItem(string)
            item = self.choice_list.item(self.choice_list.count() - 1)
            item.setData(QtCore.Qt.UserRole, tag)

    def show(self):
        corner = self.parent().rect().bottomLeft()
        global_pos = self.parent().mapToGlobal(corner)
        self.move(global_pos)
        super().show()
