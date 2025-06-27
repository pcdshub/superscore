import qtawesome as qta
from qtpy import QtCore, QtWidgets

from superscore.client import Client
from superscore.widgets.page.page import Page
from superscore.widgets.pv_browser_table import (PVBrowserFilterProxyModel,
                                                 PVBrowserTableModel)
from superscore.widgets.squirrel_table_view import SquirrelTableView
from superscore.widgets.tag import TagsWidget


class PVBrowserPage(Page):

    open_details_signal = QtCore.Signal(QtCore.QModelIndex, QtWidgets.QAbstractItemView)

    def __init__(self, client: Client, parent: QtWidgets.QWidget = None):
        super().__init__(parent)
        self.client = client

        self.setup_ui()

    def setup_ui(self):
        """Initialize the PV browser page with the PV browser table."""

        pv_browser_layout = QtWidgets.QVBoxLayout()
        pv_browser_layout.setContentsMargins(0, 11, 0, 0)
        self.setLayout(pv_browser_layout)

        self.search_bar = QtWidgets.QLineEdit(self)
        self.search_bar.setClearButtonEnabled(True)
        self.search_bar.addAction(
            qta.icon("fa5s.search"),
            QtWidgets.QLineEdit.LeadingPosition,
        )
        search_bar_lyt = QtWidgets.QHBoxLayout()
        spacer = QtWidgets.QSpacerItem(1, 1, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        search_bar_lyt.addWidget(self.search_bar)
        search_bar_lyt.addSpacerItem(spacer)
        pv_browser_layout.addLayout(search_bar_lyt)

        filter_tags = TagsWidget(tag_groups=self.client.backend.get_tags(), enabled=True)
        pv_browser_layout.addWidget(filter_tags)

        pv_browser_model = PVBrowserTableModel(self.client)
        self.pv_browser_filter = PVBrowserFilterProxyModel()
        self.pv_browser_filter.setSourceModel(pv_browser_model)

        self.pv_browser_table = SquirrelTableView(self)
        self.pv_browser_table.setModel(self.pv_browser_filter)
        header_view = self.pv_browser_table.horizontalHeader()
        header_view.setSectionResizeMode(header_view.Fixed)
        header_view.setStretchLastSection(True)
        pv_browser_layout.addWidget(self.pv_browser_table)
        self.pv_browser_table.resizeColumnsToContents()

        self.search_bar.editingFinished.connect(self.search_bar_middle_man)
        filter_tags.tagSetChanged.connect(self.pv_browser_filter.set_tag_set)
        self.pv_browser_table.doubleClicked.connect(self.open_details_middle_man)

    @QtCore.Slot()
    def search_bar_middle_man(self):
        search_text = self.search_bar.text()
        self.pv_browser_filter.setFilterFixedString(search_text)

    @QtCore.Slot(QtCore.QModelIndex)
    def open_details_middle_man(self, index: QtCore.QModelIndex):
        if not isinstance(index, QtCore.QModelIndex) or not index.isValid():
            return
        self.open_details_signal.emit(index, self.pv_browser_table)
