"""
`superscore demo` launches the UI along with a backend and an IOC
exposing PVs from a selected fixture. Select options in demo.cfg
"""

import argparse
import logging
from pathlib import Path

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


def main(*args, **kwargs):
    from superscore.bin.demo_main import main
    main(*args, **kwargs)
