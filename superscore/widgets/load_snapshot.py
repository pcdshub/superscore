'''
Currently opens smaller load configuration .ui, temporary load page
'''
from qtpy import QtWidgets

from superscore.widgets.core import Display


class LoadScreen(Display, QtWidgets.QDialog):
    filename = "load_snapshot_dialog.ui"
    label: QtWidgets.QLabel

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
