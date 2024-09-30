"""
Qt tree model and item classes for visualizing Entry dataclasses
"""

from __future__ import annotations

import logging
import time
from enum import Enum, IntEnum, auto
from typing import (Any, Callable, ClassVar, Dict, Generator, List, Optional,
                    Union)
from uuid import UUID
from weakref import WeakValueDictionary

import numpy as np
import qtawesome as qta
from qtpy import QtCore, QtGui, QtWidgets

from superscore.backends.core import SearchTerm
from superscore.client import Client
from superscore.control_layers import EpicsData
from superscore.model import (Collection, Entry, Nestable, Parameter, Readback,
                              Root, Setpoint, Severity, Snapshot, Status)
from superscore.qt_helpers import QDataclassBridge
from superscore.widgets import ICON_MAP

logger = logging.getLogger(__name__)


PVEntry = Union[Parameter, Setpoint, Readback]


class CustRoles(IntEnum):
    DisplayTypeRole = QtCore.Qt.UserRole
    EpicsDataRole = auto()


class EntryItem:
    """Node representing one Entry"""
    _bridge_cache: ClassVar[
        WeakValueDictionary[int, QDataclassBridge]
    ] = WeakValueDictionary()
    bridge: QDataclassBridge
    _data: Entry

    def __init__(
        self,
        data: Entry,
        tree_parent: Optional[EntryItem] = None,
    ):
        self._data = data
        self._parent = None
        self._columncount = 2
        # Consider making children a property that looks at underlying data
        self._children: List[EntryItem] = []
        self._parent = None
        self._row = 0  # (self._row)th child of this item's parent
        if tree_parent:
            tree_parent.addChild(self)

        # Assign bridge, for updating the entry properties when data changes?
        # For this to be relevant we need to subscribe to the bridge,
        # for example to change icons on type update
        if self._data:
            try:
                self.bridge = self._bridge_cache[id(data)]
            except KeyError:
                bridge = QDataclassBridge(data)
                self._bridge_cache[id(data)] = bridge
                self.bridge = bridge

    def fill_uuids(self, client: Optional[Client] = None) -> None:
        """Fill this item's data if it is a uuid, using ``client``"""
        if isinstance(self._data, UUID) and client is not None:
            self._data = list(client.search(SearchTerm('uuid', 'eq', self._data)))[0]

    def data(self, column: int) -> Any:
        """
        Return the data for the requested column.
        Column 0: name
        Column 1: description

        Parameters
        ----------
        column : int
            data column requested

        Returns
        -------
        Any
        """
        if self._data is None:
            # This should never be seen
            return '<root>'

        if column == 0:
            if isinstance(self._data, Nestable):
                return getattr(self._data, 'title', 'root')
            else:
                return getattr(self._data, 'pv_name', '<no pv>')
        elif column == 1:
            return getattr(self._data, 'description', '<no desc>')

        # TODO: something about icons

    def tooltip(self) -> str:
        """Construct the tooltip based on the stored entry"""
        return self._data.uuid

    def columnCount(self) -> int:
        """Return the item's column count"""
        return self._columncount

    def childCount(self) -> int:
        """Return the item's child count"""
        return len(self._children)

    def child(self, row: int) -> EntryItem:
        """Return the item's child"""
        if row >= 0 and row < self.childCount():
            return self._children[row]

    def get_children(self) -> Generator[EntryItem, None, None]:
        """Yield this item's children"""
        yield from self._children

    def parent(self) -> EntryItem:
        """Return the item's parent"""
        return self._parent

    def row(self) -> int:
        """Return the item's row under its parent"""
        return self._row

    def addChild(self, child: EntryItem) -> None:
        """
        Add a child to this item.

        Parameters
        ----------
        child : EntryItem
            Child EntryItem to add to this EntryItem
        """
        child._parent = self
        child._row = len(self._children)
        self._children.append(child)

    def removeChild(self, child: EntryItem) -> None:
        """Remove ``child`` from this EntryItem"""
        try:
            self._children.remove(child)
        except ValueError:
            logger.debug(f"EntryItem ({child}) is not a child of this parent ({self})")
            return
        child._parent = None
        # re-assign rows to children
        remaining_children = self.takeChildren()
        for rchild in remaining_children:
            self.addChild(rchild)

    def replaceChild(self, old_child: EntryItem, new_child: EntryItem) -> None:
        """Replace ``old_child`` with ``new_child``, maintaining order"""
        for idx in range(self.childCount()):
            if self.child(idx) is old_child:
                self._children[idx] = new_child
                new_child._parent = self
                new_child._row = idx

                # dereference old_child
                old_child._parent = None
                return

        raise IndexError('old child not found, could not replace')

    def takeChild(self, idx: int) -> EntryItem:
        """Remove and return the ``idx``-th child of this item"""
        child = self._children.pop(idx)
        child._parent = None
        # re-assign rows to children
        remaining_children = self.takeChildren()
        for rchild in remaining_children:
            self.addChild(rchild)

        return child

    def insertChild(self, idx: int, child: EntryItem) -> None:
        """Add ``child`` to this EntryItem at index ``idx``"""
        self._children.insert(idx, child)
        # re-assign rows to children
        remaining_children = self.takeChildren()
        for rchild in remaining_children:
            self.addChild(rchild)

    def takeChildren(self) -> list[EntryItem]:
        """
        Remove and return this item's children
        """
        children = self._children
        self._children = []
        for child in children:
            child._parent = None

        return children

    def icon(self):
        """return icon for this item"""
        icon_id = ICON_MAP.get(type(self._data), None)
        if icon_id is None:
            return
        return qta.icon(icon_id)


