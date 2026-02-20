def get_page_map():
    # Don't pollute the namespace
    from superscore.model import (Collection, Entry, Parameter, Readback,
                                  Setpoint, Snapshot, Template)
    from superscore.widgets.core import DataWidget
    from superscore.widgets.page.entry import (CollectionPage, ParameterPage,
                                               ReadbackPage, SetpointPage,
                                               SnapshotPage)
    from superscore.widgets.page.template import TemplatePage

    page_map: dict[type[Entry], type[DataWidget]] = {
        Collection: CollectionPage,
        Snapshot: SnapshotPage,
        Parameter: ParameterPage,
        Setpoint: SetpointPage,
        Readback: ReadbackPage,
        Template: TemplatePage,
    }

    return page_map


PAGE_MAP = get_page_map()
