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