def build_tree(entry: Entry, parent: Optional[EntryItem] = None) -> EntryItem:
    """
    Walk down the ``entry`` tree and create an `EntryItem` for each, linking
    them to their parents

    Parameters
    ----------
    entry : Entry
        the top-level item to start with

    parent : EntryItem, optional
        the parent `EntryItem` of ``entry``

    Returns
    -------
    EntryItem
        the constructed `EntryItem` with parent-child linkages
    """

    item = EntryItem(entry, tree_parent=parent)
    if isinstance(entry, Root):
        for child in entry.entries:
            build_tree(child, parent=item)
    elif isinstance(entry, Nestable):
        for child in entry.children:
            build_tree(child, parent=item)

    return item


class RootTree(QtCore.QAbstractItemModel):
    """
    Item model for the database tree-view.
    This model will query the client for entry information.
    Attempts to be lazy with its representation, only querying data when necessary.
    This model should only care about the metadata and structure of the Entry's
    it displays, not the contents (pv-names, values, links, etc)

    This model will be as lazy as the Client allows.  If the client can provide
    uuid-ified entries, this model can be modified to be more performant / lazy

    The base implementation likely does none of this
    """
    def __init__(
        self,
        *args,
        base_entry: Entry,
        client: Optional[Client] = None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.base_entry = base_entry
        self.root_item = build_tree(base_entry)
        self.client = client
        self.headers = ['name', 'description']

    def refresh_tree(self) -> None:
        self.layoutAboutToBeChanged.emit()
        self.root_item = build_tree(self.base_entry)
        self.layoutChanged.emit()

    def headerData(
        self,
        section: int,
        orientation: QtCore.Qt.Orientation,
        role: int
    ) -> Any:
        """
        Returns the header data for the model.
        Currently only displays horizontal header data

        Parameters
        ----------
        section : int
            section to provide header information for
        orientation : Qt.Orientation
            header orientation, Qt.Horizontal or Qt.Vertical
        role : int
            Qt role to provide header information for

        Returns
        -------
        Any
            requested header data
        """
        if role != QtCore.Qt.DisplayRole:
            return

        if orientation == QtCore.Qt.Horizontal:
            return self.headers[section]

    def index(
        self,
        row: int,
        column: int,
        parent: QtCore.QModelIndex = QtCore.QModelIndex()
    ) -> QtCore.QModelIndex:
        """
        Returns the index of the item in the model.

        In a tree view the rows are defined relative to parent item.  If an
        item is the first child under its parent, it will have row=0,
        regardless of the number of items in the tree.

        Parameters
        ----------
        row : int
            The row of the requested index.
        column : int
            The column of the requested index
        parent : QtCore.QModelIndex, optional
            The parent of the requested index, by default None

        Returns
        -------
        QtCore.QModelIndex
        """
        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()

        parent_item = None
        if not parent or not parent.isValid():
            parent_item = self.root_item
        else:
            parent_item = parent.internalPointer()

        child_item = parent_item.child(row)
        if child_item:
            return self.createIndex(row, column, child_item)

        # all else return invalid index
        return QtCore.QModelIndex()

    def index_from_item(self, item: EntryItem) -> QtCore.QModelIndex:
        return self.createIndex(item.row(), 0, item)

    def parent(self, index: QtCore.QModelIndex) -> QtCore.QModelIndex:
        """

        Parameters
        ----------
        index : QtCore.QModelIndex
            item to retrieve parent of

        Returns
        -------
        QtCore.QModelIndex
            index of the parent item
        """
        if not index.isValid():
            return QtCore.QModelIndex()
        child = index.internalPointer()
        if child is self.root_item:
            return QtCore.QModelIndex()
        parent = child.parent()
        if parent in (self.root_item, None):
            return QtCore.QModelIndex()

        return self.createIndex(parent.row(), 0, parent)

    def rowCount(self, parent: QtCore.QModelIndex) -> int:
        """
        Called by tree view to determine number of children an item has.

        Parameters
        ----------
        parent : QtCore.QModelIndex
            index of the parent item being queried

        Returns
        -------
        int
            number of children ``parent`` has
        """
        if not parent.isValid():
            parent_item = self.root_item
        else:
            parent_item = parent.internalPointer()
        return parent_item.childCount()

    def columnCount(self, parent: QtCore.QModelIndex) -> int:
        """
        Called by tree view to determine number of columns of data ``parent`` has

        Parameters
        ----------
        parent : QtCore.QModelIndex

        Returns
        -------
        int
            number of columns ``parent`` has
        """
        if not parent.isValid():
            parent_item = self.root_item
        else:
            parent_item = parent.internalPointer()
        return parent_item.columnCount()

    def data(self, index: QtCore.QModelIndex, role: int) -> Any:
        """
        Returns the data stored under the given ``role`` for the item
        referred to by the ``index``.  Uses and assumes ``EntryItem`` methods.

        Parameters
        ----------
        index : QtCore.QModelIndex
            index that identifies the portion of the model in question
        role : int
            the data role

        Returns
        -------
        Any
            The data to be displayed by the model
        """
        if not index.isValid():
            return None

        item: EntryItem = index.internalPointer()  # Gives original EntryItem
        item.fill_uuids(client=self.client)

        # special handling for status info
        if index.column() == 1:
            if role == QtCore.Qt.DisplayRole:
                return item.data(1)
            if role == QtCore.Qt.TextAlignmentRole:
                return QtCore.Qt.AlignLeft

        if role == QtCore.Qt.ToolTipRole:
            return item.tooltip()
        if role == QtCore.Qt.DisplayRole:
            return item.data(index.column())

        if role == CustRoles.DisplayTypeRole:
            return item

        if role == QtCore.Qt.DecorationRole and index.column() == 0:
            return item.icon()

        return None


class BaseTableEntryModel(QtCore.QAbstractTableModel):
    """
    Common methods for table model that holds onto entries.
    To subclass this:
    - implement the `.data()` method and specify handling for your chosen columns
    and Qt display roles
    - define the header names
    - define any custom functionality

    Enables the editable flag for the last row for open-page-buttons

    Parameters
    ----------
    entries : Optional[List[Entry]], optional
        A list of Entry objects to display in the table, by default None

    """
    entries: List[Entry]
    headers: List[str]
    _editable_cols: Dict[int, bool] = {}

    def __init__(
        self,
        *args,
        entries: Optional[List[Entry]] = None,
        **kwargs
    ) -> None:
        self.entries = entries or []
        super().__init__(*args, **kwargs)

    def rowCount(self, parent_index: Optional[QtCore.QModelIndex] = None):
        return len(self.entries)

    def columnCount(self, parent_index: Optional[QtCore.QModelIndex] = None):
        return len(self.headers)

    def set_entries(self, entries: List[Entry]):
        """
        Set the entries for this table.  Subclasses will need to override
        in order to encapsulate all logic between `layoutAboutToBeChanged` and
        `layoutChanged` signals.  (super().set_entries should not be called)
        """
        self.layoutAboutToBeChanged.emit()
        self.entries = entries
        self.layoutChanged.emit()

    def headerData(
        self,
        section: int,
        orientation: QtCore.Qt.Orientation,
        role: int = QtCore.Qt.DisplayRole
    ) -> Any:
        """
        Returns the header data for the model.
        Currently only displays horizontal header data
        """
        if role != QtCore.Qt.DisplayRole:
            return

        if orientation == QtCore.Qt.Horizontal:
            return self.headers[section]

    def set_editable(self, col_index: int, editable: bool) -> None:
        """If a column is allowed to be editable, set it as editable"""
        self._editable_cols[col_index] = editable

    def flags(self, index: QtCore.QModelIndex) -> QtCore.Qt.ItemFlag:
        """
        Returns the item flags for the given ``index``.  The returned
        item flag controls what behaviors the item supports.

        Parameters
        ----------
        index : QtCore.QModelIndex
            the index referring to a cell of the TableView

        Returns
        -------
        QtCore.Qt.ItemFlag
            the ItemFlag corresponding to the cell
        """
        if self._editable_cols[index.column()]:
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable
        else:
            return QtCore.Qt.ItemIsEnabled

    def add_entry(self, entry: Entry) -> None:
        if entry in self.entries or not isinstance(entry, Entry):
            return

        self.layoutAboutToBeChanged.emit()
        self.entries.append[entry]
        self.layoutChanged.emit()

    def remove_row(self, row_index: int) -> None:
        self.remove_entry(self.entries[row_index])

    def remove_entry(self, entry: Entry) -> None:
        self.layoutAboutToBeChanged.emit()
        try:
            self.entries.remove(entry)
        except ValueError:
            logger.debug(f"Entry of type ({type(entry).__name__})"
                         "not found in table, could not remove.")
        self.layoutChanged.emit()

    def icon(self, entry: Entry) -> Optional[QtGui.QIcon]:
        """return icon for this ``entry``"""
        icon_id = ICON_MAP.get(type(entry), None)
        if icon_id is None:
            return
        return qta.icon(icon_id)


class DisplayType(Enum):
    """type of data displayed in tables"""
    PV_NAME = auto()
    STATUS = auto()
    SEVERITY = auto()
    EPICS_DATA = auto()


class LivePVHeader(IntEnum):
    """
    Enum for more readable header names.  Underscores will be replaced with spaces
    """
    PV_NAME = 0
    STORED_VALUE = auto()
    LIVE_VALUE = auto()
    TIMESTAMP = auto()
    STORED_STATUS = auto()
    LIVE_STATUS = auto()
    STORED_SEVERITY = auto()
    LIVE_SEVERITY = auto()
    OPEN = auto()
    REMOVE = auto()

    def header_name(self) -> str:
        return self.name.title().replace('_', ' ')

    @classmethod
    def from_header_name(cls, name: str) -> LivePVHeader:
        return LivePVHeader[name.upper().replace(' ', '_')]


class LivePVTableModel(BaseTableEntryModel):
    # Takes PV-entries
    # shows live details (current PV status, severity)
    # shows setpoints (can be blank)
    # TO-DO:
    # open details delegate
    # methods for hide un-needed rows (user interaction?)
    headers: List[str]
    _data_cache: Dict[str, EpicsData]
    _poll_thread: Optional[_PVPollThread]
    _header_to_field: Dict[LivePVHeader, str] = {
        LivePVHeader.PV_NAME: 'pv_name',
        LivePVHeader.STORED_VALUE: 'data',
        LivePVHeader.STORED_STATUS: 'status',
        LivePVHeader.STORED_SEVERITY: 'severity',
    }

    def __init__(
        self,
        *args,
        client: Client,
        entries: Optional[List[PVEntry]] = None,
        poll_period: float = 1.0,
        **kwargs
    ) -> None:
        super().__init__(*args, entries=entries, **kwargs)
        self.headers = [h.header_name() for h in LivePVHeader]

        self._editable_cols = {h.value: False for h in LivePVHeader}
        self._editable_cols[LivePVHeader.OPEN] = True
        self._editable_cols[LivePVHeader.REMOVE] = True

        self.client = client
        self.poll_period = poll_period
        self._data_cache = {e.pv_name: None for e in entries}
        self._poll_thread = None

        self.start_polling()

    def start_polling(self) -> None:
        """Start the polling thread"""
        if self._poll_thread and self._poll_thread.isRunning():
            return

        self._poll_thread = _PVPollThread(
            data=self._data_cache,
            poll_period=self.poll_period,
            client=self.client,
            parent=self
        )
        self._data_cache = self._poll_thread.data
        self._poll_thread.data_ready.connect(self._data_ready)
        self._poll_thread.finished.connect(self._poll_thread_finished)

        self._poll_thread.start()

    def stop_polling(self, wait_time: float = 0.0) -> None:
        """
        stop the polling thread, and mark it as stopped.
        wait time in ms
        """
        if self._poll_thread is None or not self._poll_thread.isRunning():
            return

        logger.debug(f"stopping and de-referencing thread @ {id(self._poll_thread)}")
        # does not remove reference to avoid premature python garbage collection
        self._poll_thread.data = {}
        self._poll_thread.stop()

        if wait_time > 0.0:
            self._poll_thread.wait(wait_time)

    @QtCore.Slot()
    def _poll_thread_finished(self):
        """Slot: poll thread finished and returned."""
        if self._poll_thread is None:
            return

        self._poll_thread.data_ready.disconnect(self._data_ready)
        self._poll_thread.finished.disconnect(self._poll_thread_finished)

    @QtCore.Slot()
    def _data_ready(self) -> None:
        """
        Slot: initial indication from _DevicePollThread that the data dictionary is ready.
        """
        self.beginResetModel()
        self.endResetModel()

        if self._poll_thread is not None:
            self._poll_thread.data_changed.connect(self._data_changed)

    @QtCore.Slot(str)
    def _data_changed(self, pv_name: str) -> None:
        """
        Slot: data changed for the given attribute in the thread.
        Signals the entire row to update (a single PV worth of data)
        """
        try:
            row = list(self._data_cache).index(pv_name)
        except IndexError:
            ...
        else:
            self.dataChanged.emit(
                self.createIndex(row, 0),
                self.createIndex(row, self.columnCount()),
            )

    def set_entries(self, entries: list[PVEntry]) -> None:
        """Set the entries for this table, reset data cache"""
        self.layoutAboutToBeChanged.emit()
        self.entries = entries
        self._data_cache = {e.pv_name: None for e in entries}
        self._poll_thread.data = self._data_cache
        self.dataChanged.emit(
            self.createIndex(0, 0),
            self.createIndex(self.rowCount(), self.columnCount()),
        )
        self.layoutChanged.emit()

    def remove_entry(self, entry: PVEntry) -> None:
        """Remove ``entry`` from the table model"""
        super().remove_entry(entry)
        self.layoutAboutToBeChanged.emit()
        self._data_cache = {e.pv_name: None for e in self.entries}
        self._poll_thread.data = self._data_cache
        self.layoutChanged.emit()

    def index_from_item(
        self,
        item: PVEntry,
        column: Union[str, int]
    ) -> QtCore.QModelIndex:
        """
        Create an index given a `PVEntry` and desired column.
        The column name must be an option in `LivePVHeaderEnum`, or able to be
        converted to one by swapping ' ' with '_'

        Parameters
        ----------
        item : PVEntry
            A PVEntry dataclass instance
        column : Union[str, int]
            A column name or column index

        Returns
        -------
        QtCore.QModelIndex
            The corresponding model index
        """
        row = self.entries.index(item)
        if isinstance(column, int):
            col = column
        elif isinstance(column, str):
            col = LivePVHeader.from_header_name(column).value
        return self.createIndex(row, col, item)

    def data(self, index: QtCore.QModelIndex, role: int) -> Any:
        """
        Returns the data stored under the given role for the item
        referred to by the index.

        UserRole provides data necessary to generate an edit delegate for the
        cell based on the data-type

        Parameters
        ----------
        index : QtCore.QModelIndex
            An index referring to a cell of the TableView
        role : int
            The requested data role.

        Returns
        -------
        Any
            the requested data
        """
        entry: PVEntry = self.entries[index.row()]
        if isinstance(entry, UUID):
            entry = self.client.backend.get_entry(self.entries[index.row()])
            self.entries[index.row()] = entry

        if index.column() == LivePVHeader.PV_NAME:
            if role == QtCore.Qt.DecorationRole:
                return self.icon(entry)
            elif role == QtCore.Qt.DisplayRole:
                name_text = getattr(entry, 'pv_name')
                return name_text
            elif role == CustRoles.DisplayTypeRole:
                return DisplayType.PV_NAME

        if role not in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole,
                        QtCore.Qt.BackgroundRole, CustRoles.DisplayTypeRole,
                        CustRoles.EpicsDataRole):
            # Other parts of the table are read only
            return QtCore.QVariant()

        if index.column() == LivePVHeader.STORED_VALUE:
            cache_data = self.get_cache_data(entry.pv_name)
            if role == CustRoles.DisplayTypeRole:
                return DisplayType.EPICS_DATA
            elif role == CustRoles.EpicsDataRole:
                return cache_data
            stored_data = getattr(entry, 'data', None)
            if stored_data is None:
                return '--'
            # do some data handling (currently only for enums)
            if isinstance(cache_data, EpicsData):
                if cache_data.enums and isinstance(stored_data, int):
                    return cache_data.enums[stored_data]
            return stored_data
        elif index.column() == LivePVHeader.LIVE_VALUE:
            live_value = self._get_live_data_field(entry, 'data')
            stored_data = getattr(entry, 'data', None)
            is_close = self.is_close(live_value, stored_data)
            if stored_data and role == QtCore.Qt.BackgroundRole and not is_close:
                return QtGui.QColor('red')
            return str(live_value)
        elif index.column() == LivePVHeader.TIMESTAMP:
            return entry.creation_time.strftime('%Y/%m/%d %H:%M')
        elif index.column() == LivePVHeader.STORED_STATUS:
            if role == CustRoles.DisplayTypeRole:
                return DisplayType.STATUS
            status = getattr(entry, 'status', '--')
            return getattr(status, 'name', status)
        elif index.column() == LivePVHeader.LIVE_STATUS:
            return self._get_live_data_field(entry, 'status')
        elif index.column() == LivePVHeader.STORED_SEVERITY:
            if role == CustRoles.DisplayTypeRole:
                return DisplayType.SEVERITY
            severity = getattr(entry, 'severity', '--')
            return getattr(severity, 'name', severity)
        elif index.column() == LivePVHeader.LIVE_SEVERITY:
            return self._get_live_data_field(entry, 'severity')
        elif index.column() == LivePVHeader.OPEN:
            return "Open"
        elif index.column() == LivePVHeader.REMOVE:
            return "Remove"

        # if nothing is found, return invalid QVariant
        return QtCore.QVariant()

    def setData(self, index: QtCore.QModelIndex, value: Any, role: int) -> bool:
        """Set data"""
        entry = self.entries[index.row()]
        header_col = LivePVHeader(index.column())
        try:
            print("setData", index, value, role)
            setattr(entry, self._header_to_field[header_col], value)
            return True
        except Exception as exc:
            logger.error(f"Failed to set data ({value}) ->"
                         f"({index.row()}, {index.column()}): {exc}")
            return False

    def _get_live_data_field(self, entry: PVEntry, field: str) -> Any:
        """
        Helper to get field from data cache

        Parameters
        ----------
        entry : PVEntry
            The Entry to get data from
        field : str
            The field in the EpicsData to fetch (data, status, severity, timestamp)

        Returns
        -------
        Any
            The data from EpicsData(entry.pv_name).field
        """
        live_data = self.get_cache_data(entry.pv_name)
        if not isinstance(live_data, EpicsData):
            # Data is probably fetching, return as is
            return live_data

        data_field = getattr(live_data, field)
        if isinstance(data_field, Enum):
            return str(getattr(data_field, 'name', data_field))
        elif live_data.enums and field == 'data':
            return live_data.enums[live_data.data]
        else:
            return data_field

    def is_close(self, l_data, r_data) -> bool:
        """
        Returns True if ``l_data`` is close to ``r_data``, False otherwise.
        Intended for use with numeric values.
        """
        try:
            return np.isclose(l_data, r_data)
        except TypeError:
            return False

    def get_cache_data(self, pv_name: str) -> EpicsData:
        """
        Get data from cache if possible.  If missing from cache, add pv_name for
        the polling thread to update.
        """
        data = self._data_cache.get(pv_name, None)

        if data is None:
            if pv_name not in self._data_cache:
                self._data_cache[pv_name] = None

            # TODO: A neat spinny icon maybe?
            return "fetching..."
        else:
            return data


