"""Largely smoke tests for various pages"""

import pytest
from pytestqt.qtbot import QtBot

from superscore.client import Client
from superscore.model import Collection
from superscore.widgets.page.entry import CollectionPage
from superscore.widgets.page.search import SearchPage


@pytest.fixture(scope='function')
def collection_page(qtbot: QtBot):
    data = Collection()
    page = CollectionPage(data=data)
    qtbot.addWidget(page)
    return page


@pytest.fixture(scope='function')
def search_page(qtbot: QtBot, mock_client: Client):
    page = SearchPage(client=mock_client)
    qtbot.addWidget(page)
    return page


@pytest.mark.parametrize('page', ["collection_page", "search_page"])
def test_page_smoke(page: str, request: pytest.FixtureRequest):
    """smoke test, just create each page and see if they fail"""
    print(type(request.getfixturevalue(page)))
