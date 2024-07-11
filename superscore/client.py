"""Client for superscore.  Used for programmatic interactions with superscore"""
import logging
from typing import Any, Generator, List, Optional, Union
from uuid import UUID

from superscore.backends.core import _Backend
from superscore.control_layers import ControlLayer
from superscore.control_layers.status import TaskStatus
from superscore.model import Entry, Setpoint, Snapshot

logger = logging.getLogger(__name__)


class Client:
    backend: _Backend
    cl: ControlLayer

    def __init__(self, backend: _Backend, **kwargs) -> None:
        self.backend = backend
        self.cl = ControlLayer()

    @classmethod
    def from_config(cls, cfg=None):
        raise NotImplementedError

    def search(self, **post) -> Generator[Entry, None, None]:
        """Search by key-value pair.  Can search by any field, including id"""
        return self.backend.search(**post)

    def save(self, entry: Entry):
        """Save information in ``entry`` to database"""
        # validate entry is valid
        self.backend.save_entry(entry)

    def delete(self, entry: Entry) -> None:
        """Remove item from backend, depending on backend"""
        # check for references to ``entry`` in other objects?
        self.backend.delete_entry(entry)

    def compare(self, entry_l: Entry, entry_r: Entry) -> Any:
        """Compare two entries.  Should be of same type, and return a diff"""
        raise NotImplementedError

    def apply(
        self,
        entry: Union[Setpoint, Snapshot],
        sequential: bool = False
    ) -> Optional[List[TaskStatus]]:
        """
        Apply settings found in ``entry``.  If no writable values found, return.
        If ``sequential`` is True, apply values in ``entry`` in sequence, blocking
        with each put request.  Else apply all values simultaneously (asynchronously)

        Parameters
        ----------
        entry : Union[Setpoint, Snapshot]
            The entry to apply values from
        sequential : bool, optional
            Whether to apply values sequentially, by default False

        Returns
        -------
        Optional[List[TaskStatus]]
            TaskStatus(es) for each value applied.
        """
        if not isinstance(entry, (Setpoint, Snapshot)):
            logger.info("Entries must be a Snapshot or Setpoint")
            return

        if isinstance(entry, Setpoint):
            return [self.cl.put(entry.pv_name, entry.data)]

        # Gather pv-value list and apply at once
        status_list = []
        pv_list, data_list = self._gather_data(entry)
        if sequential:
            for pv, data in zip(pv_list, data_list):
                logger.debug(f'Putting {pv} = {data}')
                status: TaskStatus = self.cl.put(pv, data)
                if status.exception():
                    logger.warning(f"Failed to put {pv} = {data}, "
                                   "terminating put sequence")
                    return

                status_list.append(status)
        else:
            return self.cl.put(pv_list, data_list)

    def _gather_data(
        self,
        entry: Union[Setpoint, Snapshot, UUID],
        pv_list: Optional[List[str]] = None,
        data_list: Optional[List[Any]] = None
    ) -> Optional[tuple[List[str], List[Any]]]:
        """
        Gather writable pv name - data pairs recursively.
        If pv_list and data_list are provided, gathered data will be added to
        these lists in-place. If both lists are omitted, this function will return
        the two lists after gathering.

        Queries the backend to fill any UUID values found.

        Parameters
        ----------
        entry : Union[Setpoint, Snapshot, UUID]
            Entry to gather writable data from
        pv_list : Optional[List[str]], optional
            List of addresses to write data to, by default None
        data_list : Optional[List[Any]], optional
            List of data to write to addresses in ``pv_list``, by default None

        Returns
        -------
        Optional[tuple[List[str], List[Any]]]
            the filled pv_list and data_list
        """
        top_level = False
        if (pv_list is None) and (data_list is None):
            pv_list = []
            data_list = []
            top_level = True
        elif (pv_list is None) or (data_list is None):
            raise ValueError(
                "Arguments pv_list and data_list must either both be provided "
                "or both omitted."
            )

        if isinstance(entry, Snapshot):
            for child in entry.children:
                self._gather_data(child, pv_list, data_list)
        elif isinstance(entry, UUID):
            child_entry = self.backend.get_entry(entry)
            self._gather_data(child_entry, pv_list, data_list)
        elif isinstance(entry, Setpoint):
            pv_list.append(entry.pv_name)
            data_list.append(entry.data)

        # Readbacks are not writable, and are not gathered

        if top_level:
            return pv_list, data_list

    def validate(self, entry: Entry):
        """
        Validate ``entry`` is properly formed and able to be inserted into
        the backend.  Includes checks the following:
        - dataclass is valid
        - reachable from root
        - references are not cyclical, and type-correct
        """
        raise NotImplementedError