class _PVPollThread(QtCore.QThread):
    """
    Polling thread for LivePVTableModel

    Emits ``data_changed(pv: str)`` when a pv has new data
    Parameters
    ----------
    client : superscore.client.Client
        The client to communicate to PVs through

    data : dict[str, EpicsData]
        Per-PV EpicsData, potentially generated previously.

    poll_period : float
        The poll period in seconds (time between poll events). A zero or
        negative poll rate will indicate single-shot mode.  In "single shot"
        mode, the data is queried exactly once and then the thread exits.

    parent : QWidget, optional, keyword-only
        The parent widget.
    """
    data_ready: ClassVar[QtCore.Signal] = QtCore.Signal()
    data_changed: ClassVar[QtCore.Signal] = QtCore.Signal(str)
    running: bool

    data: Dict[str, EpicsData]
    poll_period: float

    def __init__(
        self,
        client: Client,
        data: Dict[str, EpicsData],
        poll_period: float,
        *,
        parent: Optional[QtWidgets.QWidget] = None
    ):
        super().__init__(parent=parent)
        self.data = data
        self.poll_period = poll_period
        self.client = client
        self.running = False
        self._attrs = set()

    def stop(self) -> None:
        """Stop the polling thread."""
        self.running = False

    def _update_data(self, pv_name):
        """
        Update the internal data cache with new data from EPICS.
        Emit self.data_changed signal if data has changed
        """
        try:
            val = self.client.cl.get(pv_name)
        except Exception as e:
            logger.warning(f'Unable to get data from {pv_name}: {e}')
            return

        # ControlLayer.get may return CommunicationError instead of raising
        if not isinstance(val, Exception) and self.data[pv_name] != val:
            self.data_changed.emit(pv_name)
            self.data[pv_name] = val

    def run(self):
        """The thread polling loop."""
        self.running = True

        self.data_ready.emit()

        while self.running:
            t0 = time.monotonic()
            for pv_name in self.data:
                self._update_data(pv_name)
                if not self.running:
                    break
                time.sleep(0)

            if self.poll_period <= 0.0:
                # A zero or below means "single shot" updates.
                break

            elapsed = time.monotonic() - t0
            time.sleep(max((0, self.poll_period - elapsed)))


