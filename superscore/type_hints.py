from typing import Dict, Protocol, Union

AnyEpicsType = Union[int, str, float, bool]


class AnyDataclass(Protocol):
    """
    Protocol stub shamelessly lifted from stackoverflow to hint at dataclass
    """
    __dataclass_fields__: Dict
