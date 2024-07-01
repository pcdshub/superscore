"""
Top-level window widget that contains other widgets
"""
from __future__ import annotations

from qtpy import QtWidgets

from superscore.widgets.core import Display


class Window(Display, QtWidgets.QMainWindow):
    """Main superscore window"""

    filename = 'main_window.ui'

    tree_view: QtWidgets.QTreeView
    tab_widget: QtWidgets.QTabWidget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