class BaseDataTableView(QtWidgets.QTableView):
    """
    Base TableView for holding and manipulating an entry / list of entries
    TODO: signature docs
    """
    # signal indicating the contained has been updated
    data_updated: ClassVar[QtCore.Signal] = QtCore.Signal()
    _model: Optional[Union[LivePVTableModel, NestableTableModel]] = None
    _model_cls: Union[LivePVTableModel, NestableTableModel] = LivePVTableModel
    open_column: int = 0
    remove_column: int = 0

    def __init__(
        self,
        *args,
        client: Optional[Client] = None,
        data: Optional[Union[Entry, List[Entry]]] = None,
        open_page_slot: Optional[Callable] = None,
        **kwargs,
    ) -> None:
        """need to set open_column, close_column in subclass"""
        super().__init__(*args, **kwargs)
        self.data = data
        self._client = client
        self.open_page_slot = open_page_slot
        self.sub_entries = []

        # only these for now, may need an update later
        self.setup_ui()

    def setup_ui(self):
        """initialize ui elements for this table"""
        # set delegates
        self.open_delegate = ButtonDelegate(button_text='open details')
        self.setItemDelegateForColumn(self.open_column, self.open_delegate)
        self.open_delegate.clicked.connect(self.open_row_details)

        self.remove_delegate = ButtonDelegate(button_text='remove')
        self.setItemDelegateForColumn(self.remove_column, self.remove_delegate)
        self.remove_delegate.clicked.connect(self.remove_row)

    def open_row_details(self, index: QtCore.QModelIndex) -> None:
        entry = self._model.entries[index.row()]
        self.open_page_slot(entry)

    def remove_row(self, index: QtCore.QModelIndex) -> None:
        entry = self._model.entries[index.row()]
        self._model.remove_row(index.row())

        if isinstance(self.data, list):
            self.data.remove(entry)
        elif isinstance(self.data, Nestable):
            self.data.children.remove(entry)
        # edit data held by widget
        self.data_updated.emit()

    def set_data(self, data: Any):
        """Set the data for this view, re-setup ui"""
        if not isinstance(data, (list, Nestable)):
            raise ValueError(
                f"Attempted to set an incompatable data type ({type(data)})"
            )
        self.data = data
        self.gather_sub_entries()

        if self.client is None:
            logger.debug("Client not yet set, cannot initialize model")
            return

        if self._model is None:
            self._model = self._model_cls(
                client=self.client,
                entries=self.sub_entries
            )
            self.setModel(self._model)
        else:
            self._model.set_entries(self.sub_entries)

        self.data_updated.emit()

    def gather_sub_entries(self):
        raise NotImplementedError

    @property
    def client(self):
        return self._client

    @client.setter
    def client(self, client: Client):
        self._set_client(client)

    def _set_client(self, client: Client):
        if client is self._client:
            return

        if not isinstance(client, Client):
            raise ValueError("Provided client is not a superscore Client")

        self._client = client


