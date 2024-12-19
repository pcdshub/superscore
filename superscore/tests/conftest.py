import inspect
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union
from unittest.mock import MagicMock

import apischema
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


@pytest.fixture(scope="function")
def test_data(request: pytest.FixtureRequest) -> Root:
    """
    Return the requested data from the specified fixture or callable.  A common
    entry point to gather any and all data-related fixtures for consumption in
    downstream data-stack fixtures.

    By default, returns a `Root` with no child entries (of no sources specified)

    Expects `request.param` to return a dictionary with the schema:
    {
        sources: List[StringNameOfFixtureOrCallable]
}

    Supports fixtures and callables that resolve to:
    * Root
    * Entry

    To use alone, parametrize the fixture with a string that exactly matches a
    fixture or function accessible from the conftest.py namespace

    .. code::

        @pytest.mark.parametrize(test_data, [
            {"sources": ["parameter_with_readback"]}
        ], indirect=True)
        def my_test(test_data: Entry):
            assert isinstance(test_data, Root)
    """
    print(">> test_data fixture setup")
    kwargs: Dict[str, Any] = getattr(request, "param", dict())
    sources = kwargs.get("sources", [])
    namespace = globals()

    new_root = Root()
    for source in sources:
        if source in namespace:
            try:
                data = request.getfixturevalue(source)
            except pytest.FixtureLookupError:
                # not a fixture, should be a function
                func = namespace[source]
                data = func()
        elif isinstance(source, str):
            user_path = Path(source)
            fpath = user_path if user_path.is_absolute() else Path(__file__).parent / user_path
            with open(fpath) as fp:
                serialized = json.load(fp)
            data = apischema.deserialize(Root, serialized)

        if isinstance(data, Root):
            for entry in data.entries:
                new_root.entries.append(entry)
        elif isinstance(data, Entry):
            new_root.entries.append(data)

    return new_root


@pytest.fixture(scope="function")
def test_backend(
    request: pytest.FixtureRequest,
    test_data: Root,
    tmp_path: Path
) -> _Backend:
    """
    Return a `_Backend` parametrized with the information in `request.param`, and
    containing `test_data`.

    By default, returns a `MockBackend` that cannot return or save data

    Expects `request.param` to return a dictionary with the schema:
    {
        backend_type: Type[_Backend]
    }

    To use alone, parametrize the fixture with the desired _Backend subclass.

    .. code::

        @pytest.mark.parametrize("test_backend", [
            {"backend_type": FilestoreBackend}
        ], indirect=True)
        def my_test(test_backend: Entry):
            assert isinstance(test_backend, FilestoreBackend)

    You can also specify which data to include in the backend, even if test_data
    is not explicitly used in the test.  (It is implicitly used in this fixture)

    .. code::

        @pytest.mark.parametrize("test_data,test_backend", [
            ({"sources": ["setpoint_with_readback"]}, {"backend_type": TestBackend})
        ], indirect=True)
        def test_set_backend_and_data(test_backend: _Backend, setpoint_with_readback: Setpoint):
            assert isinstance(test_backend, TestBackend)
            assert test_backend.root.entries[0] is setpoint_with_readback
    """
    kwargs: Dict[str, Any] = getattr(request, "param", dict())
    bknd_type = kwargs.get("backend_type", "MockBackend")
    print(bknd_type, kwargs)
    if bknd_type == "MockBackend":
        backend = request.getfixturevalue("mock_backend")
    else:
        backend_cls: Type[_Backend] = bknd_type
        if backend_cls is FilestoreBackend:
            tmp_fp = tmp_path / 'tmp_filestore.json'
            backend = backend_cls(path=tmp_fp)
        else:
            backend = backend_cls()

    for entry in test_data.entries:
        backend.save_entry(entry)

    return backend


