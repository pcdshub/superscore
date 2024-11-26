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
    None: None,
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
        if key in self:
            self.inverse[self[key]].remove(key)
        super().__setitem__(key, value)

    def __delitem__(self, key):
        if self[key] in self.inverse and not self.inverse[self[key]]:
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
    Tree model that highlights items that have been modified.
    Reads an `EntryDiff` and assigns background colors based on modification type
    - Red: item removed in diff
    - Yellow: item modified in diff
    - Green: item added in diff
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
        super().__init__(*args, **kwargs)
        self._diff = diff
        # a cache that stores the background color, since entries may be lazily
        # loaded on demand.  To be cleared if data or diff are changed
        self._index_to_diff_type_cache = {}
        # to be set by
        self._linked_uuids = linked_uuid_map

    def data(self, index: QtCore.QModelIndex, role: int) -> Any:
        if role == QtCore.Qt.BackgroundColorRole:
            color = self.get_background_color(index)
            return color

        return super().data(index, role)

    def get_background_color(self, index: QtCore.QModelIndex) -> Optional[QtGui.QColor]:
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
        ipointer = index.internalPointer()

        if isinstance(ipointer, EntryItem):
            return ipointer._data
        else:  # table view case
            return self.entries[index.row()]

    def _get_difftype_for_index(self, index: QtCore.QModelIndex) -> Optional[DiffType]:
        raise NotImplementedError


class DiffRootTree(DiffModelMixin, RootTree):

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
    LEFT = True
    RIGHT = False


class DiffPage(Display, QtWidgets.QWidget):
    """
    Diff Page.  Many splitters, existing views + highlighting
    No editing (so no data widget needed for bridge)
        - defers editing to details

    Refresh behavior?
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
        # Synchronize splitters
        self.l_vert_splitter.splitterMoved.connect(partial(
            self.sync_splitter, side=Side.RIGHT
        ))
        self.r_vert_splitter.splitterMoved.connect(partial(
            self.sync_splitter, side=Side.LEFT
        ))

        # initialize trees, tables, etc
        for side in Side:
            print(f'initializing {side}')
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

        self.calculate_diff()

    def sync_splitter(self, pos: int, index: int, side: Side):
        sizes = self.widget_map[~side]['splitter'].sizes()
        self.widget_map[side]['splitter'].setSizes(sizes)

    def set_entry(self, entry: Entry, side: Side):
        """set entry data for all widgets on ``side`` to ``entry``"""
        tree_view: RootTreeView = self.widget_map[side]["tree"]
        tree_view.set_data(entry)
        self.set_table_entries(entry, side)

        # re-calculate diffs
        self.calculate_diff()

    def set_table_entries(self, entry: Entry, side: Side):
        """Set the entry to view in table, use diff models for highlighting"""
        pv_view: LivePVTableView = self.widget_map[side]['pv']
        nest_view: NestableTableView = self.widget_map[side]['nest']
        pv_view.set_data(entry)
        nest_view.set_data(entry)

    def calculate_diff(self):
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
