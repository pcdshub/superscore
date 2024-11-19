import logging
from typing import Optional

from qtpy import QtCore, QtWidgets
from qtpy.QtGui import QCloseEvent

from superscore.client import Client
from superscore.model import Collection, Entry, Parameter
from superscore.type_hints import OpenPageSlot
from superscore.widgets.core import DataWidget, Display, NameDescTagsWidget
from superscore.widgets.enhanced import FilterComboBox
from superscore.widgets.manip_helpers import insert_widget
from superscore.widgets.views import (BaseTableEntryModel, LivePVHeader,
                                      LivePVTableView, NestableTableView,
                                      RootTree, RootTreeView)

logger = logging.getLogger(__name__)


class CollectionBuilderPage(Display, DataWidget):
    filename = 'collection_builder_page.ui'
    data: Collection

    meta_placeholder: QtWidgets.QWidget
    meta_widget: NameDescTagsWidget

    tree_view: RootTreeView

    sub_coll_table_view: NestableTableView
    sub_pv_table_view: LivePVTableView

    tab_widget: QtWidgets.QTabWidget
    # PV tab
    pv_line_edit: QtWidgets.QLineEdit
    rbv_line_edit: QtWidgets.QLineEdit
    # Collection tab
    add_collection_button: QtWidgets.QPushButton
    coll_combo_box: FilterComboBox
    coll_combo_box_placeholder: QtWidgets.QComboBox

    ro_checkbox: QtWidgets.QCheckBox
    add_pvs_button: QtWidgets.QPushButton

    save_button: QtWidgets.QPushButton

    def __init__(
        self,
        *args,
        client: Client,
        data: Optional[Collection] = None,
        open_page_slot: Optional[OpenPageSlot] = None,
        **kwargs
    ):
        if data is None:
            data = Collection()
        super().__init__(*args, data=data, **kwargs)
        self.client = client
        self.open_page_slot = open_page_slot
        self.tree_model = None
        self._coll_options: list[Collection] = []
        self._title = self.data.title
        # TODO: fill uuids here
        self.setup_ui()

    def setup_ui(self):
        self.meta_widget = NameDescTagsWidget(data=self.data)
        insert_widget(self.meta_widget, self.meta_placeholder)

        self.bridge.title.updated.connect(self._update_title)

        # wire add-buttons
        self.coll_combo_box = FilterComboBox()
        insert_widget(self.coll_combo_box, self.coll_combo_box_placeholder)
        self.update_collection_choices()
        self.save_button.clicked.connect(self.save_collection)
        self.add_collection_button.clicked.connect(self.add_sub_collection)
        self.add_pvs_button.clicked.connect(self.add_pv)
        self.ro_checkbox.stateChanged.connect(self.set_rbv_enabled)

        # set up views
        self.sub_pv_table_view.client = self.client
        self.sub_pv_table_view.set_data(self.data)
        for i in [LivePVHeader.STORED_VALUE, LivePVHeader.STORED_SEVERITY,
                  LivePVHeader.STORED_STATUS]:
            self.sub_pv_table_view.setColumnHidden(i, True)
        self.sub_pv_table_view.set_editable(LivePVHeader.PV_NAME, True)

        self.sub_coll_table_view.client = self.client
        self.sub_coll_table_view.set_data(self.data)

        self.tree_view.client = self.client
        self.tree_view.set_data(self.data)
        self.tree_view.open_page_slot = self.open_page_slot
        self.tree_model: RootTree = self.tree_view.model()

        self.sub_coll_table_view.data_updated.connect(self.tree_model.refresh_tree)
        self.sub_pv_table_view.data_updated.connect(self.tree_model.refresh_tree)

    def _update_title(self):
        """Set title attribute for access by containing widgets"""
        self._title = self.data.title

    def open_row_details(
        self, model: BaseTableEntryModel, index: QtCore.QModelIndex
    ) -> None:
        if self.open_page_slot is not None:
            # If adding proxy model, more robust data retrieval is needed
            entry = model.entries[index.row()]
            self.open_page_slot(entry)

    def set_rbv_enabled(self, state: int):
        """Disable RBV line edit if read-only checkbox is enabled"""
        self.rbv_line_edit.clear()
        self.rbv_line_edit.setEnabled(not bool(state))

    def update_model_data(self):
        """
        Update the model data.  Signal the models to re-read the data
        """
        self.tree_model.refresh_tree()
        self.sub_pv_table_view.set_data(self.data)
        self.sub_coll_table_view.set_data(self.data)

    def save_collection(self):
        """Save current collection to database via Client"""
        self.data.title = self.meta_widget.name_edit.text()
        self.data.description = self.meta_widget.desc_edit.toPlainText()
        # children should have been updated along the way
        self.client.save(self.data)
        logger.info(f"Collection saved ({self.data.uuid})")

    def check_valid(self, entry: Entry) -> bool:
        """Check if adding ``entry`` to the collection is valid"""
        raise NotImplementedError

    def add_pv(self):
        """
        Read pv line edits, and add to the model and list, refresh
        Readbacks without corresponding setpoint PVs are ignored
        Checking read-only will disable readback line edit
        """
        # Gather PV names
        pvs = [pv.strip(" ") for pv in self.pv_line_edit.text().split(",") if pv]
        rbvs = [rbv.strip(" ") for rbv in self.rbv_line_edit.text().split(",") if rbv]

        if len(pvs) == 0:
            logger.debug("no PVs supplied, nothing to do")
            return

        # Make Parameter's and add to self.data.collections (preserve order)
        for pv_name, rbv_name in zip(pvs, rbvs):
            readback = Parameter(pv_name=rbv_name, read_only=True)
            setpoint = Parameter(pv_name=pv_name, readback=readback)
            # ignore read-only flag for setpoint-rbv pairs
            logger.debug(f'Adding {setpoint} with readback {readback}')
            self.data.children.append(setpoint)

        for pv_idx in range(len(rbvs), len(pvs)):
            # Create single parameters for any leftover PVs
            param = Parameter(pv_name=pvs[pv_idx],
                              read_only=self.ro_checkbox.isChecked())
            logger.debug(f"Adding stand-alone parameter ({param})")
            self.data.children.append(param)

        # re-generate pv_model data (keep in sync)
        self.update_model_data()

        # clear text
        self.pv_line_edit.clear()
        self.rbv_line_edit.clear()

    def update_collection_choices(self):
        """update collection choices based on line edit"""
        search_term = ('entry_type', 'eq', Collection)
        self._coll_options = [res for res in self.client.search(search_term)
                              if res not in (self.data.children, self)]
        logger.debug(f"Gathered {len(self._coll_options)} collections")
        self.coll_combo_box.clear()
        self.coll_combo_box.addItems([c.title for c in self._coll_options])

    def add_sub_collection(self):
        """read combo box, add collection to model and list, refresh"""
        selected = self._coll_options[self.coll_combo_box.currentIndex()]
        self.data.children.append(selected)
        logger.debug(f"Added {selected.title}({selected.uuid}) to the collection")
        self.update_collection_choices()
        self.update_model_data()

    def closeEvent(self, a0: QCloseEvent) -> None:
        logger.debug("Stopping pv_model polling")
        self.sub_pv_table_view._model.stop_polling(wait_time=5000)
        return super().closeEvent(a0)
