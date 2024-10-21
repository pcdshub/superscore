"""
`superscore demo` launches the UI along with a backend and an IOC
exposing PVs from a selected fixture. Select options in demo.cfg
"""

import argparse
import configparser
import logging
import os
from collections.abc import Iterable
from pathlib import Path

import superscore.tests.conftest
from superscore.bin.ui import main as ui_main
from superscore.client import Client
from superscore.model import Entry, Readback, Root, Setpoint, Snapshot
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
    filled = []  # IOCFactory needs the Entries with data
    for fixture_name in parser.get("demo", "fixtures").split():
        fixture = getattr(superscore.tests.conftest, fixture_name)
        data = fixture()
        # fixtures can return single Entries or iterables of Entries
        if isinstance(data, Root):
            entries = data.entries
        elif isinstance(data, Entry):
            entries = (data,)
        elif isinstance(data, Iterable):
            entries = data
        else:
            raise TypeError("Demo data must be a Root, Entry, or Iterable of "
                            f"Entries: received {type(data)} from {fixture_name}")
        for entry in entries:
            client.save(entry)
            if isinstance(entry, (Snapshot, Setpoint, Readback)):
                filled.append(entry)
    with IOCFactory.from_entries(filled)(prefix=''):
        ui_main(*args, client=client, **kwargs)
