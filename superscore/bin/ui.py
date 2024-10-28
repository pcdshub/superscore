"""
`superscore ui` opens up the main application window
"""
import argparse
import sys
from typing import Optional

from qtpy.QtWidgets import QApplication

from superscore.client import Client
from superscore.widgets.window import Window

DEFAULT_WIDTH = 1400
DEFAULT_HEIGHT = 800


def build_arg_parser(argparser=None):
    if argparser is None:
        argparser = argparse.ArgumentParser()

    return argparser


def main(*args, client: Optional[Client] = None, **kwargs):
    app = QApplication(sys.argv)
    main_window = Window(client=client)

    primary_screen = app.screens()[0]
    center = primary_screen.geometry().center()
    # move window rather creating a QRect because we want to include the frame geometry
    main_window.setGeometry(0, 0, DEFAULT_WIDTH, DEFAULT_HEIGHT)
    delta = main_window.geometry().center()
    main_window.move(center - delta)
    main_window.show()
    app.exec()
