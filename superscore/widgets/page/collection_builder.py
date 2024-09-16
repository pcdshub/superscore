import logging
from typing import Callable, Optional

from qtpy import QtCore, QtWidgets
from qtpy.QtGui import QCloseEvent

from superscore.client import Client
from superscore.model import Collection, Entry, Parameter
from superscore.widgets.core import DataWidget, Display, NameDescTagsWidget
from superscore.widgets.enhanced import FilterComboBox
from superscore.widgets.manip_helpers import insert_widget
from superscore.widgets.views import (BaseTableEntryModel, ButtonDelegate,
                                      LivePVHeader, LivePVTableModel,
                                      NestableTableModel, RootTree)

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

    def __init__(
        self,
        *args,
        client: Client,
        data: Optional[Collection] = None,
        open_page_slot: Optional[Callable] = None,
        **kwargs
    ):
        if data is None:
            data = Collection()
        super().__init__(*args, data=data, **kwargs)
        self.client = client
        self.open_page_slot = open_page_slot
        self.pv_model = None
        self.coll_model = None
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

        self.update_model_data()

        # Configure button delegates
        self.pv_open_delegate = ButtonDelegate(button_text='open details')
        self.sub_pv_table_view.setItemDelegateForColumn(LivePVHeader.OPEN,
                                                        self.pv_open_delegate)
        self.pv_open_delegate.clicked.connect(self.open_sub_pv_row)

        self.pv_remove_delegate = ButtonDelegate(button_text='remove')
        self.sub_pv_table_view.setItemDelegateForColumn(LivePVHeader.REMOVE,
                                                        self.pv_remove_delegate)
        self.pv_remove_delegate.clicked.connect(self.remove_sub_pv_row)

        self.nest_open_delegate = ButtonDelegate(button_text='open details')
        self.sub_coll_table_view.setItemDelegateForColumn(
            3, self.nest_open_delegate
        )
        self.nest_open_delegate.clicked.connect(self.open_sub_coll_row)

        self.nest_remove_delegate = ButtonDelegate(button_text='remove')
        self.sub_coll_table_view.setItemDelegateForColumn(
            4, self.nest_remove_delegate
        )
        self.nest_remove_delegate.clicked.connect(self.remove_sub_coll_row)

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

    def open_sub_pv_row(self, index: QtCore.QModelIndex) -> None:
        self.open_row_details(self.pv_model, index)

    def open_sub_coll_row(self, index: QtCore.QModelIndex) -> None:
        self.open_row_details(self.coll_model, index)

    def remove_entry(self, entry: Entry) -> None:
        self.data.children.remove(entry)
        self.update_model_data()

    def remove_sub_pv_row(self, index: QtCore.QModelIndex) -> None:
        entry = self.pv_model.entries[index.row()]
        self.remove_entry(entry)

    def remove_sub_coll_row(self, index: QtCore.QModelIndex) -> None:
        entry = self.coll_model.entries[index.row()]
        self.remove_entry(entry)

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
            self.pv_model._poll_thread.data = {}
            self.pv_model.stop_polling()
            self.pv_model._poll_thread.wait(5000)

        # add model to two table views
        logger.debug(f"Creating new model with {len(self.sub_pvs)} parameters "
                     f"and {len(self.sub_colls)} collections")
        self.pv_model = LivePVTableModel(entries=self.sub_pvs, client=self.client)
        self.coll_model = NestableTableModel(entries=self.sub_colls)
        self.sub_pv_table_view.setModel(self.pv_model)

        # TODO: un-hard code this once there is a better way of managing columns
        # Potentially dealing with columns that have moved
        for i in [LivePVHeader.STORED_VALUE, LivePVHeader.STORED_SEVERITY,
                  LivePVHeader.STORED_STATUS]:
            self.sub_pv_table_view.setColumnHidden(i, True)

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
