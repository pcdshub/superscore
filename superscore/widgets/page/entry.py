"""
Widgets for visualizing and editing core model dataclasses
"""
import logging

from qtpy import QtWidgets
from qtpy.QtGui import QCloseEvent

from superscore.client import Client
from superscore.model import (Collection, Nestable, Parameter, Readback,
                              Setpoint, Snapshot)
from superscore.widgets.core import DataWidget, Display, NameDescTagsWidget
from superscore.widgets.manip_helpers import insert_widget
from superscore.widgets.views import (LivePVTableView, NestableTableView,
                                      RootTree)

logger = logging.getLogger(__name__)


class NestablePage(Display, DataWidget):
    filename = 'nestable_page.ui'

    meta_placeholder: QtWidgets.QWidget
    meta_widget: NameDescTagsWidget
    tree_view: QtWidgets.QTreeView
    sub_coll_table_view: NestableTableView
    sub_pv_table_view: LivePVTableView

    data: Nestable

    def __init__(
        self,
        *args,
        data: Nestable,
        client: Client,
        editable: bool = False,
        **kwargs
    ):
        super().__init__(*args, data=data, **kwargs)
        self.client = client
        self.editable = editable
        self.setup_ui()

    def setup_ui(self):
        self.meta_widget = NameDescTagsWidget(data=self.data)
        insert_widget(self.meta_widget, self.meta_placeholder)

        # show tree view
        self.model = RootTree(base_entry=self.data, client=self.client)
        self.tree_view.setModel(self.model)

        self.sub_pv_table_view.client = self.client
        self.sub_pv_table_view.set_data(self.data)

        self.sub_coll_table_view.client = self.client
        self.sub_coll_table_view.set_data(self.data)

    def closeEvent(self, a0: QCloseEvent) -> None:
        logger.debug(f"Stopping polling threads for {type(self.data)}")
        self.sub_pv_table_view._model.stop_polling(wait_time=5000)
        return super().closeEvent(a0)


class CollectionPage(NestablePage):
    data: Collection


class SnapshotPage(NestablePage):
    data: Snapshot


class ParameterPage(Display, DataWidget):
    filename = 'parameter_page.ui'

    meta_placeholder: QtWidgets.QWidget
    meta_widget: NameDescTagsWidget

    # Layouts
    pv_value_hlayout: QtWidgets.QHBoxLayout
    options_hlayout: QtWidgets.QHBoxLayout
    tol_form_layout: QtWidgets.QFormLayout
    ss_form_layout: QtWidgets.QFormLayout
    rbv_hlayout: QtWidgets.QHBoxLayout

    # dynamic display/edit widgets
    pv_edit: QtWidgets.QLineEdit
    value_live_label: QtWidgets.QLabel

    tolerance_calc_label: QtWidgets.QLabel
    abs_tol_spinbox: QtWidgets.QDoubleSpinBox
    rel_tol_spinbox: QtWidgets.QDoubleSpinBox
    timeout_spinbox: QtWidgets.QDoubleSpinBox

    open_rbv_button: QtWidgets.QPushButton
    rbv_pv_label: QtWidgets.QLabel

    data: Parameter

    def __init__(self, *args, client: Client, editable: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = client
        self.setup_ui()

    def setup_ui(self):
        self.pv_edit.setText(self.data.pv_name)


class SetpointPage(ParameterPage):
    data: Setpoint


class ReadbackPage(ParameterPage):
    data: Readback
