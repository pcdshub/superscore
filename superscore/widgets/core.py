"""
Core widget classes for qt-based GUIs.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar, Optional
from weakref import WeakValueDictionary

from pcdsutils.qt.designer_display import DesignerDisplay
from qtpy import QtCore, QtWidgets

from superscore.client import Client
from superscore.qt_helpers import QDataclassBridge
from superscore.type_hints import AnyDataclass, OpenPageSlot, TagDef
from superscore.utils import SUPERSCORE_SOURCE_PATH
from superscore.widgets import get_window
from superscore.widgets.manip_helpers import match_line_edit_text_width


class Display(DesignerDisplay):
    """Helper class for loading designer .ui files and adding logic"""

    ui_dir: Path = SUPERSCORE_SOURCE_PATH / 'ui'


class DataWidget(QtWidgets.QWidget):
    """
    Base class for widgets that manipulate dataclasses.

    Defines the init args for all data widgets and handles synchronization
    of the ``QDataclassBridge`` instances. This is done so that only data
    widgets need to consider how to handle bridges and the page classes
    simply need to pass in data structures, rather than needing to keep track
    of how two widgets editing the same data structure must share the same
    bridge object.

    Parameters
    ----------
    data : any dataclass
        The dataclass that the widget needs to manipulate. Most widgets are
        expecting either specific dataclasses or dataclasses that have
        specific matching fields.
    kwargs : QWidget kwargs
        Passed directly to QWidget's __init__. Likely unused in most cases.
        Even parent is unlikely to see use because parent is set automatically
        when a widget is inserted into a layout.
    """
    # QDataclassBridge for this widget, other bridges may live in EntryItem
    _bridge_cache: ClassVar[
        WeakValueDictionary[int, QDataclassBridge]
    ] = WeakValueDictionary()
    bridge: QDataclassBridge
    data: AnyDataclass

    def __init__(self, data: AnyDataclass, **kwargs):
        super().__init__(**kwargs)
        self.data = data
        try:
            # TODO figure out better way to cache these
            # TODO worried about strange deallocation timing race conditions
            self.bridge = self._bridge_cache[id(data)]
        except KeyError:
            bridge = QDataclassBridge(data)
            self._bridge_cache[id(data)] = bridge
            self.bridge = bridge


class NameMixin:
    """
    Mixin class for distributing init_name
    """
    def init_name(self) -> None:
        """
        Set up the name_edit widget appropriately.
        """
        # Load starting text
        load_name = self.bridge.title.get() or ''
        self.last_name = load_name
        self.name_edit.setText(load_name)
        self.on_text_changed(load_name)
        # Set up the saving/loading
        self.name_edit.textEdited.connect(self.update_saved_name)
        self.name_edit.textChanged.connect(self.on_text_changed)
        self.bridge.title.changed_value.connect(self.apply_new_name)

    def update_saved_name(self, name: str) -> None:
        """
        When the user edits the name, write to the config.
        """
        self.last_name = self.name_edit.text()
        self.bridge.title.put(name)

    def apply_new_name(self, text: str) -> None:
        """
        If the text changed in the data, update the widget.

        Only run if needed to avoid annoyance with cursor repositioning.
        """
        if text != self.last_name:
            self.name_edit.setText(text)

    def on_text_changed(self, text: str):
        match_line_edit_text_width(self.name_edit, text=text)


class NameDescTagsWidget(Display, NameMixin, DataWidget):
    """
    Widget for displaying and editing the name, description, and tags fields.

    Any of these will be automatically disabled if the data source is missing
    the corresponding field.

    As a convenience, this also holds an "extra_text_label" QLabel for general use.
    """
    filename = 'name_desc_tags_widget.ui'

    name_edit: QtWidgets.QLineEdit
    name_frame: QtWidgets.QFrame
    desc_edit: QtWidgets.QPlainTextEdit
    desc_frame: QtWidgets.QFrame
    tags_widget: TagsWidget
    extra_text_label: QtWidgets.QLabel

    def __init__(self, data: AnyDataclass, **kwargs):

        tag_groups = kwargs.pop('tag_options', dict())

        super().__init__(data=data, **kwargs)
        try:
            self.bridge.title
        except AttributeError:
            self.name_frame.hide()
        else:
            self.init_name()
        try:
            self.bridge.description
        except AttributeError:
            self.desc_frame.hide()
        else:
            self.init_desc()
        try:
            self.bridge.tags
        except AttributeError:
            self.tags_widget.hide()
        else:
            self.init_tags(tag_groups)

    def init_desc(self) -> None:
        """
        Set up the desc_edit widget appropriately.
        """
        # Load starting text
        load_desc = self.bridge.description.get() or ''
        self.last_desc = load_desc
        self.desc_edit.setPlainText(load_desc)
        # Setup the saving/loading
        self.desc_edit.textChanged.connect(self.update_saved_desc)
        self.bridge.description.changed_value.connect(self.apply_new_desc)
        self.desc_edit.textChanged.connect(self.update_text_height)

    def update_saved_desc(self) -> None:
        """
        When the user edits the desc, write to the config.
        """
        self.last_desc = self.desc_edit.toPlainText()
        self.bridge.description.put(self.last_desc)

    def apply_new_desc(self, desc: str) -> None:
        """
        When some other widget updates the description, update it here.
        """
        if desc != self.last_desc:
            self.desc_edit.setPlainText(desc)

    def showEvent(self, *args, **kwargs) -> None:
        """
        Override showEvent to update the desc height when we are shown.
        """
        try:
            self.update_text_height()
        except AttributeError:
            pass
        return super().showEvent(*args, **kwargs)

    def resizeEvent(self, *args, **kwargs) -> None:
        """
        Override resizeEvent to update the desc height when we resize.
        """
        try:
            self.update_text_height()
        except AttributeError:
            pass
        return super().resizeEvent(*args, **kwargs)

    def update_text_height(self) -> None:
        """
        When the user edits the desc, make the text box the correct height.
        """
        line_count = max(self.desc_edit.document().size().toSize().height(), 1)
        self.desc_edit.setFixedHeight(line_count * 13 + 12)

    def init_tags(self, tag_groups: TagDef) -> None:
        """
        Set up the tags widgets appropriately.
        """
        self.tags_widget.setObjectName("TagsWidget")
        self.tags_widget.set_tag_groups(tag_groups)


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
        tag_groups : Optional[TagDef]
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


class QtSingleton(type(QtCore.QObject), type):
    """
    Qt specific singleton implementation, needed to ensure signals are shared
    between instances.  Adapted from
    https://stackoverflow.com/questions/59459770/receiving-pyqtsignal-from-singleton

    The more common __new__ - based singleton pattern does result in the QObject
    being a singleton, but the bound signals lose their connections whenever the
    instance is re-acquired.  I do not understand but this works

    To use this, specify `QtSingleton` as a metaclass:

    .. code-block:: python
        class SingletonClass(QtCore.QObject, metaclass=QtSingleton):
            shared_signal: ClassVar[QtCore.Signal] = QtCore.Signal()

    """
    def __init__(cls, name, bases, dict):
        super().__init__(name, bases, dict)
        cls._instance = None

    def __call__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__call__(*args, **kwargs)
        return cls._instance


class WindowLinker:
    """
    Mixin class that provides access methods for resources held by the main Window.
    These include:
    - client: first attempts to grab the client set at init, if none exists use
              the Window's client
    - open_page_slot: grabs the slot from the Window
    """

    def __init__(self, *args, client: Optional[Client] = None, **kwargs) -> None:
        self._client = client
        super().__init__(*args, **kwargs)

    @property
    def client(self) -> Optional[Client]:
        # Return the provided client if it exists, grab the Window's otherwise
        if self._client is not None:
            return self._client
        else:
            window = get_window()
            if window is not None:
                return window.client

    @client.setter
    def client(self, client: Client):
        if not isinstance(client, Client):
            raise TypeError(f"Cannot set a {type(client)} as a client")

        if client is self._client:
            return

        self._client = client

    @property
    def open_page_slot(self) -> Optional[OpenPageSlot]:
        window = get_window()
        if window is not None:
            return window.open_page

    def get_window(self):
        """Return the singleton Window instance"""
        return get_window()

    def refresh_window(self):
        """Refresh window ui elements"""
        # tree view
        window = get_window()
        window.tree_view.set_data(self.client.backend.root)
        window.tree_view.model().refresh_tree()


class FlowLayout(QtWidgets.QLayout):
    """
    A custom layout that arranges child widgets in a flowing manner.

    Widgets are placed horizontally until there is no more space, then the layout
    wraps them to the next line. This layout is useful for creating a tag cloud,
    button groups, or any interface where items should wrap automatically.
    """
    def __init__(self, margin=0, spacing=-1, **kwargs):
        """
        Initialize the FlowLayout.

        Parameters
        ----------
        parent : QWidget, optional
            The parent widget for this layout. Default is None.
        margin : int, optional
            The margin to apply around the layout. Default is 0.
        spacing : int, optional
            The spacing between items. Default is -1, which means use the default spacing.
        """
        super().__init__(**kwargs)
        if self.parent() is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self.itemList = []

    def addItem(self, item: QtWidgets.QLayoutItem) -> None:
        """
        Add an item to the layout.

        Parameters
        ----------
        item : QLayoutItem
            The layout item to add.
        """
        self.itemList.append(item)

    def count(self) -> int:
        """
        Return the number of items in the layout.

        Returns
        -------
        int
            The count of items currently in the layout.
        """
        return len(self.itemList)

    def itemAt(self, index: int) -> QtWidgets.QLayoutItem:
        """
        Return the layout item at the given index.

        Parameters
        ----------
        index : int
            The index of the item.

        Returns
        -------
        QLayoutItem or None
            The layout item if index is valid; otherwise, None.
        """
        if 0 <= index < len(self.itemList):
            return self.itemList[index]
        return None

    def takeAt(self, index: int) -> QtWidgets.QLayoutItem:
        """
        Remove and return the layout item at the given index.

        Parameters
        ----------
        index : int
            The index of the item to remove.

        Returns
        -------
        QLayoutItem or None
            The removed layout item if index is valid; otherwise, None.
        """
        if 0 <= index < len(self.itemList):
            return self.itemList.pop(index)
        return None

    def expandingDirections(self) -> QtCore.Qt.Orientations:
        """
        Specify the directions in which the layout can expand.

        Returns
        -------
        Qt.Orientations
            A combination of Qt.Horizontal and Qt.Vertical indicating that the layout can expand in both directions.
        """
        return QtCore.Qt.Horizontal | QtCore.Qt.Vertical

    def hasHeightForWidth(self) -> bool:
        """
        Indicate that this layout has a height-for-width dependency.

        Returns
        -------
        bool
            True, since the layout's height depends on its width.
        """
        return True

    def heightForWidth(self, width: int) -> int:
        """
        Calculate the height of the layout given a specific width.

        Parameters
        ----------
        width : int
            The width to calculate the height for.

        Returns
        -------
        int
            The computed height based on the layout of items.
        """
        return self.doLayout(QtCore.QRect(0, 0, width, 0), True)

    def setGeometry(self, rect: QtCore.QRect) -> None:
        """
        Set the geometry of the layout and position the child items.

        Parameters
        ----------
        rect : QRect
            The rectangle that defines the area available for the layout.
        """
        super().setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self) -> QtCore.QSize:
        """
        Provide a recommended size for the layout.

        Returns
        -------
        QSize
            The recommended size, based on the minimum size of the items.
        """
        return self.minimumSize()

    def minimumSize(self) -> QtCore.QSize:
        """
        Calculate the minimum size required by the layout.

        Returns
        -------
        QSize
            The minimum size that can contain all layout items with margins.
        """
        size = QtCore.QSize()
        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QtCore.QSize(margins.left() + margins.right(),
                             margins.top() + margins.bottom())
        return size

    def doLayout(self, rect: QtCore.QRect, testOnly: bool) -> int:
        """
        Layout the items within the given rectangle.

        Items are arranged horizontally until there is no more space, then they wrap
        to the next line. This method is used both for setting the geometry and for
        calculating the required height.

        Parameters
        ----------
        rect : QRect
            The rectangle within which to layout the items.
        testOnly : bool
            If True, the layout is calculated but item geometries are not set.

        Returns
        -------
        int
            The total height required by the layout.
        """
        x = rect.x()
        y = rect.y()
        lineHeight = 0

        for item in self.itemList:
            widget = item.widget()
            spaceX = self.spacing() + widget.style().layoutSpacing(
                QtWidgets.QSizePolicy.PushButton, QtWidgets.QSizePolicy.PushButton, QtCore.Qt.Horizontal)
            spaceY = self.spacing() + widget.style().layoutSpacing(
                QtWidgets.QSizePolicy.PushButton, QtWidgets.QSizePolicy.PushButton, QtCore.Qt.Vertical)
            nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > rect.right() and lineHeight > 0:
                x = rect.x()
                y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0
            if not testOnly:
                item.setGeometry(QtCore.QRect(QtCore.QPoint(x, y), item.sizeHint()))
            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())
        return y + lineHeight - rect.y()
