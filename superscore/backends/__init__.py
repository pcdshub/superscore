__all__ = ['BACKENDS']

import logging
from typing import Dict

from .core import _Backend

logger = logging.getLogger(__name__)


def _get_backend(backend: str) -> _Backend:
    if backend == 'filestore':
        from .filestore import FilestoreBackend
        return FilestoreBackend
    if backend == 'test':
        from .test import TestBackend
        return TestBackend

    raise ValueError(f"Unknown backend {backend}")


def _get_backends() -> Dict[str, _Backend]:
    backends = {}

    try:
        backends['filestore'] = _get_backend('filestore')
    except ImportError as ex:
        logger.debug(f"Filestore Backend unavailable: {ex}")

    try:
        backends['test'] = _get_backend('test')
    except ImportError as ex:
        logger.debug(f"Test Backend unavailable: {ex}")

    return backends


BACKENDS = _get_backends()
