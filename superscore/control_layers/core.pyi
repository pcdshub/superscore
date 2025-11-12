from collections.abc import Iterable
from typing import Any, Callable, List, Optional, overload

from superscore.control_layers.status import TaskStatus

class ControlLayer:

    def __init__(self, shims: Optional[List[str]] = None) -> None: ...

    @overload
    def get(self, address: str) -> Any:
        ...

    @overload
    def get(self, address: Iterable[str]) -> list[Any]:
        ...

    @overload
    def put(
        self,
        address: str,
        value: Any,
        cb: Optional[Callable] = None
    ) -> TaskStatus:
        ...

    @overload
    def put(
        self,
        address: list,
        value: list,
        cb: Optional[list[Callable]] = None
    ) -> list[TaskStatus]:
        ...
