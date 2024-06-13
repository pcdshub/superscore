from unittest.mock import AsyncMock

from superscore.control_layers.status import TaskStatus


def test_get(dummy_cl):
    mock_ca_get = AsyncMock(return_value='ca_value')
    dummy_cl.shims['ca'].get = mock_ca_get
    mock_pva_get = AsyncMock(return_value='pva_value')
    dummy_cl.shims['pva'].get = mock_pva_get
    assert dummy_cl.get("SOME_PREFIX") == "ca_value"
    assert dummy_cl.get("ca://SOME_PREFIX") == "ca_value"
    assert dummy_cl.get("pva://SOME_PREFIX") == "pva_value"


def test_put(dummy_cl):
    result = dummy_cl.put("OTHER:PREFIX", 4)
    assert isinstance(result, TaskStatus)
    assert result.done

    results = dummy_cl.put(["OTHER:PREFIX", "GE", "LT"], [4, 5, 6])
    assert all(isinstance(res, TaskStatus) for res in results)
    assert result.done


def test_put_callback(dummy_cl):
    cbs = []

    # callback gets called with the task as a single argument
    result = dummy_cl.put("SOME:PREFIX", 2, cbs.append)

    assert result.exception() is None
    assert result.success is True
    assert len(cbs) == 1
