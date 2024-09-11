import logging

from qtpy import QtWidgets
from qtpy.QtGui import QCloseEvent

from superscore.client import Client
from superscore.model import Collection, Entry, Parameter
from superscore.widgets.core import DataWidget, Display, NameDescTagsWidget
from superscore.widgets.enhanced import FilterComboBox
from superscore.widgets.manip_helpers import insert_widget
from superscore.widgets.views import (LivePVTableModel, NestableTableModel,
                                      RootTree)

logger = logging.getLogger(__name__)


class CollectionBuilderPage(Display, DataWidget):
    filename = 'collection_builder_page.ui'
    data: Collection

    meta_placeholder: QtWidgets.QWidget
    meta_widget: NameDescTagsWidget

    tree_view: QtWidgets.QTreeView

    sub_coll_table_view: QtWidgets.QTableView
    sub_pv_table_view: QtWidgets.QTableView

    tab_widget: QtWidgets.QTabWidget
    # PV tab
    pv_line_edit: QtWidgets.QLineEdit
    rbv_line_edit: QtWidgets.QLineEdit
    # Colleciton tab
    add_collection_button: QtWidgets.QPushButton
    coll_combo_box: FilterComboBox
    coll_combo_box_placeholder: QtWidgets.QComboBox

    ro_checkbox: QtWidgets.QCheckBox
    add_pvs_button: QtWidgets.QPushButton

    save_button: QtWidgets.QPushButton

    def __init__(self, *args, data: Collection, client: Client, **kwargs):
        super().__init__(*args, data=data, **kwargs)
        self.client = client
        self.pv_model = None
        self.coll_model = None
        self._coll_options: list[Collection] = []
        # TODO: fill uuids here
        self.setup_ui()

    def setup_ui(self):
        self.meta_widget = NameDescTagsWidget(data=self.data)
        insert_widget(self.meta_widget, self.meta_placeholder)

        # wire add-buttons
        self.coll_combo_box = FilterComboBox()
        insert_widget(self.coll_combo_box, self.coll_combo_box_placeholder)
        self.update_collection_choices()
        self.save_button.clicked.connect(self.save_collection)
        self.add_collection_button.clicked.connect(self.add_sub_collection)
        self.add_pvs_button.clicked.connect(self.add_pv)
        self.ro_checkbox.stateChanged.connect(self.set_rbv_enabled)

        self.update_model_data()

    def set_rbv_enabled(self, state: int):
        """Disable RBV line edit if read-only checkbox is enabled"""
        self.rbv_line_edit.clear()
        self.rbv_line_edit.setEnabled(not bool(state))

    def update_model_data(self):
        # initialize tree
        self.tree_model = RootTree(base_entry=self.data)
        self.tree_view.setModel(self.tree_model)
        # initialize tables
        self.sub_colls = [child for child in self.data.children
                          if isinstance(child, Collection)]
        self.sub_pvs = [child for child in self.data.children
                        if not isinstance(child, Collection)]
        if self.pv_model is not None:
            logger.debug('stopping polling')
            self.pv_model.stop_polling()
            self.pv_model._poll_thread.wait(5000)

        # add model to two table views
        logger.debug(f"Creating new model with {len(self.sub_pvs)} parameters "
                     f"and {len(self.sub_colls)} collections")
        self.pv_model = LivePVTableModel(entries=self.sub_pvs, client=self.client)
        self.coll_model = NestableTableModel(entries=self.sub_colls)
        self.sub_pv_table_view.setModel(self.pv_model)
        self.sub_coll_table_view.setModel(self.coll_model)

    def save_collection(self):
        """Save current collection to database via Client"""
        self.data.title = self.meta_widget.name_edit.text(),
        self.data.description = self.meta_widget.desc_edit.toPlainText(),
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
        search_kwargs = {'entry_type': (Collection,)}
        self._coll_options = [res for res in self.client.search(**search_kwargs)
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
        self.pv_model.stop_polling()
        return super().closeEvent(a0)
