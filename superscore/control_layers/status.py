from __future__ import annotations

import asyncio
import functools
from typing import Awaitable, Callable, Optional, Type, TypeVar, cast

TS = TypeVar("TS", bound="TaskStatus")


class TaskStatus:
    """
    Unified Status object for wrapping task completion information and attaching
    callbacks. This must be created inside of a coroutine, but can be returned to
    synchronous scope for examining the task.

    Awaiting this status is similar to awaiting the wrapped task.

    Largely vendored from bluesky/ophyd-async
    """

    def __init__(self, awaitable: Awaitable):
        if isinstance(awaitable, asyncio.Task):
            self.task = awaitable
        else:
            self.task = asyncio.create_task(awaitable)
        self.task.add_done_callback(self._run_callbacks)
        self._callbacks: list[Callable] = []

    def __await__(self):
        return self.task.__await__()

    def add_callback(self, callback: Callable):
        if self.done:
            callback(self)
        else:
            self._callbacks.append(callback)

    def _run_callbacks(self, task: asyncio.Task):
        for callback in self._callbacks:
            callback(self)

    def exception(self) -> Optional[BaseException]:
        if self.task.done():
            try:
                return self.task.exception()
            except asyncio.CancelledError as e:
                return e
        return None

    @property
    def done(self) -> bool:
        return self.task.done()

    @property
    def success(self) -> bool:
        return (
            self.task.done()
            and not self.task.cancelled()
            and self.task.exception() is None
        )

    def wait(self, timeout=None) -> None:
        """
        Block until the coroutine finishes.  Raises asyncio.TimeoutError if
        the timeout elapses before the task is completed

        To be called in a synchronous context, if the status has not been awaited

        Parameters
        ----------
        timeout : number, optional
            timeout in seconds, by default None

        Raises
        ------
        asyncio.TimeoutError
        """
        # ensure task runs in the event loop it was assigned to originally
        asyncio.get_event_loop().run_until_complete(
            asyncio.wait_for(self.task, timeout)
        )

    def __repr__(self) -> str:
        if self.done:
            if e := self.exception():
                status = f"errored: {repr(e)}"
            else:
                status = "done"
        else:
            status = "pending"
        return f"<{type(self).__name__}, task: {self.task.get_coro()}, {status}>"

    __str__ = __repr__

    @classmethod
    def wrap(cls: Type[TS], f: Callable[..., Awaitable]) -> Callable[..., TS]:
        """Wrap an async function in a TaskStatus."""

        @functools.wraps(f)
        def wrap_f(*args, **kwargs) -> TS:
            return cls(f(*args, **kwargs))

        return cast(Callable[..., TS], wrap_f)
