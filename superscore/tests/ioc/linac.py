from caproto.server import ioc_arg_parser, run

from superscore.tests.conftest import linac_data
from superscore.tests.ioc import IOCFactory

if __name__ == '__main__':
    _, snapshot = linac_data()
    LinacIOC = IOCFactory.from_entries(snapshot.children)

    ioc_options, run_options = ioc_arg_parser(
        default_prefix='SCORETEST:',
        desc="IOC evoking the structure of a linac",
    )
    ioc = LinacIOC(**ioc_options)
    run(ioc.pvdb, **run_options)
