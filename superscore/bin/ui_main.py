"""
`superscore ui` opens the graphical user interface for superscore

Function components are separated from the arg parser to defer heavy imports
"""
import sys
from typing import Optional

from qtpy.QtWidgets import QApplication

from superscore import exception
from superscore.client import Client
from superscore.widgets.window import Window

DEFAULT_WIDTH = 1400
DEFAULT_HEIGHT = 800


def main(cfg_path: Optional[str] = None):
    app = QApplication(sys.argv)
    if cfg_path:
        client = Client.from_config(cfg_path)
    else:
        client = None
    main_window = Window(client=client)

    primary_screen = app.screens()[0]
    center = primary_screen.geometry().center()
    # move window rather creating a QRect because we want to include the frame geometry
    main_window.setGeometry(0, 0, DEFAULT_WIDTH, DEFAULT_HEIGHT)
    delta = main_window.geometry().center()
    main_window.move(center - delta)
    main_window.show()

    exception.install()
    app.exec()
