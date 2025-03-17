"""
Core widget classes for qt-based GUIs.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar, Collection, Dict, Optional
from weakref import WeakValueDictionary

from pcdsutils.qt.designer_display import DesignerDisplay
from qtpy import QtCore, QtGui, QtWidgets

from superscore.client import Client
from superscore.qt_helpers import QDataclassBridge, QDataclassSet
from superscore.type_hints import AnyDataclass, OpenPageSlot
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

        tag_strings = kwargs.pop('tag_options', dict())

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
            self.init_tags(tag_strings)

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

    def init_tags(self, tag_strings: dict[int, str]) -> None:
        """
        Set up the various tags widgets appropriately.
        """
        tag_options = {string: index for index, string in tag_strings.items()}

        self.tags_widget.setObjectName("TagsWidget")
        self.tags_widget.set_tag_strings(tag_strings)
        self.tags_widget.set_tags(self.bridge.tags)

        def add_tag_to_container(string: str) -> None:
            tag = tag_options[string]
            if tag in self.bridge.tags.get():
                return
            self.tags_widget.add_tag(tag)

        self.tags_widget.editor.tag_added.connect(add_tag_to_container)


class TagsWidget(QtWidgets.QWidget):
    """
    A container for TagsElem objects arranged in a flow layout.

    This widget manages a collection of tag elements, allowing the addition
    and removal of tags. The tags are arranged using a custom FlowLayout that
    automatically wraps the tags when they reach the edge of the widget.

    Attributes
    ----------
    widgets : List[TagsElem]
        List of tag elements currently contained in the widget.
    tags : QDataclassSet
        A data structure that holds the underlying data for the tags.
    flow_layout : FlowLayout
        The layout that manages the arrangement of the tag elements.
    """

    tagStringsSet = QtCore.Signal(object)

    def __init__(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the TagsWidget.

        Parameters
        ----------
        tags : QDataclassSet, optional
            An object that contains the initial set of tags. It is expected to
            have a `get()`, `add()`, and `remove()` method.
        tag_strings : Optional[Dict[int, str]]
            A map from tag id to tag string
        *args : Any
            Additional positional arguments passed to the base QWidget.
        **kwargs : Any
            Additional keyword arguments passed to the base QWidget.
        """
        super().__init__(*args, **kwargs)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding
        )

        layout = QtWidgets.QVBoxLayout()
        layout.setObjectName("TagsWidgetLayout")
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        tag_chip_layout = QtWidgets.QHBoxLayout()
        tag_chip_layout.setObjectName("TagChipLayout")
        layout.addLayout(tag_chip_layout)
        label = QtWidgets.QLabel()
        label.setText("Tags:")
        tag_chip_layout.addWidget(label)
        self.flow_layout = FlowLayout(margin=0, spacing=5)
        self.flow_layout.setObjectName("TagFlowLayout")
        tag_chip_layout.addLayout(self.flow_layout)

        tag_input_layout = QtWidgets.QHBoxLayout()
        tag_input_layout.setObjectName("TagsWidgetInputLayout")
        self.editor = TagEditor()
        self.tagStringsSet.connect(lambda d: self.editor.set_tag_strings(d.values()))
        layout.addWidget(self.editor)

        self.tags = set()
        self.tag_strings = {}

    def add_tag(self, tag_id: int, init: bool = False, **kwargs: Any) -> TagsElem:
        """
        Create and add a new editable tag element to the widget's layout.

        This method creates a new TagsElem with the given starting value, sets up
        its signals, and adds it to the flow layout. If not during initialization,
        the tag is also appended to the underlying tags.

        Parameters
        ----------
        tag_id : int
            The text value for the new tag element.
        init : bool, optional
            Flag indicating whether this is part of the initial setup (True) or a new
            addition (False). Defaults to False.
        **kwargs : Any
            Additional keyword arguments passed by Qt signals (ignored).

        Returns
        -------
        TagsElem
            The newly created tag element.
        """
        tag = TagsElem(tag_id, parent=self)
        if not init and self.tags is not None:
            self.tags.add(tag_id)
        self.flow_layout.addWidget(tag)
        return tag

    def remove_tag(self, tag: TagsElem) -> None:
        """
        Remove a tag element from the widget and update the underlying tags.

        Parameters
        ----------
        tag : TagsElem
            The tag element to remove.
        """
        if self.tags is not None:
            self.tags.remove_value(tag.tag)
        tag.setParent(None)
        tag.deleteLater()

    def set_tags(self, tags: Optional[QDataclassSet]) -> None:
        self.tags = tags
        if self.tags is not None:
            starting_set = self.tags.get()
            if starting_set is not None:
                for starting_value in starting_set:
                    self.add_tag(starting_value, init=True)

    def set_tag_strings(self, tag_strings: Dict[int, str]) -> None:
        self.tag_strings = tag_strings
        self.tagStringsSet.emit(self.tag_strings)


