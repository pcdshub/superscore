from pytestqt.qtbot import QtBot

from superscore.widgets.window import Window


def test_main_window(qtbot: QtBot):
    """Pass if main window opens successfully"""
    window = Window()
    qtbot.addWidget(window)
