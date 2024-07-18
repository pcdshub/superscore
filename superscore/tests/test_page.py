"""Largely smoke tests for various pages"""

from typing import List

import pytest
from pytestqt.qtbot import QtBot

from superscore.client import Client
from superscore.model import Collection
from superscore.widgets.core import DataWidget
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


@pytest.fixture(scope='function')
def test_pages(
    collection_page: CollectionPage,
    search_page: SearchPage,
) -> List[DataWidget]:
    return [collection_page, search_page,]


@pytest.fixture(scope='function')
def pages(request, test_pages: List[DataWidget]):
    i = request.param
    return test_pages[i]


@pytest.mark.parametrize('pages', [0, 1], indirect=True)
def test_page_smoke(pages):
    """smoke test, just create each page and see if they fail"""
    print(type(pages))
