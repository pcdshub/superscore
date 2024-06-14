from typing import Any, Callable, Optional, overload

from superscore.control_layers.status import TaskStatus

class ControlLayer:
    @overload
    def get(self, pv: str) -> Any:
        ...

    @overload
    def get(self, pv: list[str]) -> list[Any]:
        ...

    @overload
    def put(
        self,
        pv: str,
        value: Any,
        cb: Optional[Callable] = None
    ) -> TaskStatus:
        ...

    @overload
    def put(
        self,
        pv: list,
        value: list,
        cb: Optional[list[Callable]] = None
    ) -> list[TaskStatus]:
        ...
