"""
`superscore ui` opens up the main application window
"""
import argparse
import sys
from typing import Optional

from qtpy.QtWidgets import QApplication

from superscore.client import Client
from superscore.widgets.window import Window


def build_arg_parser(argparser=None):
    if argparser is None:
        argparser = argparse.ArgumentParser()

    return argparser


def main(*args, client: Optional[Client] = None, **kwargs):
    app = QApplication(sys.argv)
    main_window = Window(client=client)

    main_window.show()
    app.exec()
