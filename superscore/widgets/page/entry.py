"""
Widgets for visualizing and editing core model dataclasses
"""
import logging
from copy import deepcopy
from typing import Optional, Union
from uuid import UUID

import qtawesome as qta
from qtpy import QtWidgets
from qtpy.QtGui import QCloseEvent

from superscore.control_layers._base_shim import EpicsData
from superscore.errors import EntryNotFoundError
from superscore.model import (Collection, Nestable, Parameter, Readback,
                              Setpoint, Severity, Snapshot, Status)
from superscore.type_hints import AnyEpicsType
from superscore.widgets.core import (DataWidget, Display, NameDescTagsWidget,
                                     WindowLinker)
from superscore.widgets.manip_helpers import (insert_widget,
                                              match_line_edit_text_width)
from superscore.widgets.thread_helpers import BusyCursorThread
from superscore.widgets.views import (LivePVTableView, NestableTableView,
                                      RootTreeView,
                                      edit_widget_from_epics_data)

logger = logging.getLogger(__name__)


class NestablePage(Display, DataWidget, WindowLinker):
    filename = 'nestable_page.ui'

    meta_placeholder: QtWidgets.QWidget
    meta_widget: NameDescTagsWidget
    tree_view: RootTreeView
    sub_coll_table_view: NestableTableView
    sub_pv_table_view: LivePVTableView

    save_button: QtWidgets.QPushButton
    snapshot_button: QtWidgets.QPushButton

    data: Nestable

    def __init__(
        self,
        *args,
        data: Nestable,
        editable: bool = False,
        **kwargs
    ):
        super().__init__(*args, data=data, **kwargs)
        self.editable = editable
        self._last_data = deepcopy(self.data)
        self.setup_ui()

    def setup_ui(self):
        self.meta_widget = NameDescTagsWidget(data=self.data)
        insert_widget(self.meta_widget, self.meta_placeholder)

        # show tree view
        self.tree_view.client = self.client
        self.tree_view.set_data(self.data)

        self.sub_pv_table_view.client = self.client
        self.sub_pv_table_view.set_data(self.data)
        self.sub_pv_table_view.data_updated.connect(self.track_changes)

        self.sub_coll_table_view.client = self.client
        self.sub_coll_table_view.set_data(self.data)
        self.sub_coll_table_view.data_updated.connect(self.track_changes)

        self.save_button.clicked.connect(self.save)
        self.snapshot_button.clicked.connect(self.take_snapshot)
        self.snapshot_button.setText("Take new Snapshot")

        self.set_editable(self.editable)

    def set_editable(self, editable: bool) -> None:
        for col in self.sub_pv_table_view._model.header_enum:
            self.sub_pv_table_view.set_editable(col, editable)

        for col in self.sub_coll_table_view._model.header_enum:
            self.sub_coll_table_view.set_editable(col, editable)

        if editable:
            self.save_button.show()
        else:
            self.save_button.hide()

        self.editable = editable

    def save(self):
        self.client.save(self.data)
        self._last_data = deepcopy(self.data)

    def track_changes(self):
        if not self.data == self._last_data:
            self.save_button.setText("Save *")
            self.save_button.setEnabled(True)
        else:
            self.save_button.setText("Save")
            self.save_button.setEnabled(False)

    def closeEvent(self, a0: QCloseEvent) -> None:
        logger.debug(f"Stopping polling threads for {type(self.data)}")
        self.sub_pv_table_view._model.stop_polling(wait_time=5000)
        return super().closeEvent(a0)

    def take_snapshot(self) -> None:
        # TODO: if data dirty, abort
        entry = self.data
        if isinstance(entry, Snapshot):
            origin = entry.origin_collection
            if origin is None:
                logging.error("The original collection is unknown: cannot save snapshot")
                return
            elif isinstance(origin, UUID):
                try:
                    entry = self.client.backend.get_entry(origin)
                except EntryNotFoundError:
                    logging.error("The original collection does not exist: cannot save snapshot")
                    return
            else:
                entry = origin
        window = self.get_window()

        snapshot = self.client.snap(entry)
        self.client.save(snapshot)
        self.refresh_window()
        window.open_restore_page(snapshot=snapshot)
        return


class CollectionPage(NestablePage):
    data: Collection


class SnapshotPage(NestablePage):
    data: Snapshot


