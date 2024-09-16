'''
Currently opens "main page" that contians the snapshot view. This is the main page that is mocked up on MIRO with basic
button to dialog screen opening functionaliy. Including a skeleton for page functionality.
'''
from qtpy import QtWidgets

from superscore.widgets.core import Display
from superscore.widgets.filter_page import FilterMenu
from superscore.widgets.load_snapshot import LoadScreen
from superscore.widgets.save_screen import SaveScreen


class SnapshotMainpage(Display, QtWidgets.QMainWindow):
    filename = "snapshot_display_mainpage.ui"

    # collectionsVertLayout
    collSearchButton: QtWidgets.QPushButton
    searchLineEdit: QtWidgets.QLineEdit
    collectionsLabel: QtWidgets.QLabel
    collectionsTreeView: QtWidgets.QTreeView

    # Top box layout load/save/info buttons
    infoButton: QtWidgets.QPushButton
    loadConfigButton: QtWidgets.QPushButton
    saveButton: QtWidgets.QPushButton

    # filters layout
    chooseMonthSpinBox: QtWidgets.QSpinBox
    displaySnapshotLabel: QtWidgets.QLabel
    filterMenuButton: QtWidgets.QPushButton
    monthsAgoLabel: QtWidgets.QLabel
    searchDescButton: QtWidgets.QPushButton
    searchDescLineEdit: QtWidgets.QLineEdit
    searchTitleLineEdit: QtWidgets.QLineEdit
    searchTitleButton: QtWidgets.QPushButton

    loadPage: QtWidgets.QWidget

    # snapshot layout
    snapshotTableWidget: QtWidgets.QTableWidget

    def search_string_title(self):
        searchTerm = self.searchTitleLineEdit.text()
        self.refreshTable(searchTerm)
        pass

    def open_save_page(self):
        self.savePage = SaveScreen()
        self.savePage.show()

    def open_info_log(self):
        pass

    def open_filter_menu(self):
        self.filter = FilterMenu()
        self.filter.show()

    def open_load_config(self):
        self.loadPage = LoadScreen()
        self.loadPage.show()

    def spin_box_filter(self):
        pass

    def update_table(self):
        pass

    def tree_set_up(self):
        pass

    def refresh_table(self, newParameters):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setup_ui()

    def setup_ui(self):
        self.filterMenuButton.clicked.connect(self.open_filter_menu)

        self.loadConfigButton.clicked.connect(self.open_load_config)

        self.saveButton.clicked.connect(self.open_save_page)

        self.searchTitleButton.clicked.connect(self.search_string_title)
