from pytestqt.qtbot import QtBot

from superscore.client import Client
from superscore.widgets.window import Window


def test_main_window(qtbot: QtBot, mock_client: Client):
    """Pass if main window opens successfully"""
    window = Window(client=Client)
    qtbot.addWidget(window)
