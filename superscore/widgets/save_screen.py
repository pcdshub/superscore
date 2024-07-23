'''
Save screen launch page and skeleton functionaliy
'''
from qtpy import QtWidgets

from superscore.widgets.core import Display


class SaveScreen(Display, QtWidgets.QWidget):
    filename = "saveScreen.ui"

    def get_title(self):
        pass

    def get_description(self):
        pass

    def get_collections(self):
        pass

    def get_tags(self):
        pass

    def final_save(self):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