class TagsElem(QtWidgets.QWidget):
    """
    A single element for the TagsWidget.

    This widget represents a tag with a label and a remove button. When the
    remove button is clicked, the element notifies its parent TagsWidget to
    remove it.

    Parameters
    ----------
    start_text : str
        The starting text for this tag.
    **kwargs : Any
        Additional keyword arguments to pass to the base QWidget.
    """
    def __init__(self, tag: int, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        self.tag = tag

        self.label: QtWidgets.QLabel = QtWidgets.QLabel(self.parent().tag_strings[tag])
        self.remove_button: QtWidgets.QToolButton = QtWidgets.QToolButton()
        self.remove_button.setText("X")
        self.remove_button.setToolTip("Remove this tag")

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(5)
        layout.addWidget(self.label)
        layout.addWidget(self.remove_button)

        self.remove_button.clicked.connect(self.remove)

    def remove(self) -> None:
        """
        Handle the remove button click.

        This slot notifies the parent TagsWidget to remove this tag element and then
        schedules this widget for deletion.
        """
        self.parent().remove_tag(self)


class TagEditor(QtWidgets.QWidget):
    """
    TagEditor widget for managing tags.

    This widget includes an editable combo box and an "Add" button for creating
    and adding new tags. It uses a completer to suggest predefined tags as the
    user types.

    Attributes
    ----------
    tag_added : QtCore.Signal
        Signal emitted when a valid tag is added.
    filename : str
        The UI file name for the widget.
    input_line : QtWidgets.QComboBox
        The combo box widget used for entering and selecting tags.
    add_button : QtWidgets.QPushButton
        The button used to trigger the tag addition.
    layout : QtWidgets.QHBoxLayout
        The layout managing the arrangement of the widgets.
    """
    tag_added = QtCore.Signal(str)

    def __init__(self) -> None:
        """
        Initialize the TagEditor widget.
        """
        super().__init__()

        self.tag_strings = set()

        layout = QtWidgets.QHBoxLayout()
        layout.setObjectName("TagEditorLayout")
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.add_button = QtWidgets.QPushButton("Add")
        self.add_button.clicked.connect(self.add_tag)
        layout.addWidget(self.add_button)

        self.input_line = QtWidgets.QComboBox()
        layout.addWidget(self.input_line)

        self.input_line.setEditable(True)
        font_metrics = QtGui.QFontMetrics(self.input_line.lineEdit().font())
        placeholder_text = "Add tag..."
        placeholder_width = font_metrics.horizontalAdvance(placeholder_text)
        self.input_line.lineEdit().setPlaceholderText(placeholder_text)
        self.input_line.setMinimumWidth(placeholder_width + 40)
        self.input_line.lineEdit().clear()
        self.input_line.lineEdit().returnPressed.connect(self.add_tag)

        layout.addStretch()

    def add_tag(self) -> None:
        """
        Handle the add action when the Add button is clicked or Return is pressed.

        Retrieves the current text from the combo box, strips any leading or trailing
        whitespace, and if the text is in the list of predefined tags, emits the
        `tag_added` signal.
        """
        text = self.input_line.currentText().strip()
        if text in self.tag_strings:
            self.tag_added.emit(text)

    def set_tag_strings(self, strings: Collection[str]) -> None:
        self.tag_strings = strings

        self.input_line.clear()
        self.input_line.addItems(strings)
        self.input_line.lineEdit().clear()

        completer = QtWidgets.QCompleter(strings, self.input_line)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        completer.setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
        completer.setFilterMode(QtCore.Qt.MatchContains)
        self.input_line.setCompleter(completer)


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
