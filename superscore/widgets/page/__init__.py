def get_page_icon_map():
    # Don't pollute the namespace
    from superscore.model import Collection, Readback, Setpoint, Snapshot
    from superscore.widgets.page.entry import CollectionPage

    page_map = {
        Collection: CollectionPage
    }

    # a list of qtawesome icon names
    icon_map = {
        Collection: 'mdi.file-document-multiple',
        Snapshot: 'mdi.camera',
        Setpoint: 'mdi.target',
        Readback: 'mdi.book-open-variant',
    }

    return page_map, icon_map


PAGE_MAP, ICON_MAP = get_page_icon_map()