class LivePVTableView(BaseDataTableView):
    """
    table widget for LivePVTableModel.  Meant to provide a standard, easy-to-use
    interface for this table model, with common configuration options exposed

    compatible with list of entries or full entry
        - updates entry when changes made
        - maintains order for rebuilding of parent collections
    Configures delegates, ignoring open page slot if provided
    Column manipulation
        - show/hide
        - re-order
    flattening of base data
        - handling of readbacks associated with base entries?
        - handling of nested nestables
    ediable stored fields if desired, updating entry
    """
    # TODO: add config args / methods: {show/hide}, poll period, column order?
    _model: Optional[LivePVTableModel]

    def __init__(self, *args, **kwargs):
        self._model_cls = LivePVTableModel
        self.open_column = LivePVHeader.OPEN
        self.remove_column = LivePVHeader.REMOVE
        super().__init__(*args, **kwargs)

        self.value_delegate = ValueDelegate()
        for col in [LivePVHeader.PV_NAME, LivePVHeader.STORED_VALUE,
                    LivePVHeader.STORED_STATUS, LivePVHeader.STORED_SEVERITY]:
            self.setItemDelegateForColumn(col, self.value_delegate)

    def gather_sub_entries(self):
        if isinstance(self.data, UUID):
            self.data = self.client.backend.get_entry(self.data)

        # TODO: gather and fill entries where necessary
        if isinstance(self.data, Nestable):
            # gather sub_nestables
            self.sub_entries = [child for child in self.data.children
                                if not isinstance(child, Nestable)]

            for i, sub_nest in enumerate(self.sub_entries):
                if isinstance(sub_nest, UUID):
                    new_entry = self._client.backend.get_entry(sub_nest)
                    self.sub_entries[i] = new_entry

        if isinstance(self.data, (Parameter, Setpoint, Readback)):
            self.sub_entries = [self.data]

    @BaseDataTableView.client.setter
    def client(self, client: Optional[Client]):
        super()._set_client(client)
        # reset model poll thread
        if self._model is not None:
            self._model.stop_polling()
            self._model.client = self._client
            self._model.start_polling()


