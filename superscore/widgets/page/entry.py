"""
Widgets for visualizing and editing core model dataclasses
"""
import logging
from typing import Callable, Optional, Union

import qtawesome as qta
from qtpy import QtWidgets
from qtpy.QtGui import QCloseEvent

from superscore.client import Client
from superscore.control_layers._base_shim import EpicsData
from superscore.model import (Collection, Nestable, Parameter, Readback,
                              Setpoint, Severity, Snapshot, Status)
from superscore.type_hints import AnyEpicsType
from superscore.widgets.core import DataWidget, Display, NameDescTagsWidget
from superscore.widgets.manip_helpers import insert_widget
from superscore.widgets.views import (LivePVTableView, NestableTableView,
                                      RootTree, edit_widget_from_epics_data)

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
        open_page_slot: Optional[Callable] = None,
        **kwargs
    ):
        super().__init__(*args, data=data, **kwargs)
        self.client = client
        self.editable = editable
        self.open_page_slot = open_page_slot
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


class BaseParameterPage(Display, DataWidget):
    filename = 'parameter_page.ui'

    meta_placeholder: QtWidgets.QWidget
    meta_widget: NameDescTagsWidget

    # Container widgets
    pv_value_hlayout: QtWidgets.QHBoxLayout
    options_hlayout: QtWidgets.QHBoxLayout
    tol_widget: QtWidgets.QWidget
    ss_widget: QtWidgets.QWidget
    timeout_widget: QtWidgets.QWidget
    rbv_widget: QtWidgets.QWidget

    # dynamic display/edit widgets
    pv_edit: QtWidgets.QLineEdit
    value_live_label: QtWidgets.QLabel
    value_stored_widget: QtWidgets.QWidget
    value_stored_placeholder: QtWidgets.QWidget
    refresh_button: QtWidgets.QToolButton

    tol_calc_label: QtWidgets.QLabel
    abs_tol_spinbox: QtWidgets.QDoubleSpinBox
    rel_tol_spinbox: QtWidgets.QDoubleSpinBox

    severity_combobox: QtWidgets.QComboBox
    status_combobox: QtWidgets.QComboBox

    timeout_spinbox: QtWidgets.QDoubleSpinBox

    open_rbv_button: QtWidgets.QPushButton
    rbv_pv_label: QtWidgets.QLabel

    data: Union[Parameter, Setpoint, Readback]

    def __init__(
        self,
        *args,
        client: Client,
        editable: bool = False,
        open_page_slot: Optional[Callable] = None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.client = client
        self.editable = editable
        self.open_page_slot = open_page_slot
        self.value_stored_widget = None
        self.setup_ui()

    def setup_ui(self):
        # initialize values
        self.pv_edit.setText(self.data.pv_name)
        self.pv_edit.textChanged.connect(self.update_pv_name)

        # update button?
        self.refresh_button.setToolTip('refresh edit details')
        self.refresh_button.setIcon(qta.icon('ei.refresh'))
        self.refresh_button.clicked.connect(self.update_live_value)
        self.update_live_value()

        try:
            self.bridge.data.data
        except AttributeError:
            self.value_stored_placeholder.hide()
        else:
            self.refresh_button.clicked.connect(self.update_stored_edit_widget)
            self.update_stored_edit_widget()

        try:
            self.bridge.status
        except AttributeError:
            self.ss_widget.hide()
        else:
            self.status_combobox.addItems([sta.name for sta in Status])
            self.severity_combobox.addItems([sta.name for sta in Severity])

            self.status_combobox.setCurrentIndex(self.data.status.value)
            self.severity_combobox.setCurrentIndex(self.data.severity.value)

        try:
            # dataclasses either have all tolerances or none
            self.bridge.abs_tolerance
        except AttributeError:
            self.tol_widget.hide()
        else:
            self.abs_tol_spinbox.setValue(self.data.abs_tolerance or 0.0)
            self.rel_tol_spinbox.setValue(self.data.rel_tolerance or 0.0)
            self.update_tol_calc()

            self.abs_tol_spinbox.valueChanged.connect(self.update_abs_tol)
            self.rel_tol_spinbox.valueChanged.connect(self.update_rel_tol)

        try:
            self.bridge.timeout
        except AttributeError:
            self.timeout_widget.hide()
        else:
            self.timeout_spinbox.setValue(self.data.timeout or 0.0)
            self.timeout_spinbox.valueChanged.connect(self.update_timeout)

        try:
            self.bridge.readback.pv_name
        except AttributeError:
            self.rbv_widget.hide()
        else:
            self.rbv_pv_label.setText(self.data.readback.pv_name)
            self.open_rbv_button.clicked.connect(self.open_rbv_page)

    def update_stored_edit_widget(self):
        e_data: EpicsData = self.client.cl.get(self.data.pv_name)
        new_widget = edit_widget_from_epics_data(e_data)

        if self.value_stored_widget:
            insert_widget(new_widget, self.value_stored_widget)
        else:
            insert_widget(new_widget, self.value_stored_placeholder)

    def update_live_value(self):
        e_data: EpicsData = self.client.cl.get(self.data.pv_name)
        self.value_live_label.setText(f"({str(e_data.data)})")

    def update_tol_calc(self):
        if not (hasattr(self.data, "data") and hasattr(self.data, "abs_tolerance")):
            self.tol_calc_label.hide()
            return

        edata: AnyEpicsType = self.data.data
        atol = self.data.abs_tolerance
        rtol = self.data.rel_tolerance

        if not (self.data and atol and rtol):
            self.tol_calc_label.setText("cannot calculate tolerances")
            return

        # tolerance calculated as in np.isclose
        total_tol = atol + rtol * abs(edata)

        self.tol_calc_label.setText(
            f"[{edata - total_tol}, {edata + total_tol}]"
        )

    def update_pv_name(self):
        if hasattr(self.data, "pv_name"):
            self.bridge.pv_name.put(self.pv_edit.text())

    def update_abs_tol(self, *args, **kwargs):
        if hasattr(self.data, "abs_tolerance"):
            self.bridge.abs_tolerance.put(self.abs_tol_spinbox.value())
            self.update_tol_calc()

    def update_rel_tol(self, *args, **kwargs):
        if hasattr(self.data, "rel_tolerance"):
            self.bridge.rel_tolerance.put(self.rel_tol_spinbox.value())
            self.update_tol_calc()

    def update_timeout(self, *args, **kwargs):
        if hasattr(self.data, "timeout"):
            self.bridge.timeout.put(self.timeout_spinbox.value())

    def open_rbv_page(self):
        if self.open_page_slot:
            self.open_page_slot(self.data.readback)


class ParameterPage(BaseParameterPage):
    data: Parameter


class SetpointPage(ParameterPage):
    data: Setpoint


class ReadbackPage(ParameterPage):
    data: Readback
