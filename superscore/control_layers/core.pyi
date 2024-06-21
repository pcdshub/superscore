from typing import Any, Callable, Optional, overload

from superscore.control_layers.status import TaskStatus

class ControlLayer:
    @overload
    def get(self, address: str) -> Any:
        ...

    @overload
    def get(self, address: list[str]) -> list[Any]:
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
