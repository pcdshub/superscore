from multiprocessing import Process
from typing import Iterable, Mapping

from caproto.server import PVGroup, pvproperty
from caproto.server import run as run_ioc
from epicscorelibs.ca import dbr

from superscore.client import Client
from superscore.model import Entry, Readback, Setpoint


class TempIOC(PVGroup):
    """
    Makes PVs accessible via EPICS when running. Instances automatically start
    and stop running when used as a context manager, and are thus suitable for
    use in tests.
    """
    def __enter__(self):
        self.running_process = Process(
            target=run_ioc,
            args=(self.pvdb,),
            daemon=True,
        )
        self.running_process.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass


class IOCFactory:
    """
    Generates TempIOC subclasses bound to a set of PVs.
    """
    @staticmethod
    def from_entries(entries: Iterable[Entry], client: Client, **ioc_options) -> PVGroup:
        """
        Defines and instantiates a TempIOC subclass containing all PVs reachable
        from entries.
        """
        attrs = IOCFactory.prepare_attrs(entries, client)
        IOC = type("IOC", (TempIOC,), attrs)
        return IOC

    @staticmethod
    def prepare_attrs(entries: Iterable[Entry], client: Client) -> Mapping[str, pvproperty]:
        """
        Turns a collecton of PVs into a Mapping from attribute names to
        caproto.pvproperties. The mapping is suitable for passing into a type()
        call as the dict arg.
        """
        pvs = []
        for entry in entries:
            leaves = client._gather_leaves(entry)
            pvs.extend(leaves)
        attrs = {}
        for entry in pvs:
            value = entry.data if isinstance(entry, (Setpoint, Readback)) else None
            pv = pvproperty(name=entry.pv_name, doc=entry.description, value=value, dtype=dbr.DBR_STRING if isinstance(entry.data, str) else None)
            attr = "".join([c.lower() for c in entry.pv_name if c.isalnum()])
            attrs[attr] = pv
        return attrs
