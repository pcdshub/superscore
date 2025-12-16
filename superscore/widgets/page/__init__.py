def get_page_map():
    # Don't pollute the namespace
    from superscore.model import (Collection, Entry, Parameter, Readback,
                                  Setpoint, Snapshot)
    from superscore.widgets.core import DataWidget
    from superscore.widgets.page.entry import (CollectionPage, ParameterPage,
                                               ReadbackPage, SetpointPage,
                                               SnapshotPage)

    page_map: dict[type[Entry], type[DataWidget]] = {
        Collection: CollectionPage,
        Snapshot: SnapshotPage,
        Parameter: ParameterPage,
        Setpoint: SetpointPage,
        Readback: ReadbackPage,
    }

    return page_map


PAGE_MAP = get_page_map()
