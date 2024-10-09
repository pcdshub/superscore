def get_page_map():
    # Don't pollute the namespace
    from superscore.model import (Collection, Parameter, Readback, Setpoint,
                                  Snapshot)
    from superscore.widgets.page.entry import (CollectionPage, ParameterPage,
                                               SnapshotPage)

    page_map = {
        Collection: CollectionPage,
        Snapshot: SnapshotPage,
        Parameter: ParameterPage,
        Setpoint: ParameterPage,
        Readback: ParameterPage,
    }

    return page_map


PAGE_MAP = get_page_map()
