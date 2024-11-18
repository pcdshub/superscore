""""""
from collections.abc import Union
from uuid import UUID

from superscore.backends import _Backend
from superscore.model import (Collection, Entry, Parameter, Readback, Root,
                              Setpoint, Snapshot)


class EntryVisitor:
    """"""
    def __init__(self, backend: _Backend):
        self.backend = backend

    def visit(self, entry: Union[Entry, Root, UUID]) -> None:
        if isinstance(entry, UUID):
            entry = self.backend.get_entry(entry)
        entry.accept(self)
        return

    def visitParameter(self, parameter: Parameter) -> None:
        raise NotImplementedError

    def visitSetpoint(self, setpoint: Setpoint) -> None:
        raise NotImplementedError

    def visitReadback(self, readback: Readback) -> None:
        raise NotImplementedError

    def visitCollection(self, collection: Collection) -> None:
        raise NotImplementedError

    def visitSnapshot(self, snapshot: Snapshot) -> None:
        raise NotImplementedError

    def visitRoot(self, root: Root) -> None:
        raise NotImplementedError


class FillUUIDVisitor(EntryVisitor):
    pass


class SnapVisitor(EntryVisitor):
    pass


class SearchVisitor(EntryVisitor):
    pass
