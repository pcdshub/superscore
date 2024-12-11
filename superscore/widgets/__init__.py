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