class NestableTableModel(BaseTableEntryModel):
    # Shows simplified details (created time, description, # pvs, # child colls)
    # Open details delegate
    headers: List[str] = ['Name', 'Description', 'Created', 'Open', 'Remove']

    def __init__(
        self,
        *args,
        client: Optional[Client] = None,
        entries: Optional[List[Union[Snapshot, Collection]]] = None,
        open_page_slot: Optional[Callable] = None,
        **kwargs
    ) -> None:
        self.open_page_slot = open_page_slot
        self._editable_cols = {ind: False for ind
                               in range(len(self.headers))}
        super().__init__(*args, entries=entries, **kwargs)

    def data(self, index: QtCore.QModelIndex, role: int) -> Any:
        """
        Returns the data stored under the given role for the item
        referred to by the index.

        Parameters
        ----------
        index : QtCore.QModelIndex
            An index referring to a cell of the TableView
        role : int
            The requested data role.

        Returns
        -------
        Any
            the requested data
        """
        entry: Entry = self.entries[index.row()]

        if role != QtCore.Qt.DisplayRole:
            # table is read only
            return QtCore.QVariant()

        if index.column() == 0:  # name column
            if role == QtCore.Qt.DecorationRole:
                return self.icon(entry)
            name_text = getattr(entry, 'title')
            return name_text
        elif index.column() == 1:  # description
            return getattr(entry, 'description')
        elif index.column() == 2:  # Created
            return entry.creation_time.strftime('%Y/%m/%d %H:%M')
        elif index.column() == 3:  # Open Delegate
            return "Open"
        elif index.column() == 4:  # Remove Delegate
            return "Remove"


