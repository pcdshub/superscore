import logging
from enum import Flag
from functools import partial
from typing import Any, Dict, Optional
from uuid import UUID

from PyQt5.QtGui import QCloseEvent
from qtpy import QtCore, QtGui, QtWidgets

from superscore.client import Client
from superscore.compare import DiffType, EntryDiff
from superscore.model import Entry
from superscore.type_hints import OpenPageSlot
from superscore.widgets.core import Display
from superscore.widgets.views import (EntryItem, LivePVHeader,
                                      LivePVTableModel, LivePVTableView,
                                      NestableHeader, NestableTableModel,
                                      NestableTableView, RootTree,
                                      RootTreeView)

logger = logging.getLogger(__name__)


DIFF_COLOR_MAP = {
    DiffType.DELETED: QtGui.QColor(255, 0, 0, alpha=100),
    DiffType.MODIFIED: QtGui.QColor(255, 255, 0, alpha=100),
    DiffType.ADDED: QtGui.QColor(0, 255, 0, alpha=100),
    None: None,  # the no modification case, do not change background color
}


class BiDict(dict):
    """
    Bi-directional mapping dictionary.
    Every key-value pair can only appear once in each dict (forward and inverse)
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.inverse = {}

    def __setitem__(self, key, value):
        # setting in the standard direction to a new value
        # must remove the inverse oldvalue-key pair
        if key in self:
            del self.inverse[self[key]]
        super().__setitem__(key, value)
        self.inverse[value] = key

    def __delitem__(self, key):
        if self[key] in self.inverse:
            del self.inverse[self[key]]
        super().__delitem__(key)

    def __getitem__(self, key: Any) -> Any:
        try:
            return super().__getitem__(key)
        except KeyError:
            return self.inverse[key]

    def __contains__(self, key: object) -> bool:
        return (super().__contains__(key) or self.inverse.__contains__(key))


class DiffModelMixin:
    """
    QAbstractItemModel Mixin that highlights items that have been modified.
    This must be mixed in with a ``QtCore.QAbstractItemModel``

    Reads an `EntryDiff` and assigns background colors based on modification type
    - Red: item removed in diff
    - Yellow: item modified in diff
    - Green: item added in diff

    Caches color assignments, and does not re-calculate / clear the cache until
    new data is assigned to the model
    """

    _diff: EntryDiff
    _linked_uuids: Dict[UUID, UUID]
    _index_to_diff_type_cache: Dict[QtCore.QModelIndex, DiffType]

    def __init__(
        self,
        *args,
        diff: Optional[EntryDiff] = None,
        linked_uuid_map: Optional[BiDict] = None,
        **kwargs
    ) -> None:
        if not isinstance(self, QtCore.QAbstractItemModel):
            raise TypeError("DiffModelMixin (and its subclasses) must be mixed"
                            "in with a QtCore.QAbstractItemModel.  "
                            f"MRO: ({list(c.__name__ for c in type(self).__mro__)})")
        super().__init__(*args, **kwargs)
        self._diff = diff
        # a cache that stores the background color, since entries may be lazily
        # loaded on demand.  To be cleared if data or diff are changed
        self._index_to_diff_type_cache = {}
        # to be set by
        self._linked_uuids = linked_uuid_map

        self.layoutChanged.connect(self._clear_diff_cache)

    def _clear_diff_cache(self) -> None:
        self._index_to_diff_type_cache = {}

    def data(self, index: QtCore.QModelIndex, role: int) -> Any:
        """
        If asked for a background color, get and return it.  Else fall back
        to functionality defined in mixed in class.
        """
        if role == QtCore.Qt.BackgroundColorRole:
            color = self.get_background_color(index)
            return color

        return super().data(index, role)

    def get_background_color(self, index: QtCore.QModelIndex) -> Optional[QtGui.QColor]:
        """
        Get the background color for the entry at ``index`` based on the stored
        EntryDiff, if one has been set

        Parameters
        ----------
        index : QtCore.QModelIndex
            the model index to get the diff background color for

        Returns
        -------
        Optional[QtGui.QColor]
            the corresponding color, None if no diff found
        """
        # do nothing if no diff is setup
        if not self._diff:
            return

        if index in self._index_to_diff_type_cache:
            return DIFF_COLOR_MAP[self._index_to_diff_type_cache[index]]

        # find diffs and assign a proper color

        diff_type = self._get_difftype_for_index(index)
        if diff_type:  # Only stash actual codes, otherwise will remember None
            self._index_to_diff_type_cache[index] = diff_type

        return DIFF_COLOR_MAP[diff_type]

    def _get_entry_from_index(self, index: QtCore.QModelIndex) -> Entry:
        """
        Get the Entry from the provided Index.  Currently covers two model
        index types:
        - TreeModel (index.internalPointer() -> EntryItem)
        - BaseTableEntryModel (self.entries[index.row()] -> Entry)

        Parameters
        ----------
        index : QtCore.QModelIndex
            the requested model index

        Returns
        -------
        Entry
            The entry corresponding to ``index``
        """
        ipointer = index.internalPointer()

        if isinstance(ipointer, EntryItem):
            return ipointer._data
        else:  # table view case
            return self.entries[index.row()]

    def _get_difftype_for_index(self, index: QtCore.QModelIndex) -> Optional[DiffType]:
        raise NotImplementedError


class DiffRootTree(DiffModelMixin, RootTree):
    """A tree model with diff highlighting specialized for RootTree"""

    def _get_difftype_for_index(
        self,
        index: QtCore.QModelIndex
    ) -> Optional[DiffType]:
        entry: Entry = self._get_entry_from_index(index)

        # show entries as modified if detected on left-side
        if entry.uuid in self._linked_uuids:
            return DiffType.MODIFIED

        for diff_item in self._diff.diffs:
            # deleted or added, entry is itself the changed item
            if entry in (diff_item.original_value, diff_item.new_value):
                return diff_item.type


class DiffTableModel(DiffModelMixin):
    """
    A table model with diff highlighting specialized for ``BaseTableEntryModel``
    """
    # Assumes use as mixin for BaseTableEntryModel
    def _get_difftype_for_index(
        self,
        index: QtCore.QModelIndex
    ) -> Optional[DiffType]:
        col = index.column()
        col_header = self.header_enum(col)

        # field not in a settable header ... timestamp?
        if col_header not in self._header_to_field:
            return

        entry = self._get_entry_from_index(index)
        field_name = self._header_to_field[col_header]
        for diff_item in self._diff.diffs:
            # handle type changes
            if entry in (diff_item.original_value, diff_item.new_value):
                return diff_item.type

            for chain_obj, chain_access in diff_item.path:
                if (
                    isinstance(chain_obj, Entry)
                    and (chain_obj.uuid in self._linked_uuids)
                    and (entry.uuid is chain_obj.uuid
                         or entry.uuid is self._linked_uuids[chain_obj.uuid])
                    and (chain_access == field_name)
                ):
                    diff_type = diff_item.type
                    # we need to check the directionality for added/deleted
                    if diff_type is DiffType.ADDED and (chain_obj.uuid == entry.uuid):
                        return
                    elif diff_type is DiffType.DELETED and (chain_obj.uuid != entry.uuid):
                        return
                    else:
                        return diff_type


class DiffPVTableModel(DiffTableModel, LivePVTableModel):
    pass


class DiffNestableTableModel(DiffTableModel, NestableTableModel):
    pass


class Side(Flag):
    """Simple right/left side enum, where inversion gives the other side"""
    LEFT = True
    RIGHT = False


class DiffPage(Display, QtWidgets.QWidget):
    """
    Diff View Page.  Compares two ``Entry`` objects, attempting to highlight
    differences where appropriate

    Features:
    - Synchronized splitters
    - Subclasses of common views augmented with diff highlighting
    - No editing (so no data widget needed for bridge)
        - defers editing to details

    To use, either:
    - supply the two entries on page creation
    - set the entries with DiffPage.set_entry()

    TODO:
    - Buttons for setting entries inside page
    - Button for refreshing entry data (new grab from client)
    - Top level Summary of Entries and possibly their differences
    """
    filename = "diff_page.ui"

    horiz_splitter: QtWidgets.QSplitter  # main l_entry/r_entry splitter

    l_vert_splitter: QtWidgets.QSplitter
    l_tree_view: RootTreeView
    l_pv_table_view: LivePVTableView
    l_nest_table_view: NestableTableView

    r_vert_splitter: QtWidgets.QSplitter
    r_tree_view: RootTreeView
    r_pv_table_view: LivePVTableView
    r_nest_table_view: NestableTableView

    meta_placeholder: QtWidgets.QWidget  # TODO: Clean up or make useful

    def __init__(
        self,
        *args,
        client: Client,
        open_page_slot: Optional[OpenPageSlot] = None,
        l_entry: Optional[Entry] = None,
        r_entry: Optional[Entry] = None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.client = client
        self.l_entry = l_entry
        self.r_entry = r_entry
        self.open_page_slot = open_page_slot
        self._linked_uuids: Dict[UUID, UUID] = BiDict()

        self.widget_map = {
            Side.LEFT: {
                'tree': self.l_tree_view,
                'pv': self.l_pv_table_view,
                'nest': self.l_nest_table_view,
                'splitter': self.l_vert_splitter
            },
            Side.RIGHT: {
                'tree': self.r_tree_view,
                'pv': self.r_pv_table_view,
                'nest': self.r_nest_table_view,
                'splitter': self.r_vert_splitter
            }
        }
        self.setup_ui()

    def setup_ui(self):
        """Initial ui setup.  Wire up slots and initialize models"""
        # Synchronize vertical splitters
        self.l_vert_splitter.splitterMoved.connect(partial(
            self.sync_splitter, side=Side.RIGHT
        ))
        self.r_vert_splitter.splitterMoved.connect(partial(
            self.sync_splitter, side=Side.LEFT
        ))

        # initialize trees, tables, etc
        for side in Side:
            tree_view: RootTreeView = self.widget_map[side]['tree']
            tree_view._model_cls = DiffRootTree
            tree_view.client = self.client

            pv_view: LivePVTableView = self.widget_map[side]['pv']
            pv_view._model_cls = DiffPVTableModel
            pv_view.open_page_slot = self.open_page_slot
            pv_view.client = self.client

            nest_view: NestableTableView = self.widget_map[side]['nest']
            nest_view._model_cls = DiffNestableTableModel
            nest_view.client = self.client
            nest_view.open_page_slot = self.open_page_slot

        self.set_entry(self.l_entry, Side.LEFT)
        self.set_entry(self.r_entry, Side.RIGHT)

        # Need to set visibility after model is configured
        for side in Side:
            pv_view: LivePVTableView = self.widget_map[side]['pv']
            for i in [LivePVHeader.LIVE_VALUE, LivePVHeader.LIVE_SEVERITY,
                      LivePVHeader.LIVE_STATUS, LivePVHeader.REMOVE]:
                pv_view.setColumnHidden(i, True)

            nest_view: NestableTableView = self.widget_map[side]['nest']
            nest_view.setColumnHidden(NestableHeader.REMOVE, True)

    def sync_splitter(self, pos: int, index: int, side: Side):
        """
        Slot for QSplitter.splitterMoved.  ``side`` must be supplied via partial
        """
        sizes = self.widget_map[~side]['splitter'].sizes()
        self.widget_map[side]['splitter'].setSizes(sizes)

    def set_entry(self, entry: Entry, side: Side):
        """
        Set entry data for all widgets on ``side`` to ``entry``.

        Parameters
        ----------
        entry : Entry
            data to be set
        side : Side
            side to set data on
        """
        tree_view: RootTreeView = self.widget_map[side]["tree"]
        tree_view.set_data(entry)
        self.set_table_entries(entry, side)

        # re-calculate diffs
        self.calculate_diff()

    def set_table_entries(self, entry: Entry, side: Side):
        """
        Set the ``entry`` to the PV and Nestable table view on ``side``

        Parameters
        ----------
        entry : Entry
            data to be set
        side : Side
            side to set data on
        """
        pv_view: LivePVTableView = self.widget_map[side]['pv']
        nest_view: NestableTableView = self.widget_map[side]['nest']
        pv_view.set_data(entry)
        nest_view.set_data(entry)

    def calculate_diff(self):
        """Calculate the diff between the stored left and right entries"""
        # get diff from client method
        # refresh tables to show highlighting
        diff = self.client.compare(self.l_entry, self.r_entry)
        self._diff = diff
        self._linked_uuids = BiDict()

        # uuids are almost always changed, if so add them to let the
        for di in self._diff.diffs:
            if isinstance(di.original_value, UUID) and isinstance(di.new_value, UUID):
                self._linked_uuids[di.original_value] = di.new_value

        for side in Side:
            for view in ["tree", "pv", "nest"]:
                model: DiffModelMixin = self.widget_map[side][view].model()
                if model is None:
                    logger.debug(f"No model set for {side.name} {view} view,"
                                 "skipping diff setting step")
                    continue
                model._diff = diff
                model._linked_uuids = self._linked_uuids

    def closeEvent(self, a0: QCloseEvent) -> None:
        for side in Side:
            self.widget_map[side]['pv'].close()
        return super().closeEvent(a0)
