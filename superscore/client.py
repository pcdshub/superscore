"""Client for superscore.  Used for programmatic interactions with superscore"""
import configparser
import logging
import os
from pathlib import Path
from typing import Any, Generator, List, Optional, Union
from uuid import UUID

from superscore.backends import BACKENDS
from superscore.backends.core import _Backend
from superscore.control_layers import ControlLayer
from superscore.control_layers.status import TaskStatus
from superscore.model import Entry, Setpoint, Snapshot

logger = logging.getLogger(__name__)


class Client:
    backend: _Backend
    cl: ControlLayer

    def __init__(
        self,
        backend: Optional[_Backend] = None,
        control_layer: Optional[ControlLayer] = None,
    ) -> None:
        if backend is None:
            # set up a temp backend with temp file
            backend = BACKENDS['test']
        if control_layer is None:
            control_layer = ControlLayer()

        self.backend = backend
        self.cl = control_layer

    @classmethod
    def from_config(cls, cfg: Path = None):
        """
        Create a client from the configuration file specification.

        Configuration file should be of an "ini" format, along the lines of:

        .. code::

            [backend]
            type = filestore
            path = ./db/filestore.json

            [control_layer]
            ca = true
            pva = true

        The ``backend`` section has one special key ("type"), and the rest of the
        settings are passed to the appropriate ``_Backend`` as keyword arguments.

        The ``control_layer`` section has a key-value pair for each available shim.
        The ``ControlLayer`` object will be created with all the valid shims with
        True values.

        Parameters
        ----------
        cfg : Path, optional
            Path to a configuration file, by default None.  If omitted,
            :meth:`.find_config` will be used to find one

        Raises
        ------
        RuntimeError
            If a configuration file cannot be found
        """
        if not cfg:
            cfg = cls.find_config()
        if not os.path.exists(cfg):
            raise RuntimeError(f"Superscore configuration file not found: {cfg}")

        cfg_parser = configparser.ConfigParser()
        cfg_file = cfg_parser.read(cfg)
        logger.debug(f"Loading configuration file at ({cfg_file})")

        # Gather Backend
        if 'backend' in cfg_parser.sections():
            backend_type = cfg_parser.get("backend", "type")
            kwargs = {key: value for key, value
                      in cfg_parser["backend"].items()
                      if key != "type"}
            backend = BACKENDS[backend_type](**kwargs)
        else:
            backend = BACKENDS['test']()

        # configure control layer and shims
        if 'control_layer' in cfg_parser.sections():
            shim_choices = [val for val, enabled
                            in cfg_parser["control_layer"].items()
                            if enabled]
            control_layer = ControlLayer(shims=shim_choices)
        else:
            control_layer = ControlLayer()

        return cls(backend=backend, control_layer=control_layer)

    @staticmethod
    def find_config() -> Path:
        """
        Search for a ``superscore`` configuation file.  Searches in the following
        locations in order
        - ``$SUPERSCORE_CFG`` (a full path to a config file)
        - ``$XDG_CONFIG_HOME/{superscore.cfg, .superscore.cfg}`` (either filename)
        - ``~/.config/{superscore.cfg, .superscore.cfg}``

        Returns
        -------
        path : str
            Absolute path to the configuration file

        Raises
        ------
        OSError
            If no configuration file can be found by the described methodology
        """
        # Point to with an environment variable
        if os.environ.get('SUPERSCORE_CFG', False):
            happi_cfg = os.environ.get('SUPERSCORE_CFG')
            logger.debug("Found $SUPERSCORE_CFG specification for Client "
                         "configuration at %s", happi_cfg)
            return happi_cfg
        # Search in the current directory and home directory
        else:
            config_dirs = [os.environ.get('XDG_CONFIG_HOME', "."),
                           os.path.expanduser('~/.config'),]
            for directory in config_dirs:
                logger.debug('Searching for superscore config in %s', directory)
                for path in ('.superscore.cfg', 'superscore.cfg'):
                    full_path = os.path.join(directory, path)

                    if os.path.exists(full_path):
                        logger.debug("Found configuration file at %r", full_path)
                        return full_path
        # If found nothing
        raise OSError("No superscore configuration file found. Check SUPERSCORE_CFG.")

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
