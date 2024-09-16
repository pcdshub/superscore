'''
Filter dialog launch and skeleton functionality
'''
from qtpy import QtWidgets

from superscore.widgets.core import Display


class FilterMenu(Display, QtWidgets.QWidget):
    filename = "filterScreen.ui"

    # filter snapshot horizaontal layout
    clearFilterButton: QtWidgets.QPushButton
    filterSnapshotLabel: QtWidgets.QLabel

    # Filter options vert layout
    collResetButton: QtWidgets.QPushButton
    collectionsLable: QtWidgets.QLabel
    collectionsTreeWidget: QtWidgets.QTreeWidget

    metaPvLabel: QtWidgets.QLabel
    metaPvResetButton: QtWidgets.QPushButton
    metaPvTableView: QtWidgets.QTableView

    tagLabel: QtWidgets.QLabel
    tagListWidget: QtWidgets.QListWidget
    tagResetButton: QtWidgets.QPushButton

    applyFiltersButton: QtWidgets.QPushButton

    def save_data(self):
        pass

    def get_collections(self):
        pass

    def get_metaPV(self):
        pass

    def get_tags(self):
        pass

    def fill_data_collections(self):
        pass

    def fill_data_metaPV(self):
        pass

    def fill_data_tags(self):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.applyFiltersButton.clicked.connect(self.save_data)
