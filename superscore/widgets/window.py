"""
Top-level window widget that contains other widgets
"""
from __future__ import annotations

import logging
from functools import partial
from typing import ClassVar, Optional
from uuid import UUID

import qtawesome as qta
from pcdsutils.qt.callbacks import WeakPartialMethodSlot
from qtpy import QtCore, QtWidgets
from qtpy.QtGui import QCloseEvent

from superscore.client import CallbackType, Client
from superscore.model import Entry, Snapshot
from superscore.widgets import ICON_MAP
from superscore.widgets.core import DataWidget, Display, QtSingleton
from superscore.widgets.page import PAGE_MAP
from superscore.widgets.page.collection_builder import CollectionBuilderPage
from superscore.widgets.page.diff import DiffPage
from superscore.widgets.page.restore import RestorePage
from superscore.widgets.page.search import SearchPage
from superscore.widgets.thread_helpers import get_qthread_cache
from superscore.widgets.views import DiffDispatcher, RootTreeView

logger = logging.getLogger(__name__)


class Window(Display, QtWidgets.QMainWindow, metaclass=QtSingleton):
    """Main superscore window"""

    filename = 'main_window.ui'

    tree_view: RootTreeView
    tab_widget: QtWidgets.QTabWidget

    action_new_coll: QtWidgets.QAction

    entry_saved: ClassVar[QtCore.Signal] = QtCore.Signal(UUID)
    entry_deleted: ClassVar[QtCore.Signal] = QtCore.Signal(UUID)
    entry_updated: ClassVar[QtCore.Signal] = QtCore.Signal(UUID)

    # Diff dispatcher singleton, used to notify when diffs are ready
    diff_dispatcher: DiffDispatcher = DiffDispatcher()
    client: Client

    def __init__(self, *args, client: Optional[Client] = None, **kwargs):
        super().__init__(*args, **kwargs)
        if client:
            self.client = client
        else:
            self.client = Client.from_config()

        self._partial_slots = []

        self.setup_ui()
        self.open_search_page()

    def setup_ui(self) -> None:
        tab_bar = self.tab_widget.tabBar()
        # always use scroll area and never truncate file names
        tab_bar.setUsesScrollButtons(True)
        tab_bar.setElideMode(QtCore.Qt.ElideNone)
        self.tab_widget.tabCloseRequested.connect(self.remove_tab)

        # setup tree view
        self.tree_view.client = self.client
        self.tree_view.set_data(self.client.backend.root)
        self.entry_updated.connect(self.tree_view.update_uuid)
        self.entry_saved.connect(self.tree_view.update_uuid)
        # override context menu
        self.tree_view.create_context_menu = self._window_context_menu

        # setup actions
        self.action_new_coll.triggered.connect(self.open_collection_builder)

        # open diff page
        self.diff_dispatcher.comparison_ready.connect(self.open_diff_page)

        # subscribe global entry signals to client.  Other widgets can then sub
        # to these signals to keep signaling within Qt
        self.client.register_callback(CallbackType.ENTRY_SAVED, self.entry_saved.emit)
        self.client.register_callback(CallbackType.ENTRY_DELETED, self.entry_deleted.emit)
        self.client.register_callback(CallbackType.ENTRY_UPDATED, self.entry_updated.emit)

    def remove_tab(self, tab_index: int) -> None:
        """Remove the requested tab and delete the widget"""
        widget = self.tab_widget.widget(tab_index)
        widget.close()
        widget.deleteLater()
        self.tab_widget.removeTab(tab_index)

    def _update_tab_title(self, tab_index: int) -> None:
        """Update a DataWidget tab title.  Assumes widget._title exists"""
        # TODO: fix for entry pages to have ._title
        title_text = self.tab_widget.widget(tab_index)._title
        self.tab_widget.setTabText(tab_index, title_text)

    def open_collection_builder(self):
        """open collection builder page"""
        page = CollectionBuilderPage(client=self.client)
        self.tab_widget.addTab(page, 'new collection')
        self.tab_widget.setCurrentWidget(page)
        # This will be left dangling after a collection is saved, since bridges
        # will be refreshed
        update_slot = WeakPartialMethodSlot(
            page.bridge.title, page.bridge.title.updated,
            self._update_tab_title,
            tab_index=self.tab_widget.indexOf(page),
        )
        self._partial_slots.append(update_slot)

    def open_page(self, entry: Entry) -> DataWidget:
        """
        Open a page for ``entry`` in a new tab.

        Parameters
        ----------
        entry : Entry
            Entry subclass to open a new page for

        Returns
        -------
        DataWidget
            Created widget, for cross references
        """
        logger.debug(f'attempting to open {entry}')
        if not isinstance(entry, Entry):
            logger.debug('Could not open page for non-Entry dataclass')
            return

        if type(entry) not in PAGE_MAP:
            logger.debug(f'No page corresponding to {type(entry).__name__}')

        try:
            page = PAGE_MAP[type(entry)]
        except KeyError:
            raise TypeError(f'No page widget for {type(entry)}, cannot open in tab')

        page_widget = page(data=entry, client=self.client,
                           editable=self.client.is_editable(entry))
        icon = qta.icon(ICON_MAP[type(entry)])
        tab_name = getattr(
            entry, 'title', getattr(entry, 'pv_name', f'<{type(entry).__name__}>')
        )
        idx = self.tab_widget.addTab(page_widget, icon, tab_name)
        self.tab_widget.setCurrentIndex(idx)

        return page_widget

    def open_index(self, index: QtCore.QModelIndex) -> None:
        entry: Entry = index.internalPointer()._data
        self.open_page(entry)

    def open_search_page(self) -> None:
        page = SearchPage(client=self.client)
        index = self.tab_widget.addTab(page, 'search')
        self.tab_widget.setCurrentIndex(index)

    def open_restore_page(self, snapshot: Snapshot) -> None:
        page = RestorePage(data=snapshot, client=self.client)
        index = self.tab_widget.addTab(page, snapshot.title)
        self.tab_widget.setCurrentIndex(index)

    def open_diff_page(self) -> None:
        page = DiffPage(
            client=self.client,
            l_entry=self.diff_dispatcher.l_entry,
            r_entry=self.diff_dispatcher.r_entry,
        )
        index = self.tab_widget.addTab(page, 'Comparison View')
        self.tab_widget.setCurrentIndex(index)

    def _window_context_menu(self, entry: Entry) -> QtWidgets.QMenu:
        """override for RootTreeView context menu"""
        menu = QtWidgets.QMenu(self)
        open_action = menu.addAction(
            f'&Open Detailed {type(entry).__name__} page'
        )
        # WeakPartialMethodSlot may not be needed, menus are transient
        open_action.triggered.connect(partial(self.open_page, entry))
        if isinstance(entry, Snapshot):
            restore_page_action = menu.addAction('Inspect values')
            restore_page_action.triggered.connect(partial(self.open_restore_page, entry))

        return menu

    def closeEvent(self, a0: QCloseEvent) -> None:
        # hide to mimic closing, and prevent confusion
        self.hide()
        while self.tab_widget.count() > 0:
            self.remove_tab(0)

        # use a copy of the cache, threads may finalize and be removed during iter
        for remaining_thread in list(get_qthread_cache()):
            if not remaining_thread.isFinished():
                remaining_thread.wait(5000)
                logger.debug(f"cleaned up remaining thread: {remaining_thread}")
        super().closeEvent(a0)