class NestableTableView(BaseDataTableView):
    def __init__(self, *args, **kwargs):
        self._model_cls = NestableTableModel
        self.open_column = 3
        self.remove_column = 4
        super().__init__(*args, **kwargs)

    def gather_sub_entries(self):
        if isinstance(self.data, UUID):
            self.data = self.client.backend.get_entry(self.data)
        # TODO: gather and fill entries where necessary
        if isinstance(self.data, Nestable):
            # gather sub_nestables
            self.sub_entries = [child for child in self.data.children
                                if isinstance(child, Nestable)]

            for i, sub_nest in enumerate(self.sub_entries):
                if isinstance(sub_nest, UUID):
                    new_entry = self._client.backend.get_entry(sub_nest)
                    self.sub_entries[i] = new_entry


class ButtonDelegate(QtWidgets.QStyledItemDelegate):
    clicked = QtCore.Signal(QtCore.QModelIndex)

    def __init__(self, *args, button_text: str = '', **kwargs):
        self.button_text = button_text
        super().__init__(*args, **kwargs)

    def createEditor(
        self,
        parent: QtWidgets.QWidget,
        option,
        index: QtCore.QModelIndex
    ) -> QtWidgets.QWidget:
        button = QtWidgets.QPushButton(self.button_text, parent)
        button.clicked.connect(
            lambda _, index=index: self.clicked.emit(index)
        )
        return button

    def updateEditorGeometry(
        self,
        editor: QtWidgets.QWidget,
        option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex
    ) -> None:
        return editor.setGeometry(option.rect)


class ValueDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def createEditor(
        self,
        parent: QtWidgets.QWidget,
        option,
        index: QtCore.QModelIndex
    ) -> QtWidgets.QWidget:
        dtype: DisplayType = index.model().data(
            index, role=CustRoles.DisplayTypeRole
        )
        data_val = index.model().data(index, role=QtCore.Qt.DisplayRole)
        if dtype == DisplayType.PV_NAME:
            widget = QtWidgets.QLineEdit(data_val, parent)
        elif dtype == DisplayType.STATUS:
            widget = QtWidgets.QComboBox(parent)
            widget.addItems([sev.name for sev in Severity])
        elif dtype == DisplayType.STATUS:
            widget = QtWidgets.QComboBox(parent)
            widget.addItems([sta.name for sta in Status])
        elif dtype == DisplayType.EPICS_DATA:
            # need to fetch data for this PV, not stored data
            data_val: EpicsData = index.model().data(
                index, role=CustRoles.EpicsDataRole
            )
            if isinstance(data_val.data, str):
                widget = QtWidgets.QLineEdit(data_val.data, parent)
            elif data_val.enums:  # Catch enums before numerics, enums are ints
                widget = QtWidgets.QComboBox(parent)
                widget.addItems(data_val.enums)
                widget.setCurrentIndex(data_val.data)
            elif isinstance(data_val.data, int):
                widget = QtWidgets.QSpinBox(parent)
                widget.setValue(data_val.data)
                widget.setMaximum(data_val.upper_ctrl_limit)
                widget.setMinimum(data_val.lower_ctrl_limit)
            elif isinstance(data_val.data, float):
                widget = QtWidgets.QDoubleSpinBox(parent)
                widget.setValue(data_val.data)
                widget.setMaximum(data_val.upper_ctrl_limit)
                widget.setMinimum(data_val.lower_ctrl_limit)
                widget.setDecimals(data_val.precision)
        else:
            logger.debug(f"datatype ({dtype}) incompatible with supported edit "
                         f"widgets: ({data_val})")
            return
        return widget

    def setModelData(
        self,
        editor: QtWidgets.QWidget,
        model: QtCore.QAbstractItemModel,
        index: QtCore.QModelIndex
    ) -> None:
        if isinstance(editor, QtWidgets.QAbstractSpinBox):
            val = editor.value()
        elif isinstance(editor, QtWidgets.QLineEdit):
            val = editor.text()
        elif isinstance(editor, QtWidgets.QComboBox):
            val = editor.currentIndex()
        else:
            return
        model.setData(index, val, QtCore.Qt.EditRole)

    def updateEditorGeometry(
        self,
        editor: QtWidgets.QWidget,
        option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex
    ) -> None:
        return editor.setGeometry(option.rect)
