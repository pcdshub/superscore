from typing import TYPE_CHECKING, Callable, Dict, Protocol, Union

if TYPE_CHECKING:
    from superscore.model import Entry
    from superscore.widgets.core import DataWidget

AnyEpicsType = Union[int, str, float, bool]


class AnyDataclass(Protocol):
    """
    Protocol stub shamelessly lifted from stackoverflow to hint at dataclass
    """
    __dataclass_fields__: Dict


OpenPageSlot = Callable[["Entry"], "DataWidget"]
