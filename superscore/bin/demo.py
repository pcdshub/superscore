"""
`superscore demo` launches the UI along with a backend and an IOC
exposing PVs from a selected fixture. Select options in demo.cfg
"""

import argparse
import configparser
import logging
import os
from pathlib import Path

from superscore.backends.test import populate_backend
from superscore.bin.ui import main as ui_main
from superscore.client import Client
from superscore.model import Readback, Setpoint
from superscore.tests.ioc import IOCFactory
from superscore.utils import build_abs_path

logger = logging.getLogger(__name__)

DEMO_CONFIG = Path(__file__).parent.parent / "tests" / "demo.cfg"


def build_arg_parser(argparser=None):
    if argparser is None:
        argparser = argparse.ArgumentParser()
    argparser.add_argument(
        "--db-path",
        type=str,
        help="An alternate file or directory to store the demo database. This "
             "file will be overwritten each run.")
    return argparser


def main(*args, db_path=None, **kwargs):
    parser = configparser.ConfigParser()
    parser.read(DEMO_CONFIG)
    if db_path is not None:
        db_path = Path(db_path)
        if db_path.is_dir():
            db_path /= 'superscore_demo.json'
        parser.set('backend', 'path', build_abs_path(Path.cwd(), db_path))
    client = Client.from_parsed_config(parser)
    # start with clean demo database
    try:
        os.remove(client.backend.path)
    except FileNotFoundError:
        pass
    # write data from the sources to the backend
    source_names = parser.get("demo", "fixtures").split()
    populate_backend(client.backend, source_names)
    # IOCFactory needs the Entries with data
    filled = [entry for entry in client.search() if isinstance(entry, (Setpoint, Readback))]
    with IOCFactory.from_entries(filled, client)(prefix=''):
        ui_main(*args, client=client, **kwargs)
