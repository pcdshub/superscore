__all__ = ['BACKENDS']

import logging
from typing import Dict

from .core import _Backend

logger = logging.getLogger(__name__)


BACKENDS: Dict[str, type[_Backend]] = {}


def _get_backend(backend: str) -> type[_Backend]:
    if backend == 'filestore':
        from .filestore import FilestoreBackend
        return FilestoreBackend
    if backend == 'test':
        from .test import TestBackend
        return TestBackend
    if backend == 'directory':
        from .directory import DirectoryBackend
        return DirectoryBackend

    raise ValueError(f"Unknown backend {backend}")


def _init_backends() -> Dict[str, type[_Backend]]:
    backends = {}

    try:
        backends['filestore'] = _get_backend('filestore')
    except ImportError as ex:
        logger.debug(f"Filestore Backend unavailable: {ex}")

    try:
        backends['test'] = _get_backend('test')
    except ImportError as ex:
        logger.debug(f"Test Backend unavailable: {ex}")

    try:
        backends['directory'] = _get_backend('directory')
    except ImportError as ex:
        logger.debug(f"Directory Backend unavailable: {ex}")

    return backends


def get_backend(backend_name: str) -> type[_Backend]:
    try:
        backend = BACKENDS[backend_name]
    except KeyError:
        # try to load it
        try:
            BACKENDS[backend_name] = _get_backend(backend_name)
            backend = BACKENDS[backend_name]
        except ValueError:
            raise ValueError(f'Backend {backend_name} not supported. Available '
                             f'backends include: ({list(BACKENDS.keys())})')
        except ImportError as ex:
            raise ValueError(f'Backend {(backend_name)} failed to load: {ex}')

    return backend


BACKENDS = _init_backends()
