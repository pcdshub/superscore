"""
Top-level window widget that contains other widgets
"""
from __future__ import annotations

import logging
from functools import partial
from typing import Optional

import qtawesome as qta
from pcdsutils.qt.callbacks import WeakPartialMethodSlot
from qtpy import QtCore, QtWidgets
from qtpy.QtGui import QCloseEvent

from superscore.client import Client
from superscore.model import Entry, Snapshot
from superscore.widgets import ICON_MAP
from superscore.widgets.core import DataWidget, QtSingleton
from superscore.widgets.page import PAGE_MAP
from superscore.widgets.page.collection_builder import CollectionBuilderPage
from superscore.widgets.page.diff import DiffPage
from superscore.widgets.page.restore import RestorePage
from superscore.widgets.page.search import SearchPage
from superscore.widgets.snapshot_table import SnapshotTableModel
from superscore.widgets.views import DiffDispatcher

logger = logging.getLogger(__name__)


class Window(QtWidgets.QMainWindow, metaclass=QtSingleton):
    """Main superscore window"""

    # Diff dispatcher singleton, used to notify when diffs are ready
    diff_dispatcher: DiffDispatcher = DiffDispatcher()

    def __init__(self, *args, client: Optional[Client] = None, **kwargs):
        super().__init__(*args, **kwargs)
        if client:
            self.client = client
        else:
            self.client = Client.from_config()
        self._partial_slots = []
        self.setup_ui()

    def setup_ui(self) -> None:
        navigation_panel = NavigationPanel()
        navigation_panel.sigViewSnapshots.connect(self.open_snapshot_table)

        self.snapshot_table = QtWidgets.QTableView()
        self.snapshot_table.setModel(SnapshotTableModel(self.client))
        self.snapshot_table.setStyleSheet(
            "QTableView::item {"
            "    border: 0px;"  # required to enforce padding on left side of cell
            "    padding: 5px;"
            "}"
        )
        header_view = self.snapshot_table.horizontalHeader()
        header_view.setSectionResizeMode(header_view.ResizeToContents)
        header_view.setSectionResizeMode(1, header_view.Stretch)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(navigation_panel)
        splitter.addWidget(self.snapshot_table)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        self.setCentralWidget(splitter)

        # open diff page
        self.diff_dispatcher.comparison_ready.connect(self.open_diff_page)

    def open_snapshot_table(self):
        self.centralWidget().replaceWidget(1, self.snapshot_table)

    def remove_tab(self, tab_index: int) -> None:
        """Remove the requested tab and delete the widget"""
        widget = self.tab_widget.widget(tab_index)
        widget.close()
        widget.deleteLater()
        self.tab_widget.removeTab(tab_index)

    def _update_tab_title(self, tab_index: int) -> None:
        """Update a DataWidget tab title.  Assumes widget.title exists"""
        title_text = self.tab_widget.widget(tab_index)._title
        self.tab_widget.setTabText(tab_index, title_text)

    def open_collection_builder(self):
        """open collection builder page"""
        page = CollectionBuilderPage(client=self.client)
        self.tab_widget.addTab(page, 'new collection')
        self.tab_widget.setCurrentWidget(page)
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
            logger.debug(f'No page widget for {type(entry)}, cannot open in tab')
            return

        page_widget = page(data=entry, client=self.client)
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
        super().closeEvent(a0)


class NavigationPanel(QtWidgets.QWidget):

    sigViewSnapshots = QtCore.Signal()
    sigBrowsePVs = QtCore.Signal()
    sigConfigureTags = QtCore.Signal()
    sigSave = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setLayout(QtWidgets.QVBoxLayout())

        view_snapshots_button = QtWidgets.QPushButton()
        view_snapshots_button.setIcon(qta.icon("ph.stack"))
        view_snapshots_button.setText("View Snapshots")
        view_snapshots_button.setFlat(True)
        view_snapshots_button.clicked.connect(self.sigViewSnapshots.emit)
        self.layout().addWidget(view_snapshots_button)

        browse_pvs_button = QtWidgets.QPushButton()
        browse_pvs_button.setIcon(qta.icon("ph.database"))
        browse_pvs_button.setText("Browse PVs")
        browse_pvs_button.setFlat(True)
        browse_pvs_button.clicked.connect(self.sigBrowsePVs.emit)
        self.layout().addWidget(browse_pvs_button)

        configure_tags_button = QtWidgets.QPushButton()
        configure_tags_button.setIcon(qta.icon("ph.tag"))
        configure_tags_button.setText("Configure Tags")
        configure_tags_button.setFlat(True)
        configure_tags_button.clicked.connect(self.sigConfigureTags.emit)
        self.layout().addWidget(configure_tags_button)

        self.layout().addStretch()

        save_button = QtWidgets.QPushButton()
        save_button.setIcon(qta.icon("ph.instagram-logo"))
        save_button.setText("Save Snapshot")
        save_button.clicked.connect(self.sigSave.emit)
        self.layout().addWidget(save_button)
