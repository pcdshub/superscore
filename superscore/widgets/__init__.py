import qtawesome as qta

import superscore.color
from superscore.model import Severity, Status


def _get_icon_map():
    # do not pollute namespace
    from superscore.model import (Collection, Parameter, Readback, Setpoint,
                                  Snapshot)

    # a list of qtawesome icon names
    icon_map = {
        Collection: 'mdi.file-document-multiple',
        Parameter: 'mdi.file',
        Snapshot: 'mdi.camera',
        Setpoint: 'mdi.target',
        Readback: 'mdi.book-open-variant',
    }

    return icon_map


ICON_MAP = _get_icon_map()


class SeverityIcons:
    cache = {}
    scale = 1.3

    def __getitem__(self, key):
        try:
            return self.cache[key]
        except KeyError:
            if key == Severity.NO_ALARM or key == Status.NO_ALARM:
                icon = None
            elif key == Severity.MINOR:
                icon = qta.icon(
                    "ph.warning-fill",
                    color=superscore.color.YELLOW,
                    scale_factor=self.scale,
                )
            elif key == Severity.MAJOR:
                icon = qta.icon(
                    "ph.x-square-fill",
                    color=superscore.color.RED,
                    scale_factor=self.scale,
                )
            elif key == Severity.INVALID:
                icon = qta.icon(
                    "ph.question-fill",
                    color=superscore.color.MAGENTA,
                    scale_factor=self.scale,
                )
            elif isinstance(key, Status):  # not Status.NO_ALARM
                icon = qta.icon(
                    "mdi.disc",
                    color=superscore.color.GREY,
                    scale_factor=self.scale,
                )
            else:
                raise
            self.cache[key] = icon
            return icon


SEVERITY_ICONS = SeverityIcons()


def get_window():
    """
    Return the window singleton if it already exists, to allow other widgets to
    access its members.
    Must not be called in the code path that results from Window.__init__.
    A good (safe) rule of thumb is to make sure this function cannot be reached
    from any widget's __init__ method.
    Hides import in __init__ to avoid circular imports.
    """
    from .window import Window
    if Window._instance is None:
        return
    return Window()
