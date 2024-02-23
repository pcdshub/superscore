"""
Core classes for qt-based GUIs.
"""
from pathlib import Path

from pcdsutils.qt.designer_display import DesignerDisplay

from superscore.utils import SUPERSCORE_SOURCE_PATH


class Display(DesignerDisplay):
    """Helper class for loading designer .ui files and adding logic"""

    ui_dir: Path = SUPERSCORE_SOURCE_PATH / 'ui'
