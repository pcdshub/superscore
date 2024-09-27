"""

"""

import argparse
import logging
import os

from superscore.bin.ui import main as ui_main
from superscore.client import Client
from superscore.tests.conftest import linac_data
from superscore.tests.ioc import IOCFactory

logger = logging.getLogger(__name__)


def build_arg_parser(argparser=None):
    if argparser is None:
        argparser = argparse.ArgumentParser()
    return argparser


def main(*args, config_name: str = "tests/demo_config.cfg", **kwargs):
    coll, snap = linac_data()
    client = Client.from_config(config_name)
    try:
        os.remove(client.backend.path)
    except FileNotFoundError:
        pass
    client.save(coll)
    client.save(snap)
    # TODO: add Snapshot with varius severities and statuses
    with IOCFactory.from_entries(snap.children)(prefix=''):
        ui_main(*args, client=client, **kwargs)
