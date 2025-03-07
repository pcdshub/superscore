"""
Core widget classes for qt-based GUIs.
"""
from __future__ import annotations

from pathlib import Path
from typing import ClassVar, List, Optional
from weakref import WeakValueDictionary

from pcdsutils.qt.designer_display import DesignerDisplay
from qtpy import QtCore, QtWidgets

from superscore.client import Client
from superscore.qt_helpers import QDataclassBridge, QDataclassList
from superscore.type_hints import AnyDataclass, OpenPageSlot
from superscore.utils import SUPERSCORE_SOURCE_PATH
from superscore.widgets import get_window
from superscore.widgets.manip_helpers import (FrameOnEditFilter,
                                              match_line_edit_text_width)


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
    tags_content: QtWidgets.QVBoxLayout
    add_tag_button: QtWidgets.QToolButton
    tags_frame: QtWidgets.QFrame
    extra_text_label: QtWidgets.QLabel

    def __init__(self, data: AnyDataclass, **kwargs):
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
            self.tags_frame.hide()
        else:
            self.init_tags()

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

    def init_tags(self) -> None:
        """
        Set up the various tags widgets appropriately.
        """
        tags_list = TagsWidget(
            data_list=self.bridge.tags,
            layout=QtWidgets.QHBoxLayout(),
        )
        self.tags_content.addWidget(tags_list)

        def add_tag() -> None:
            if tags_list.widgets and not tags_list.widgets[-1].line_edit.text().strip():
                # Don't add another tag if we haven't filled out the last one
                return

            elem = tags_list.add_item('')
            elem.line_edit.setFocus()

        self.add_tag_button.clicked.connect(add_tag)


class TagsWidget(QtWidgets.QWidget):
    """
    A widget used to edit a QDataclassList tags field.

    Aims to emulate the look and feel of typical tags fields
    in online applications.

    Parameters
    ----------
    data_list : QDataclassList
        The dataclass list to edit using this widget.
    layout : QLayout
        The layout to use to arrange our labels. This should be an
        instantiated but not placed layout. This lets us have some
        flexibility in whether we arrange things horizontally,
        vertically, etc.
    """
    widgets: List[TagsElem]

    def __init__(
        self,
        data_list: QDataclassList,
        layout: QtWidgets.QLayout,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.data_list = data_list
        self.setLayout(layout)
        self.widgets = []
        starting_list = data_list.get()
        if starting_list is not None:
            for starting_value in starting_list:
                self.add_item(starting_value, init=True)

    def add_item(
        self,
        starting_value: str,
        init: bool = False,
        **kwargs,
    ) -> TagsElem:
        """
        Create and add new editable widget element to this widget's layout.

        This can either be an existing string on the dataclass list to keep
        track of, or it can be used to add a new string to the dataclass list.

        This method will also set up the signals and slots for the new widget.

        Parameters
        ----------
        starting_value : str
            The starting text value for the new widget element.
            This should match the text exactly for tracking existing
            strings.
        checked : bool, optional
            This argument is unused, but it will be sent by various button
            widgets via the "clicked" signal so it must be present.
        init : bool, optional
            Whether or not this is the initial initialization of this widget.
            This will be set to True in __init__ so that we don't mutate
            the underlying dataclass. False, the default, means that we're
            adding a new string to the dataclass, which means we should
            definitely append it.
        **kwargs : from qt signals
            Other kwargs sent along with qt signals will be ignored.

        Returns
        -------
        strlistelem : StrListElem
            The widget created by this function call.
        """
        new_widget = TagsElem(starting_value, self)
        self.widgets.append(new_widget)
        if not init:
            self.data_list.append(starting_value)
        self.layout().addWidget(new_widget)
        return new_widget

    def save_item_update(self, item: TagsElem, new_value: str) -> None:
        """
        Update the dataclass as appropriate when the user submits a new value.

        Parameters
        ----------
        item : StrListElem
            The widget that the user has edited.
        new_value : str
            The value that the user has submitted.
        """
        index = self.widgets.index(item)
        self.data_list.put_to_index(index, new_value)

    def remove_item(self, item: TagsElem) -> None:
        """
        Update the dataclass as appropriate when the user removes a value.

        Parameters
        ----------
        item : StrListElem
            The widget that the user has clicked the delete button for.
        """
        index = self.widgets.index(item)
        self.widgets.remove(item)
        self.data_list.remove_index(index)
        item.deleteLater()


class TagsElem(Display, QtWidgets.QWidget):
    """
    A single element for the TagsWidget.

    Has a QLineEdit for changing the text and a delete button.
    Changes its style to no frame when it has text and is out of focus.
    Only shows the delete button when the text is empty.

    Parameters
    ----------
    start_text : str
        The starting text for this tag.
    tags_widget : TagsWidget
        A reference to the TagsWidget that contains this widget.
    """
    filename = 'tags_elem.ui'

    line_edit: QtWidgets.QLineEdit
    del_button: QtWidgets.QToolButton

    def __init__(self, start_text: str, tags_widget: TagsWidget, **kwargs):
        super().__init__(**kwargs)
        self.line_edit.setText(start_text)
        self.tags_widget = tags_widget
        edit_filter = FrameOnEditFilter(parent=self)
        edit_filter.set_no_edit_style(self.line_edit)
        self.line_edit.installEventFilter(edit_filter)
        self.on_text_changed(start_text)
        self.line_edit.textChanged.connect(self.on_text_changed)
        self.line_edit.textEdited.connect(self.on_text_edited)
        self.del_button.clicked.connect(self.on_del_clicked)
        icon = self.style().standardIcon(QtWidgets.QStyle.SP_TitleBarCloseButton)
        self.del_button.setIcon(icon)

    def on_text_changed(self, text: str) -> None:
        """
        Edit our various visual elements when the text changes.

        This will do all of the following:
        - make the delete button show only when the text field is empty
        - adjust the size of the text field to be roughly the size of the
          string we've inputted
        """
        # Show or hide the del button as needed
        self.del_button.setVisible(not text)
        # Adjust the width to match the text
        match_line_edit_text_width(self.line_edit, text=text)

    def on_data_changed(self, data: str) -> None:
        """
        Change the text displayed here using new data, if needed.
        """
        if self.line_edit.text() != data:
            self.line_edit.setText(data)

    def on_text_edited(self, text: str) -> None:
        """
        Update the dataclass when the user edits the text.
        """
        self.tags_widget.save_item_update(
            item=self,
            new_value=text,
        )

    def on_del_clicked(self, **kwargs) -> None:
        """
        Tell the QTagsWidget when our delete button is clicked.
        """
        self.tags_widget.remove_item(self)


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

    def refresh_window(self):
        """Refresh window ui elements"""
        # tree view
        window = get_window()
        window.tree_view.set_data(self.client.backend.root)
        window.tree_view.model().refresh_tree()
