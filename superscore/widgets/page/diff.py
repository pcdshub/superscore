from enum import Flag
from functools import partial
from typing import Any, Dict, Optional, Set
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
                                      NestableTableModel, NestableTableView,
                                      RootTree, RootTreeView)

DIFF_COLOR_MAP = {
    DiffType.DELETED: QtGui.QColor(255, 0, 0, alpha=100),
    DiffType.MODIFIED: QtGui.QColor(255, 255, 0, alpha=100),
    DiffType.ADDED: QtGui.QColor(0, 255, 0, alpha=100),
    None: None,
}


class DiffModelMixin:
    """
    Tree model that highlights items that have been modified.
    Reads an `EntryDiff` and assigns background colors based on modification type
    - Red: item removed in diff
    - Yellow: item modified in diff
    - Green: item added in diff
    """

    _diff: EntryDiff
    _linked_uuids: Set[UUID]
    _index_to_diff_type_cache: Dict[QtCore.QModelIndex, DiffType]

    def __init__(self, *args, diff: Optional[EntryDiff] = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._diff = diff
        # a cache that stores the background color, since entries may be lazily
        # loaded on demand.  To be cleared if data or diff are changed
        self._index_to_diff_type_cache = {}
        self._linked_uuids = set()

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

        # show entries as modified if detected on left-side
        if self._get_entry_from_index(index).uuid in self._linked_uuids:
            return DIFF_COLOR_MAP[DiffType.MODIFIED]

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

    def _get_difftype_for_index(self, index: QtCore.QModelIndex) -> Optional[DiffType]:
        entry: Entry = self._get_entry_from_index(index)
        for diff_item in self._diff.diffs:
            # deleted or added, entry is itself the changed item
            if entry in (diff_item.original_value, diff_item.new_value):
                return diff_item.type

            # modified, entry is in the path (Match happens on left/original side)
            if entry in (segment[0] for segment in diff_item.path):
                # uuids are almost always changed, if so add them to let the
                # other tree know
                self._linked_uuids.add(entry.uuid)
                for di in self._diff.diffs:
                    if di.original_value == entry.uuid:
                        self._linked_uuids.add(di.new_value)

                return diff_item.type


class DiffPVTableModel(DiffModelMixin, LivePVTableModel):

    def _get_difftype_for_index(self, index: QtCore.QModelIndex) -> Optional[DiffType]:
        entry: Entry = self._get_entry_from_index(index)
        col = index.column()
        col_header = self.header_enum(col)

        # field not in a settable header ... timestamp?
        if col_header not in self._header_to_field:
            return

        field_name = self._header_to_field[col_header]
        for diff_item in self._diff.diffs:
            if (entry, field_name) in diff_item.path:
                return diff_item.type


class DiffNestableTableModel(DiffModelMixin, NestableTableModel):
    def _get_difftype_for_index(self, index: QtCore.QModelIndex) -> Optional[DiffType]:
        return DiffType.MODIFIED


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
        self._linked_uuids: Set[UUID] = set()

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
            pv_view: LivePVTableView = self.widget_map[side]['pv']
            pv_view.open_page_slot = self.open_page_slot
            pv_view.client = self.client
            for i in [LivePVHeader.LIVE_VALUE, LivePVHeader.LIVE_SEVERITY,
                      LivePVHeader.LIVE_STATUS]:
                pv_view.setColumnHidden(i, True)

            nest_view: NestableTableView = self.widget_map[side]['nest']
            nest_view.client = self.client
            pv_view.open_page_slot = self.open_page_slot

        self.set_entry(self.l_entry, Side.LEFT)
        self.set_entry(self.r_entry, Side.RIGHT)

        self.calculate_diff()

    def sync_splitter(self, pos: int, index: int, side: Side):
        sizes = self.widget_map[~side]['splitter'].sizes()
        self.widget_map[side]['splitter'].setSizes(sizes)

    def set_entry(self, entry: Entry, side: Side):
        """Initialize the widgets for the ``side`` with ``entry``"""
        tree_view: RootTreeView = self.widget_map[side]['tree']
        tree_view.setModel(
            DiffRootTree(base_entry=entry, client=self.client)
        )

        pv_view: LivePVTableView = self.widget_map[side]['pv']
        pv_view._model_cls = DiffPVTableModel
        nest_view: NestableTableView = self.widget_map[side]['nest']
        nest_view._model_cls = DiffNestableTableModel
        self.set_table_entries(entry, side)

        # clear modified uuids
        self.modified_uuids = set()

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
        for side in Side:
            for view in ["tree", "pv", "nest"]:
                model: DiffModelMixin = self.widget_map[side][view].model()
                model._diff = diff
                model._linked_uuids = self._linked_uuids

    def closeEvent(self, a0: QCloseEvent) -> None:
        for side in Side:
            self.widget_map[side]['pv'].close()
        return super().closeEvent(a0)
