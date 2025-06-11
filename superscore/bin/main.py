"""
`superscore` is the top-level command for accessing various subcommands.

Try:

"""

import argparse
import asyncio
import importlib
import logging
from inspect import iscoroutinefunction

import superscore
from superscore.permission_manager import PermissionManager

logger = logging.getLogger('superscore')


DESCRIPTION = __doc__
MODULES = ("ui", "demo")


def _try_import(module):
    relative_module = f'.{module}'
    return importlib.import_module(relative_module, 'superscore.bin')


def _build_commands():
    """
    Search for *_parser submodules to gather and build subcommands.
    Each submodule should have two functions:
    * `build_arg_parser`: takes an argparser instance and adds any necessary
                          arguments
    * `main`: imports the main routine from a different submodule and runs it

    This separation ensures that heavier imports can be deferred until necessary,
    and argparse details (help text, argument descriptions) are returned quickly.

    Also builds up the the argparse description whenever a subcommand is added.
    """
    global DESCRIPTION
    result = {}
    unavailable = []

    for module in sorted(MODULES):
        try:
            mod = _try_import(module + "_parser")
        except Exception as ex:
            unavailable.append((module, ex))
        else:
            result[module] = (mod.build_arg_parser, mod.main)
            DESCRIPTION += f'\n    $ superscore {module} --help'

    if unavailable:
        for module, ex in unavailable:
            logger.warning(
                f'WARNING: "{module}" subcommand is unavailable due to:'
                f'\n\t{ex.__class__.__name__}: {ex}'
            )

    return result


COMMANDS = _build_commands()


def main():
    top_parser = argparse.ArgumentParser(
        prog='superscore',
        description=DESCRIPTION,
        formatter_class=argparse.RawTextHelpFormatter
    )

    top_parser.add_argument(
        '--version', '-V',
        action='version',
        version=superscore.__version__,
        help="Show the superscore version number and exit."
    )

    top_parser.add_argument(
        '--log', '-l', dest='log_level',
        default='INFO',
        type=str,
        help='Python logging level (e.g. DEBUG, INFO, WARNING)'
    )

    top_parser.add_argument(
        '-a', '--admin',
        action='store_true',
        help='Launch with admin privileges enabled'
    )

    subparsers = top_parser.add_subparsers(help='Possible subcommands')
    for command_name, (build_func, main) in COMMANDS.items():
        sub = subparsers.add_parser(command_name)
        build_func(sub)
        sub.set_defaults(func=main)

    args = top_parser.parse_args()
    kwargs = vars(args)
    log_level = kwargs.pop('log_level')
    admin_mode = kwargs.pop('admin')
    logger.setLevel(log_level)

    if admin_mode:
        permission_manager = PermissionManager.get_instance()
        permission_manager.set_admin_mode(True)
        logger.info("Admin mode enabled via launch flag")

    if hasattr(args, 'func'):
        func = kwargs.pop('func')
        logger.debug('%s(**%r)', func.__name__, kwargs)
        if iscoroutinefunction(func):
            asyncio.run(func(**kwargs))
        else:
            func(**kwargs)
    else:
        top_parser.print_help()


if __name__ == '__main__':
    main()
