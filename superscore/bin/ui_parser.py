"""
`superscore ui` opens up the main application window
"""
import argparse


def build_arg_parser(argparser=None):
    if argparser is None:
        argparser = argparse.ArgumentParser()

    return argparser


def main(*args, **kwargs):
    from superscore.bin.ui_main import main
    main(*args, **kwargs)
