"""
Top-level window widget that contains other widgets
"""
from __future__ import annotations

from qtpy.QtWidgets import QMainWindow

from superscore.widgets.core import Display


class Window(Display, QMainWindow):
    """Main superscore window"""

    filename = 'main_window.ui'
