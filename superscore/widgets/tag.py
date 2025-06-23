from typing import Any, Optional

import qtawesome as qta
from qtpy import QtCore, QtWidgets

import superscore.color
from superscore.type_hints import TagDef, TagSet
from superscore.widgets import FlowLayout


class TagChip(QtWidgets.QFrame):
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

    tagsChanged = QtCore.Signal(set)

    def __init__(self, tag_group: int, choices: dict[int, str], tag_name: str, desc: str = "", enabled: bool = False, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        self.tag_group = tag_group
        self.tag_name = tag_name
        self.choices = choices
        self.tags = set()
        self.setProperty("empty", True)
        self.setToolTip(desc)
        self.setStyleSheet(
            "TagChip {"
            "border-width: 2px;"
            f"border-color: {superscore.color.GREY};"
            "border-radius: 1.9ex;"
            "}\n"
            "TagChip:disabled {"
            "border-radius: 1.7ex;"
            "}\n"
            "TagChip[empty=\"false\"] {"
            "border-style: solid;"
            "}\n"
            "TagChip[empty=\"true\"] {"
            "border-style: dashed;"
            "}\n"
        )

        self.group_label = QtWidgets.QLabel()
        self.group_label.setStyleSheet(
            "QLabel:disabled {"
            f"color: {superscore.color.GREY};"
            "}"
        )
        self.spacer_label = QtWidgets.QLabel("|")
        self.tags_label = QtWidgets.QLabel()
        self.tags_label.setStyleSheet(
            f"color: {superscore.color.LIGHT_BLUE};"
        )

        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().setSpacing(3)
        self.layout().addWidget(self.group_label)
        self.layout().addWidget(self.spacer_label)
        self.layout().addWidget(self.tags_label)

        self.editor = TagEditor(self.choices, self.tags, parent=self)
        self.editor.tagsChanged.connect(self.set_tags)
        self.editor.hide()

        self.clear_button = QtWidgets.QToolButton()
        self.clear_button.setStyleSheet(
            "QToolButton {"
            "border-radius: 1ex;"
            "}"
        )
        clear_icon = qta.icon("ph.x-circle-fill", color=superscore.color.GREY, scale_factor=1.1)
        self.clear_button.setIcon(clear_icon)
        self.clear_button.clicked.connect(self.clear)
        self.layout().insertWidget(0, self.clear_button)

        self.add_button = QtWidgets.QToolButton()
        self.add_button.setStyleSheet(
            "QToolButton {"
            "border-radius: 1ex;"
            "}"
        )
        add_icon = qta.icon("ph.plus-circle-fill", color=superscore.color.GREY, scale_factor=1.1)
        self.add_button.setIcon(add_icon)
        self.add_button.clicked.connect(self.editor.show)
        self.layout().insertWidget(0, self.add_button)

        self.setEnabled(enabled)
        self.redraw()

    def setEnabled(self, enabled: bool):
        super().setEnabled(enabled)
        self.redraw()

    def redraw(self) -> None:
        """Redraw this widget according to its current state"""
        # set label text
        tag_strings = {self.choices[tag] for tag in self.tags}
        self.group_label.setText(f"{self.tag_name}")
        self.tags_label.setText(', '.join(sorted(tag_strings)))
        if len(self.tags) > 0:
            self.spacer_label.show()
        else:
            self.spacer_label.hide()

        # show correct icon
        self.clear_button.hide()
        self.add_button.hide()
        if self.isEnabled():
            if len(self.tags) > 0:
                self.clear_button.show()
            else:
                self.add_button.show()
            self.layout().setContentsMargins(5, 2, 5, 2)
        else:
            self.layout().setContentsMargins(10, 2, 0, 2)

        # trigger "empty" property styling; cannot update box model
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def set_tags(self, tags: set[int]) -> None:
        """Set this widget's active tags and redraw."""
        self.tags = tags
        self.setProperty("empty", len(self.tags) == 0)
        self.redraw()
        self.tagsChanged.emit(self.tags)

    def clear(self) -> None:
        """Clear this widget's active tags."""
        self.tags = set()
        self.editor.choice_list.clearSelection()
        self.redraw()

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

    tagSetChanged = QtCore.Signal(dict)

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
        self.tag_groups = tag_groups

        self.setEnabled(enabled)

        self.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)

        self.setLayout(FlowLayout(margin=0, spacing=5))
        self.layout().setObjectName("TagChipFlowLayout")

        self.set_tag_groups(self.tag_groups)

    def set_tag_groups(self, tag_groups: TagDef) -> None:
        while self.layout().count() > 0:
            self.layout().takeAt(0)
        for tag_group, details in tag_groups.items():
            chip = TagChip(tag_group, details[2], details[0], desc=details[1], enabled=self.isEnabled())
            chip.tagsChanged.connect(lambda tags: self.tagSetChanged.emit(self.get_tag_set()))
            self.layout().addWidget(chip)
        self.tag_groups = tag_groups

    def set_tags(self, tag_set: TagSet) -> None:
        """Sets the child TagChips according to the provided TagSet"""
        for tag_group in tag_set:
            chip = self.get_group_chip(tag_group)
            if isinstance(chip, TagChip):
                chip.set_tags(tag_set[tag_group])

    def get_tag_set(self) -> TagSet:
        """Constructs the TagSet representation of the child TagChips"""
        tag_set = {}
        chips = self.findChildren(TagChip)
        for chip in chips:
            tag_set[chip.tag_group] = chip.tags
        return tag_set

    def get_group_chip(self, tag_group: int) -> Optional[TagChip]:
        """Returns TagChip corresponding to the desired tag group, or None if chip was not found"""
        chips = self.findChildren(TagChip)
        for chip in chips:
            if chip.tag_group == tag_group:
                return chip
        return None
