"""Largely smoke tests for various pages"""

from pytestqt.qtbot import QtBot

from superscore.model import Collection
from superscore.widgets.page.entry import CollectionPage


def test_collection_page(qtbot: QtBot):
    data = Collection()
    page = CollectionPage(data=data)
    qtbot.addWidget(page)