class BaseParameterPage(Display, DataWidget, WindowLinker):
    filename = 'parameter_page.ui'

    meta_placeholder: QtWidgets.QWidget
    meta_widget: NameDescTagsWidget

    # Container widgets
    pv_value_widget: QtWidgets.QWidget
    options_hlayout: QtWidgets.QHBoxLayout
    tol_widget: QtWidgets.QWidget
    tol_form_layout: QtWidgets.QFormLayout
    ss_widget: QtWidgets.QWidget
    ss_form_layout: QtWidgets.QFormLayout
    timeout_widget: QtWidgets.QWidget
    timeout_form_layout: QtWidgets.QFormLayout
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

    save_button: QtWidgets.QPushButton

    _edata_thread: Optional[BusyCursorThread]
    data: Union[Parameter, Setpoint, Readback]

    def __init__(
        self,
        *args,
        editable: bool = False,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.editable = editable
        self.value_stored_widget = None
        self.edata = None
        self._edata_thread: Optional[BusyCursorThread] = None
        self._last_data = deepcopy(self.data)
        self.setup_ui()

    def setup_ui(self):
        # initialize values
        self.pv_edit.setText(self.data.pv_name)
        self.pv_edit.textChanged.connect(self.update_pv_name)
        self.update_pv_name(self.data.pv_name)

        # setup data thread
        self._edata_thread = BusyCursorThread(func=self._get_edata)

        self._edata_thread.finished.connect(self.update_stored_edit_widget)
        self._edata_thread.finished.connect(self.update_live_value)

        self.refresh_button.setToolTip('refresh edit details')
        self.refresh_button.setIcon(qta.icon('ei.refresh'))
        self.refresh_button.clicked.connect(self.get_edata)
        self.get_edata()

        self.save_button.clicked.connect(self.save)

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
            self.bridge.readback
        except AttributeError:
            self.rbv_widget.hide()
        else:
            self.setup_rbv_widget()

        self.track_changes()
        self.set_editable(self.editable)

    def get_edata(self) -> None:
        if self._edata_thread and self._edata_thread.isRunning():
            return

        self._edata_thread.start()

    def _get_edata(self):
        self.edata = self.client.cl.get(self.data.pv_name)

    def set_editable(self, editable: bool) -> None:
        self.pv_edit.setReadOnly(not editable)
        if self.value_stored_widget is not None:
            self.value_stored_widget.setEnabled(editable)

        for form_layout in (self.ss_form_layout, self.tol_form_layout,
                            self.timeout_form_layout):
            for i in range(form_layout.rowCount()):
                item = form_layout.itemAt(i, QtWidgets.QFormLayout.FieldRole)

                # designer can sometimes sneak blank rows or start at i=1
                if item is not None:
                    item.widget().setEnabled(editable)

        self.open_rbv_button.setEnabled(editable)

        if editable:
            self.save_button.show()
        else:
            self.save_button.hide()

        self.editable = editable

    def update_stored_edit_widget(self):
        data = self.edata
        if not isinstance(data, EpicsData):
            new_widget = QtWidgets.QToolButton()
            new_widget.setIcon(qta.icon("msc.debug-disconnect"))
            new_widget.setEnabled(False)
            new_widget.setSizePolicy(
                QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum
            )
        else:
            new_widget = edit_widget_from_epics_data(data)

        insert_widget(new_widget, self.value_stored_placeholder)
        self.value_stored_widget = new_widget

        # update edit status in case new widgets created
        self.set_editable(self.editable)

    def update_live_value(self):
        data = self.edata
        if not isinstance(data, EpicsData):
            self.value_live_label.setText("(-)")
        else:
            self.value_live_label.setText(f"({str(data.data)})")

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

    def update_pv_name(self, text: str):
        if hasattr(self.data, "pv_name"):
            self.bridge.pv_name.put(text)

        match_line_edit_text_width(self.pv_edit, text=text)

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

    def open_rbv_page(self) -> DataWidget:
        if self.open_page_slot:
            widget = self.open_page_slot(self.data.readback)
            widget.bridge.pv_name.changed_value.connect(self.rbv_pv_label.setText)

    def create_rbv(self):
        new_rbv = Readback(pv_name='<MY:PV>')
        self.bridge.readback.put(new_rbv)
        self.open_rbv_page()

    def setup_rbv_widget(self):
        if self.data.readback is None:
            # Setup create-new button
            self.rbv_pv_label.setText("[None]")
            self.open_rbv_button.clicked.connect(self.create_rbv)
        else:
            self.rbv_pv_label.setText(self.data.readback.pv_name)
            self.open_rbv_button.clicked.connect(self.open_rbv_page)

    def save(self):
        self.client.save(self.data)
        self._last_data = deepcopy(self.data)

    def track_changes(self):
        if not self.data == self._last_data:
            self.save_button.setText("Save *")
            self.save_button.setEnabled(True)
        else:
            self.save_button.setText("Save")
            self.save_button.setEnabled(False)


class ParameterPage(BaseParameterPage):
    data: Parameter


class SetpointPage(BaseParameterPage):
    data: Setpoint


class ReadbackPage(BaseParameterPage):
    data: Readback
