""""""
import re
from typing import Iterable, Union
from uuid import UUID

from superscore.model import (Collection, Entry, Parameter, Readback, Root,
                              Setpoint, Snapshot)
from superscore.search_term import SearchTerm, SearchTermValue
from superscore.type_hints import AnyEpicsType


class EntryVisitor:
    """"""
    def __init__(self, backend):
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
    def __init__(self, backend, *search_terms: Iterable[SearchTerm]):
        super().__init__(backend)
        self.search_terms = search_terms
        self.matches = []

    def _check_match(self, entry: Union[Entry, Root]) -> bool:
        conditions = []
        for attr, op, target in self.search_terms:
            # TODO: search for child pvs?
            if attr == "entry_type":
                conditions.append(isinstance(entry, target))
            else:
                try:
                    # check entry attribute by name
                    value = getattr(entry, attr)
                    conditions.append(self.compare(op, value, target))
                except AttributeError:
                    conditions.append(False)
        if all(conditions):
            self.matches.append(entry)

    def visitParameter(self, parameter: Parameter) -> None:
        self._check_match(parameter)

    def visitSetpoint(self, setpoint: Setpoint) -> None:
        self._check_match(setpoint)

    def visitReadback(self, readback: Readback) -> None:
        self._check_match(readback)

    def visitCollection(self, collection: Collection) -> None:
        self._check_match(collection)

    def visitSnapshot(self, snapshot: Snapshot) -> None:
        self._check_match(snapshot)

    def visitRoot(self, root: Root) -> None:
        return

    @staticmethod
    def compare(op: str, data: AnyEpicsType, target: SearchTermValue) -> bool:
        """
        Return whether data and target satisfy the op comparator, typically during application
        of a search filter. Possible values of op are detailed in _Backend.search

        Parameters
        ----------
        op: str
            one of the comparators that all backends must support, detailed in _Backend.search
        data: AnyEpicsType | Tuple[AnyEpicsType]
            data from an Entry that is being used to decide whether the Entry passes a filter
        target: AnyEpicsType | Tuple[AnyEpicsType]
            the filter value

        Returns
        -------
        bool
            whether data and target satisfy the op condition
        """
        if op == "eq":
            return data == target
        elif op == "lt":
            return data <= target
        elif op == "gt":
            return data >= target
        elif op == "in":
            return data in target
        elif op == "like":
            if isinstance(data, UUID):
                data = str(data)
            return re.search(target, data)
        else:
            raise ValueError(f"SearchTerm does not support operator \"{op}\"")
