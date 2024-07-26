"""
Top-level window widget that contains other widgets
"""
from __future__ import annotations

import logging
from typing import Optional

import qtawesome as qta
from qtpy import QtCore, QtWidgets

from superscore.client import Client
from superscore.model import Entry
from superscore.widgets import ICON_MAP
from superscore.widgets.core import Display
from superscore.widgets.page import PAGE_MAP
from superscore.widgets.page.search import SearchPage

logger = logging.getLogger(__name__)


class Window(Display, QtWidgets.QMainWindow):
    """Main superscore window"""

    filename = 'main_window.ui'

    tree_view: QtWidgets.QTreeView
    tab_widget: QtWidgets.QTabWidget

    def __init__(self, *args, client: Optional[Client] = None, **kwargs):
        super().__init__(*args, **kwargs)
        if client:
            self.client = client
        else:
            self.client = Client.from_config()

        self.setup_ui()
        self.open_search_page()

    def setup_ui(self) -> None:
        tab_bar = self.tab_widget.tabBar()
        # always use scroll area and never truncate file names
        tab_bar.setUsesScrollButtons(True)
        tab_bar.setElideMode(QtCore.Qt.ElideNone)
        self.tab_widget.tabCloseRequested.connect(self.tab_widget.removeTab)

    def open_page(self, entry: Entry) -> None:
        """
        Open a page for ``entry`` in a new tab.

        Parameters
        ----------
        entry : Entry
            Entry subclass to open a new page for
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

        page_widget = page(data=entry)
        icon = qta.icon(ICON_MAP[type(entry)])
        tab_name = getattr(
            entry, 'title', getattr(entry, 'pv_name', f'<{type(entry).__name__}>')
        )
        idx = self.tab_widget.addTab(page_widget, icon, tab_name)
        self.tab_widget.setCurrentIndex(idx)

    def open_search_page(self) -> None:
        page = SearchPage(client=self.client, open_page_slot=self.open_page)
        self.tab_widget.addTab(page, 'search')
