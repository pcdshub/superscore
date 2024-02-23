"""
`superscore ui` opens up the main application window
"""
import argparse
import sys

from qtpy.QtWidgets import QApplication

from superscore.widgets.window import Window


def build_arg_parser(argparser=None):
    if argparser is None:
        argparser = argparse.ArgumentParser()

    return argparser


def main(*args, **kwargs):
    app = QApplication(sys.argv)
    main_window = Window()

    main_window.show()
    app.exec()