@pytest.fixture(scope="function")
def test_client(
    request: pytest.FixtureRequest,
    test_backend: _Backend,
) -> Client:
    """
    Return a `Client` parametrized with information in `request.param`, and
    holding the backend returned from `test_backend`.

    By default, returns a `Client` with a `MockBackend` and mocked ControlLayer

    Component fixtures can be specified per-test, or left as default here.
    This takes advantage of the fact that a fixture is defined by its most recent
    invocation (meaning if we re-define the test_data fixture at the test, that
    definition will be used in this fixture)

    Expects `request.param` to return a dictionary with the schema:
    {
        mock_cl: bool, by default True
    }

    To use alone, parametrize the fixture with and optionally its upstream
    fixtures (test_data, test_backend)
    .. code::

        @pytest.mark.parametrize("test_data,test_backend,test_client,", [(
            {"sources": ["db/filestore.json",]},
            {"type": FilestoreBackend},
            {"mock_cl": True},
        )], indirect=True)
        def my_test(test_client: Client):
            assert "filestore.json" in test_client.backend.path
    """
    kwargs: Dict[str, Any] = getattr(request, "param", dict())
    client = Client(backend=test_backend)
    # Set up control layer
    if kwargs.get("mock_cl", True):
        cl = MagicMock(spec=ControlLayer)
        client.cl = cl

    return client


def setup_test_stack(
    sources: Optional[List[str]] = None,
    backend_type: Optional[Type[_Backend]] = None,
    mock_cl: bool = True,
):
    """
    Set up the test stack (data, backend, client) for a test given the
    parameters above.  By default produces a `Client` with a mocked `_Backend`
    and `ControlLayer`, which can neither save nor return data.

    If you are using the default settings of the above fixtures, you do not need
    to use this decorator.

    This is a convenience wrapper around @pytest.mark.parametrize

    To use, simply supply the requested arguments:

    .. code-block:: python

        @setup_test_stack(
            sources: ["db/filestore.json", "linac_data"],
            backend_type: FilestoreBackend,
            mock_cl=False
        )
        def test_full_stack(test_client: Client):
            # do a test

    Intricacies:
    - currently no way to parametrize and generate multiple tests
    - need to define on tests, not fixtures that call test_*
        - those tests may not actually have test_* etc in params
    - the decorated test must request the "highest level" fixture expected by
      itself and its own fixtures
        - if a test invokes a fixture that uses `test_client`, it must itself
          also request test_client for this decorator to work

    """
    def decorator(func):
        param_list = []
        # gather data_params
        data_params = {"sources": sources or []}
        backend_params = {"backend_type": backend_type or "MockBackend"}
        client_params = {"mock_cl": mock_cl}

        # gather requisite fixtures, ignoring parameters for components higher
        # in the food chain
        func_params = inspect.signature(func).parameters
        if "test_client" in func_params:
            fixture_list = "test_data,test_backend,test_client,"
            param_list = [(data_params, backend_params, client_params)]
        elif "test_backend" in func_params:
            fixture_list = "test_data,test_backend,"
            param_list = [(data_params, backend_params)]
        elif "test_data" in func_params:
            fixture_list = "test_data,"
            param_list = [data_params]
        else:
            raise ValueError(
                "None of (test_data, test_backend, test_client) fixtures found "
                "in test arguments.  Using this helper decorator requires at least "
                "the highest level fixture used in the fixture chain to be "
                "referenced as an argument."
                "This is true even if the `test_*` fixture is used in a fixture, "
                "but not directly in the test itself."
            )

        print(f"Setting up test stack with: {fixture_list}, "
              "({len(param_list)}){param_list}")

        # This takes advantage of the fact that fixture definitions are gathered
        # first, then run.  This means that if a fixture requests a plain
        # test_backend, but we re-parametrize it right before the test
        # (with this decorator), all fixtures in the chain will use the parametrized
        # test_backend.  We are in essence re-defining fixture parameters before
        # they are used.
        return pytest.mark.parametrize(
            fixture_list, param_list, indirect=True
        )(func)

    return decorator
