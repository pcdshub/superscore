def get_page_map():
    # Don't pollute the namespace
    from superscore.model import Collection
    from superscore.widgets.page.entry import CollectionPage

    page_map = {
        Collection: CollectionPage
    }

    return page_map


PAGE_MAP = get_page_map()
