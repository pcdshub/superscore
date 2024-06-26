"""
Qt tree model and item classes for visualizing Entry dataclasses
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar, Generator, List, Optional
from weakref import WeakValueDictionary

from PyQt5.QtCore import Qt
from qtpy import QtCore

from superscore.client import Client
from superscore.model import Entry, Nestable, Root
from superscore.qt_helpers import QDataclassBridge

logger = logging.getLogger(__name__)


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
                return getattr(self._data, 'pv_name')
        elif column == 1:
            return getattr(self._data, 'description', 'fart')

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

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
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
        if role != Qt.DisplayRole:
            return

        if orientation == Qt.Horizontal:
            return self.headers[section]

    def index(
        self,
        row: int,
        column: int,
        parent: QtCore.QModelIndex = None
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
        Returns the parent of the given model item.

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
        # special handling for status info
        if index.column() == 1:
            if role == Qt.DisplayRole:
                return item.data(1)
            if role == Qt.TextAlignmentRole:
                return Qt.AlignCenter

        if role == Qt.ToolTipRole:
            return item.tooltip()
        if role == Qt.DisplayRole:
            return item.data(index.column())

        if role == Qt.UserRole:
            return item

        return None
