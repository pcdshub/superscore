
from qtpy import QtWidgets

from superscore.model import Collection
from superscore.widgets.core import DataWidget, Display, NameDescTagsWidget
from superscore.widgets.manip_helpers import insert_widget
from superscore.widgets.tree import RootTree


class CollectionPage(Display, DataWidget):
    filename = 'collection_page.ui'

    meta_placeholder: QtWidgets.QWidget
    meta_widget: NameDescTagsWidget
    child_tree_view: QtWidgets.QTreeView
    pv_table: QtWidgets.QTableWidget
    repr_text_edit: QtWidgets.QTextEdit

    data: Collection

    def __init__(self, *args, data: Collection, **kwargs):
        super().__init__(*args, data=data, **kwargs)
        self.setup_ui()

    def setup_ui(self):
        self.meta_widget = NameDescTagsWidget(data=self.data)
        insert_widget(self.meta_widget, self.meta_placeholder)

        self.repr_text_edit.setText(str(self.data))
        # recurse through children and gather PVs
        # show tree view
        self.model = RootTree(base_entry=self.data)
        self.child_tree_view.setModel(self.model)
