import os
from datetime import datetime, timezone
from pathlib import Path

SUPERSCORE_SOURCE_PATH = Path(__file__).parent


def utcnow():
    return datetime.now(timezone.utc)


def build_abs_path(basedir: str, path: str) -> str:
    """
    Builds an abs path starting at basedir if path is not already absolute.
    ~ and ~user constructions will be expanded, so ~/path is considered absolute.
    If path is absolute already, this function returns path without modification.
    Parameters
    ----------
    basedir : str
        If path is not absolute already, build an abspath
        with path starting here.
    path : str
        The path to convert to absolute.
    """
    path = os.path.expanduser(path)
    if not os.path.isabs(path):
        return os.path.abspath(os.path.join(basedir, path))
    return path
