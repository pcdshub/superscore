"""
`superscore demo` launches the UI along with a backend and an IOC
exposing PVs from a selected fixture. Select options in demo.cfg
"""

import argparse
import configparser
import logging
import os

import superscore.tests.conftest
from superscore.bin.ui import main as ui_main
from superscore.client import Client
from superscore.model import Entry, Readback, Setpoint, Snapshot
from superscore.tests.ioc import IOCFactory

logger = logging.getLogger(__name__)

DEMO_CONFIG = "tests/demo.cfg"


def build_arg_parser(argparser=None):
    if argparser is None:
        argparser = argparse.ArgumentParser()
    return argparser


def main(*args, **kwargs):
    client = Client.from_config(DEMO_CONFIG)
    # start with clean demo database
    try:
        os.remove(client.backend.path)
    except FileNotFoundError:
        pass
    parser = configparser.ConfigParser()
    parser.read(DEMO_CONFIG)
    filled = []  # IOCFactory needs the Entries with data
    for fixture_name in parser.get("demo", "fixtures").split():
        fixture = getattr(superscore.tests.conftest, fixture_name)
        data = fixture()
        # fixtures can return single Entries or iterables of Entries
        entries = (data,) if isinstance(data, Entry) else data
        for entry in entries:
            client.save(entry)
            if isinstance(entry, (Snapshot, Setpoint, Readback)):
                filled.append(entry)
    with IOCFactory.from_entries(filled)(prefix=''):
        ui_main(*args, client=client, **kwargs)
