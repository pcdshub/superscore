import asyncio
from typing import Any, Callable

import pytest

from superscore.control_layers.status import TaskStatus


@pytest.fixture
async def normal_coroutine() -> Callable[[], Any]:
    async def inner_coroutine():
        await asyncio.sleep(0.01)

    return inner_coroutine


@pytest.fixture
async def failing_coroutine() -> Callable[[], Any]:
    async def inner_coroutine():
        await asyncio.sleep(0.01)
        raise ValueError()

    return inner_coroutine


@pytest.fixture
async def long_coroutine_status() -> TaskStatus:
    @TaskStatus.wrap
    async def inner_coroutine():
        for i in range(100):
            print(f'coro wait: {i}')
            await asyncio.sleep(1)

    return inner_coroutine()


async def test_status_success(normal_coroutine):
    st = TaskStatus(normal_coroutine())
    assert isinstance(st, TaskStatus)
    assert not st.done
    assert not st.success
    await st
    assert st.done
    assert st.success


async def test_status_fail(failing_coroutine):
    status = TaskStatus(failing_coroutine())
    assert status.exception() is None

    with pytest.raises(ValueError):
        await status

    assert isinstance(status.exception(), ValueError)


def test_status_wait(long_coroutine_status):
    assert not long_coroutine_status.done
    with pytest.raises(asyncio.TimeoutError):
        long_coroutine_status.wait(1)
    assert long_coroutine_status.done
    assert isinstance(long_coroutine_status.exception(), asyncio.CancelledError)


async def test_status_wrap():
    @TaskStatus.wrap
    async def coro_status():
        await asyncio.sleep(0.01)

    st = coro_status()
    assert isinstance(st, TaskStatus)
    await st
    assert st.done
