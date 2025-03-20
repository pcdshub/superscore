"""
`superscore ui` opens up the main application window.

The application will attempt to find and read configuration file.  This
configuration file path can also be provided manually.
"""
import argparse


def build_arg_parser(argparser=None):
    if argparser is None:
        argparser = argparse.ArgumentParser()
    argparser.add_argument(
        "--cfg-path",
        dest="cfg_path",
        type=str,
        help="A file path to a valid configuration file"
    )

    argparser.description = __doc__
    return argparser


def main(*args, **kwargs):
    from superscore.bin.ui_main import main
    main(*args, **kwargs)
