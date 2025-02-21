"""
`superscore demo` opens the graphical user interface for superscore with a demo
database pre-loaded

Function components are separated from the arg parser to defer heavy imports
"""
import configparser
import os
from pathlib import Path

from superscore.backends.core import populate_backend
from superscore.bin.demo import DEMO_CONFIG
from superscore.bin.ui import main as ui_main
from superscore.client import Client
from superscore.model import Readback, Setpoint
from superscore.tests.ioc import IOCFactory
from superscore.utils import build_abs_path


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
