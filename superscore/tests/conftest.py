import shutil
from pathlib import Path
from typing import Callable, Iterable, List, Union
from unittest.mock import MagicMock

import pytest

from superscore.backends.core import _Backend
from superscore.backends.filestore import FilestoreBackend
from superscore.backends.test import TestBackend
from superscore.client import Client
from superscore.control_layers._base_shim import _BaseShim
from superscore.control_layers.core import ControlLayer
from superscore.model import Entry, Nestable, Root
from superscore.tests.ioc import IOCFactory
from superscore.widgets.views import EntryItem

# expose fixtures and helpers from other files in conftest so they will be gathered
from .conftest_data import (linac_data, linac_with_comparison_snapshot,  # NOQA
                            parameter_with_readback, sample_database,
                            setpoint_with_readback, simple_snapshot)


@pytest.fixture(scope='function')
def linac_backend():
    root = linac_data()
    return TestBackend(root.entries)


def populate_backend(backend, sources: Iterable[Union[Callable, str, Root, Entry]]) -> None:
    """
    Utility for quickly filling test backends with data. Supports a mix of many
    types of sources:
    * Roots
    * Entries
    * Callables that return Roots or Entries
    * strings that resolve in this function's global namespace to such Callables
    """
    namespace = globals()
    for source in sources:
        if isinstance(source, Callable):
            data = source()
        elif source in namespace:
            func = namespace[source]
            data = func()
        else:
            data = source
        if isinstance(data, Root):
            for entry in data.entries:
                backend.save_entry(entry)
        else:
            backend.save_entry(data)


@pytest.fixture(scope='function')
def filestore_backend(request, tmp_path: Path) -> FilestoreBackend:
    """
    This fixture is intended to be given data via pytest.mark.parametrize in each test
    definition that invokes it.  It can be parametrized even if a test doesn't invoke it
    directly, such as if a test invokes a client fixture that then invokes it.  Invoking this
    fixture without any parametrization results in a functional but empty backend.

    Parametrization in intermediate fixture definitions will be clobbered by test
    parametrization, so parametrizaton should only be done in test definitions to maintain
    clarity around which data is being used.

    Each parameter should be either:
    - a path to a valid filestore, absolute or relative to conftest.py
    - an Iterable of sources accepted by conftest.py::populate_backend

    e.g.
    @pytest.mark.parametrize("filestore_backend", ["db/filestore.json"], indirect=True)
    def my_test(filestore_backend):
        ...

    @pytest.mark.parametrize("filestore_backend", [("linac_data",)], indirect=True)
    def my_test(sample_client):
        ...
    """
    tmp_fp = tmp_path / 'tmp_filestore.json'
    try:
        source = request.param
    except AttributeError:
        backend = FilestoreBackend(path=tmp_fp)
    else:
        if isinstance(source, str):
            user_path = Path(source)
            fp = user_path if user_path.is_absolute() else Path(__file__).parent / user_path
            shutil.copy(fp, tmp_fp)
            backend = FilestoreBackend(path=tmp_fp)
        elif isinstance(source, Iterable):
            backend = FilestoreBackend(path=tmp_fp)
            populate_backend(backend, source)
    print(tmp_path)
    return backend


@pytest.fixture(scope='function')
def test_backends(filestore_backend: FilestoreBackend) -> List[_Backend]:
    return [filestore_backend,]


@pytest.fixture(scope='function')
def backends(request, test_backends: List[_Backend]):
    i = request.param
    return test_backends[i]


class DummyShim(_BaseShim):
    """Shim that does nothing"""
    async def get(self, *args, **kwargs):
        return

    async def put(self, *args, **kwargs):
        return

    def monitor(self, *args, **kwargs):
        return


@pytest.fixture(scope='function')
def dummy_cl() -> ControlLayer:
    cl = ControlLayer()
    cl.shims = {protocol: DummyShim() for protocol in ['ca', 'pva']}
    return cl


@pytest.fixture(scope='function')
def mock_backend() -> _Backend:
    mock_bk = MagicMock(spec=_Backend)
    return mock_bk


class MockTaskStatus:
    def exception(self):
        return None

    @property
    def done(self):
        return True


@pytest.fixture(scope='function')
def mock_client(mock_backend: _Backend) -> Client:
    client = Client(backend=mock_backend)
    return client


@pytest.fixture(scope='function')
def sample_client(
    filestore_backend: FilestoreBackend,
    dummy_cl: ControlLayer
) -> Client:
    """Return a client with actual data, but no communication capabilities"""
    client = Client(backend=filestore_backend)
    client.cl = dummy_cl

    return client


@pytest.fixture
def linac_ioc(linac_backend):
    _, snapshot = linac_data().entries
    client = Client(backend=linac_backend)
    with IOCFactory.from_entries(snapshot.children, client)(prefix="SCORETEST:") as ioc:
        yield ioc


def nest_depth(entry: Union[Nestable, EntryItem]) -> int:
    """
    Return the depth of nesting in ``entry``.
    Works for Entries or EntryItem's (tree items)
    """
    depths = []
    q = []
    q.append((entry, 0))  # entry and depth
    while q:
        e, depth = q.pop()
        if isinstance(e, Nestable):
            attr = 'children'
        elif isinstance(e, EntryItem):
            attr = '_children'
        else:
            depths.append(depth)
            continue

        children = getattr(e, attr)
        if not children:
            depths.append(depth)
        else:
            for child in children:
                q.append((child, depth+1))

    return max(depths)
