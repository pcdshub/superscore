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
from superscore.widgets.pv_browser_table import (PVBrowserFilterProxyModel,
                                                 PVBrowserTableModel)
from superscore.widgets.pv_table import PV_HEADER, PVTableModel
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
        self.pv_tables = []
        self.setup_ui()

    def setup_ui(self) -> None:
        self.navigation_panel = self.init_nav_panel()

        # Initialize content pages and add to stack
        self.snapshot_table = self.init_snapshot_table()
        self.pv_browser_page = self.init_pv_browser_page()

        self.main_content_stack = QtWidgets.QStackedLayout()
        self.main_content_stack.addWidget(self.snapshot_table)
        self.main_content_stack.addWidget(self.pv_browser_page)
        self.main_content_stack.setCurrentWidget(self.snapshot_table)
        self.main_content_container = QtWidgets.QWidget()
        self.main_content_container.setContentsMargins(0, 0, 0, 0)
        self.main_content_container.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        self.main_content_container.setLayout(self.main_content_stack)

        central_widget = QtWidgets.QWidget()
        central_widget.setLayout(QtWidgets.QHBoxLayout())
        central_widget.layout().addWidget(self.navigation_panel)
        central_widget.layout().addWidget(self.main_content_container)
        central_widget.layout().setSpacing(0)
        central_widget.layout().setContentsMargins(0, 0, 0, 0)
        self.setCentralWidget(central_widget)

        # open diff page
        self.diff_dispatcher.comparison_ready.connect(self.open_diff_page)

    def init_nav_panel(self) -> NavigationPanel:
        navigation_panel = NavigationPanel()
        navigation_panel.sigViewSnapshots.connect(self.open_snapshot_table)
        navigation_panel.sigBrowsePVs.connect(self.open_pv_browser_page)
        navigation_panel.set_nav_button_selected(navigation_panel.view_snapshots_button)
        navigation_panel.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
        return navigation_panel

    def init_snapshot_table(self) -> QtWidgets.QTableView:
        """Initialize the snapshot page"""
        snapshot_table = QtWidgets.QTableView()
        snapshot_table.setModel(SnapshotTableModel(self.client))
        snapshot_table.doubleClicked.connect(self.open_snapshot)
        snapshot_table.setStyleSheet(
            "QTableView::item {"
            "    border: 0px;"  # required to enforce padding on left side of cell
            "    padding: 5px;"
            "}"
        )
        snapshot_table.verticalHeader().hide()
        header_view = snapshot_table.horizontalHeader()
        header_view.setSectionResizeMode(header_view.ResizeToContents)
        header_view.setSectionResizeMode(1, header_view.Stretch)
        return snapshot_table

    def init_pv_browser_page(self) -> QtWidgets.QWidget:
        """Initialize the PV browser page with the PV browser table."""
        pv_browser_model = PVBrowserTableModel(self.client)
        pv_browser_filter = PVBrowserFilterProxyModel()
        pv_browser_filter.setSourceModel(pv_browser_model)

        pv_browser_page = QtWidgets.QWidget()
        pv_browser_layout = QtWidgets.QVBoxLayout()
        pv_browser_layout.setContentsMargins(0, 11, 0, 0)
        pv_browser_page.setLayout(pv_browser_layout)

        search_bar = QtWidgets.QLineEdit(pv_browser_page)
        search_bar.setClearButtonEnabled(True)
        search_bar.addAction(
            qta.icon("fa5s.search"),
            QtWidgets.QLineEdit.LeadingPosition,
        )
        search_bar.textChanged.connect(pv_browser_filter.setFilterFixedString)
        search_bar_lyt = QtWidgets.QHBoxLayout()
        spacer = QtWidgets.QSpacerItem(1, 1, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        search_bar_lyt.addWidget(search_bar)
        search_bar_lyt.addSpacerItem(spacer)
        pv_browser_layout.addLayout(search_bar_lyt)

        self.pv_browser_table = QtWidgets.QTableView(pv_browser_page)
        self.pv_browser_table.setModel(pv_browser_filter)
        self.pv_browser_table.verticalHeader().hide()
        header_view = self.pv_browser_table.horizontalHeader()
        header_view.setSectionResizeMode(header_view.ResizeToContents)
        header_view.setStretchLastSection(True)
        pv_browser_layout.addWidget(self.pv_browser_table)
        return pv_browser_page

    def open_pv_browser_page(self) -> None:
        """Open the PV Browser Page if it is not already open."""
        if self.main_content_stack.currentWidget() != self.pv_browser_page:
            self.main_content_stack.setCurrentWidget(self.pv_browser_page)
            self.navigation_panel.set_nav_button_selected(self.navigation_panel.browse_pvs_button)

    def open_snapshot_table(self) -> None:
        """Open the snapshot page if it is not already open."""
        if self.main_content_stack.currentWidget() != self.snapshot_table:
            self.main_content_stack.setCurrentWidget(self.snapshot_table)
            self.navigation_panel.set_nav_button_selected(self.navigation_panel.view_snapshots_button)

    def open_snapshot(self, index: QtCore.Qt.QModelIndex) -> None:
        snapshot = self.snapshot_table.model()._data[index.row()]
        pv_table = QtWidgets.QTableView()
        pv_table.setModel(PVTableModel(snapshot.uuid, self.client))
        pv_table.destroyed.connect(pv_table.model().close)
        pv_table.setShowGrid(False)
        pv_table.verticalHeader().hide()
        header_view = pv_table.horizontalHeader()
        header_view.setSectionResizeMode(header_view.Stretch)
        header_view.setSectionResizeMode(PV_HEADER.CHECKBOX.value, header_view.ResizeToContents)
        header_view.setSectionResizeMode(PV_HEADER.SEVERITY.value, header_view.ResizeToContents)
        header_view.setSectionResizeMode(PV_HEADER.DEVICE.value, header_view.ResizeToContents)
        header_view.setSectionResizeMode(PV_HEADER.PV.value, header_view.ResizeToContents)

        self.main_content_stack.addWidget(pv_table)
        self.main_content_stack.setCurrentWidget(pv_table)
        self.pv_tables.append(pv_table)  # Store a reference so they can be cleaned up later

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
        self.tab_widget.addTab(page, "new collection")
        self.tab_widget.setCurrentWidget(page)
        update_slot = WeakPartialMethodSlot(
            page.bridge.title,
            page.bridge.title.updated,
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
        logger.debug(f"attempting to open {entry}")
        if not isinstance(entry, Entry):
            logger.debug("Could not open page for non-Entry dataclass")
            return

        if type(entry) not in PAGE_MAP:
            logger.debug(f"No page corresponding to {type(entry).__name__}")

        try:
            page = PAGE_MAP[type(entry)]
        except KeyError:
            logger.debug(f"No page widget for {type(entry)}, cannot open in tab")
            return

        page_widget = page(data=entry, client=self.client)
        icon = qta.icon(ICON_MAP[type(entry)])
        tab_name = getattr(entry, "title", getattr(entry, "pv_name", f"<{type(entry).__name__}>"))
        idx = self.tab_widget.addTab(page_widget, icon, tab_name)
        self.tab_widget.setCurrentIndex(idx)

        return page_widget

    def open_index(self, index: QtCore.QModelIndex) -> None:
        entry: Entry = index.internalPointer()._data
        self.open_page(entry)

    def open_search_page(self) -> None:
        page = SearchPage(client=self.client)
        index = self.tab_widget.addTab(page, "search")
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
        index = self.tab_widget.addTab(page, "Comparison View")
        self.tab_widget.setCurrentIndex(index)

    def _window_context_menu(self, entry: Entry) -> QtWidgets.QMenu:
        """override for RootTreeView context menu"""
        menu = QtWidgets.QMenu(self)
        open_action = menu.addAction(f"&Open Detailed {type(entry).__name__} page")
        # WeakPartialMethodSlot may not be needed, menus are transient
        open_action.triggered.connect(partial(self.open_page, entry))
        if isinstance(entry, Snapshot):
            restore_page_action = menu.addAction("Inspect values")
            restore_page_action.triggered.connect(partial(self.open_restore_page, entry))

        return menu

    def closeEvent(self, a0: QCloseEvent) -> None:
        try:
            for pv_table in self.pv_tables:
                pv_table.model().stop_polling(wait_time=5000)
                pv_table.close()
        except AttributeError:
            pass
        super().closeEvent(a0)


class NavigationPanel(QtWidgets.QWidget):

    sigViewSnapshots = QtCore.Signal()
    sigBrowsePVs = QtCore.Signal()
    sigConfigureTags = QtCore.Signal()
    sigSave = QtCore.Signal()
    sigExpandedChanged = QtCore.Signal(bool)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setLayout(QtWidgets.QVBoxLayout())

        self.setStyleSheet(
            """
            QPushButton {
                padding: 8px;
                border-radius: 4px;
                text-align: left;
                border: none;
            }
            QPushButton:hover {
                background-color: lightgray;
            }
            QPushButton#save-snapshot-btn {
                border: 1px solid #555555;
                background-color: white;
            }
            QPushButton#save-snapshot-btn:hover {
                background-color: lightgray;
            }
            QPushButton[selected="true"] {
                background-color: white;
            }
            QPushButton[icon-only="true"] {
                text-align: center;
            }
        """
        )

        self.expanded = True

        self.view_snapshots_button = QtWidgets.QPushButton()
        self.view_snapshots_button.setIcon(qta.icon("ph.stack"))
        self.view_snapshots_button.setIconSize(QtCore.QSize(24, 24))
        self.view_snapshots_button.setText("View Snapshots")
        self.view_snapshots_button.setFlat(True)
        self.view_snapshots_button.setToolTip("View Snapshots")
        self.view_snapshots_button.clicked.connect(self.sigViewSnapshots.emit)
        self.layout().addWidget(self.view_snapshots_button)

        self.browse_pvs_button = QtWidgets.QPushButton()
        self.browse_pvs_button.setIcon(qta.icon("ph.database"))
        self.browse_pvs_button.setIconSize(QtCore.QSize(24, 24))
        self.browse_pvs_button.setText("Browse PVs")
        self.browse_pvs_button.setFlat(True)
        self.browse_pvs_button.setToolTip("Browse PVs")
        self.browse_pvs_button.clicked.connect(self.sigBrowsePVs.emit)
        self.layout().addWidget(self.browse_pvs_button)

        self.configure_tags_button = QtWidgets.QPushButton()
        self.configure_tags_button.setIcon(qta.icon("ph.tag"))
        self.configure_tags_button.setIconSize(QtCore.QSize(24, 24))
        self.configure_tags_button.setText("Configure Tags")
        self.configure_tags_button.setFlat(True)
        self.configure_tags_button.setToolTip("Configure Tags")
        self.configure_tags_button.clicked.connect(self.sigConfigureTags.emit)
        self.layout().addWidget(self.configure_tags_button)

        self.nav_buttons = [self.view_snapshots_button, self.browse_pvs_button, self.configure_tags_button]

        self.layout().addStretch()

        toggle_expand_layout = QtWidgets.QHBoxLayout()
        self.toggle_expand_button = QtWidgets.QPushButton()
        self.toggle_expand_button.setIcon(qta.icon("ph.arrow-line-left"))
        self.toggle_expand_button.setIconSize(QtCore.QSize(24, 24))
        self.toggle_expand_button.setFlat(True)
        self.toggle_expand_button.clicked.connect(self.toggle_expanded)
        toggle_expand_layout.addWidget(self.toggle_expand_button)
        toggle_expand_layout.addStretch()
        self.layout().addLayout(toggle_expand_layout)

        self.save_button = QtWidgets.QPushButton()
        self.save_button.setIcon(qta.icon("ph.instagram-logo"))
        self.save_button.setIconSize(QtCore.QSize(24, 24))
        self.save_button.setText("Save Snapshot")
        self.save_button.clicked.connect(self.sigSave.emit)
        self.save_button.setObjectName("save-snapshot-btn")
        self.layout().addWidget(self.save_button)

    def set_nav_button_selected(self, nav_button: QtWidgets.QPushButton) -> None:
        """Sets a nav button as selected and deselects the others.

        Args:
            nav_button (QtWidgets.QPushButton): The button to set as selected.
        """
        for button in self.nav_buttons:
            button.setProperty("selected", True if button == nav_button else False)
        self.reset_stylesheet()

    def toggle_expanded(self) -> None:
        """Toggles the expanded state of the nav panel"""
        self.set_expanded(not self.expanded)

    def set_expanded(self, value: bool) -> None:
        """Sets the expanded state of the nav panel and redraws the buttons appropriately"""
        if self.expanded != value:
            self.expanded = value
            if self.expanded:
                self.toggle_expand_button.setIcon(qta.icon("ph.arrow-line-left"))
                self.view_snapshots_button.setText("View Snapshots")
                self.browse_pvs_button.setText("Browse PVs")
                self.configure_tags_button.setText("Configure Tags")
                self.save_button.setText("Save Snapshot")
                for button in self.nav_buttons:
                    button.setProperty("icon-only", False)
                self.save_button.setProperty("icon-only", False)
            else:
                self.toggle_expand_button.setIcon(qta.icon("ph.arrow-line-right"))
                for button in self.nav_buttons:
                    button.setText("")
                    button.setProperty("icon-only", True)
                self.save_button.setText("")
                self.save_button.setProperty("icon-only", True)

            self.sigExpandedChanged.emit(self.expanded)
            self.reset_stylesheet()

    def reset_stylesheet(self) -> None:
        """Clears then resets stylesheet to force recomputation. Needed when property
        or object name driven styles should change."""
        stylesheet = self.styleSheet()
        self.setStyleSheet("")
        self.setStyleSheet(stylesheet)
