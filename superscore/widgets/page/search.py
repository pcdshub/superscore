"""Search page"""

import logging
from typing import Any, Dict, List

from dateutil import tz
from qtpy import QtCore, QtWidgets

from superscore.client import Client
from superscore.model import Collection, Readback, Setpoint, Snapshot
from superscore.widgets.core import Display

logger = logging.getLogger(__name__)


class SearchPage(Display, QtWidgets.QWidget):
    filename = 'search_page.ui'

    # Left splitter, filter options select
    name_line_edit: QtWidgets.QLineEdit
    snapshot_checkbox: QtWidgets.QCheckBox
    collection_checkbox: QtWidgets.QCheckBox
    setpoint_checkbox: QtWidgets.QCheckBox
    readback_checkbox: QtWidgets.QCheckBox
    pv_line_edit: QtWidgets.QLineEdit
    desc_line_edit: QtWidgets.QLineEdit
    start_dt_edit: QtWidgets.QDateTimeEdit
    end_dt_edit: QtWidgets.QDateTimeEdit

    apply_filter_button: QtWidgets.QPushButton

    # Right splitter, filter results view
    name_subfilter_line_edit: QtWidgets.QLineEdit
    query_details_label: QtWidgets.QLabel
    save_filter_button: QtWidgets.QPushButton
    help_button: QtWidgets.QPushButton  # maybe a toolbutton for widget pop-out

    filter_table_view: QtWidgets.QTableView
    results_table_view: QtWidgets.QTableView

    def __init__(self, *args, client: Client, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.client = client

        self.type_checkboxes: List[QtWidgets.QCheckBox] = [
            self.snapshot_checkbox, self.collection_checkbox,
            self.setpoint_checkbox, self.readback_checkbox,
        ]
        self.setup_ui()

    def setup_ui(self) -> None:
        self.start_dt_edit.setDate(QtCore.QDate.currentDate().addDays(-365))
        self.end_dt_edit.setDate(QtCore.QDate.currentDate())
        self.apply_filter_button.clicked.connect(self._gather_search_terms)

    def _gather_search_terms(self) -> Dict[str, Any]:
        search_kwargs = {}

        # type
        entry_type_list = []
        for checkbox, entry_type in zip(
            self.type_checkboxes,
            (Snapshot, Collection, Setpoint, Readback)
        ):
            if checkbox.isChecked():
                entry_type_list.append(entry_type)

        if entry_type_list:
            search_kwargs["entry_type"] = tuple(entry_type_list)

        # name
        name = self.name_line_edit.text()
        if name:
            search_kwargs['title'] = tuple(n.strip() for n in name.split(','))

        # description
        desc = self.desc_line_edit.text()
        if desc:
            search_kwargs['description'] = desc

        # TODO: sort out PVs
        pvs = self.pv_line_edit.text()
        if pvs:
            search_kwargs['pvs'] = tuple(pv.strip() for pv in pvs.split(','))

        # time
        start_dt = self.start_dt_edit.dateTime().toPyDateTime()
        search_kwargs['start_time'] = start_dt.astimezone(tz.UTC)
        end_dt = self.end_dt_edit.dateTime().toPyDateTime()
        search_kwargs['end_time'] = end_dt.astimezone(tz.UTC)

        logger.debug(f'gathered search terms: {search_kwargs}')
        return search_kwargs
