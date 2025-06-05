"""
`superscore ui` opens the graphical user interface for superscore

Function components are separated from the arg parser to defer heavy imports
"""
import sys
from typing import Optional

from qtpy.QtWidgets import QApplication

from superscore.client import Client
from superscore.widgets.window import Window

MAX_DEFAULT_WIDTH = 1920
MAX_DEFAULT_HEIGHT = 1080


def main(cfg_path: Optional[str] = None):
    app = QApplication(sys.argv)
    if cfg_path:
        client = Client.from_config(cfg_path)
    else:
        client = None
    main_window = Window(client=client)

    primary_screen = app.screens()[0]
    screen_width = primary_screen.geometry().width()
    screen_height = primary_screen.geometry().height()
    width = min(int(screen_width*.7), MAX_DEFAULT_WIDTH)
    height = min(int(screen_height*.7), MAX_DEFAULT_HEIGHT)
    # move window rather creating a QRect because we want to include the frame geometry
    main_window.setGeometry(0, 0, width, height)
    center = primary_screen.geometry().center()
    delta = main_window.geometry().center()
    main_window.move(center - delta)
    main_window.show()
    app.exec()
