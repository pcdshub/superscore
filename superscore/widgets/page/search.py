"""Search page"""

import logging
from typing import Any, Callable, Dict, List, Optional

import qtawesome as qta
from dateutil import tz
from qtpy import QtCore, QtWidgets

from superscore.client import Client
from superscore.model import Collection, Entry, Readback, Setpoint, Snapshot
from superscore.widgets.core import Display
from superscore.widgets.page import ICON_MAP

logger = logging.getLogger(__name__)


class SearchPage(Display, QtWidgets.QWidget):
    """
    Widget for searching and displaying Entry's.  Contains a variety of filter
    option input widgets, a sortable table view, and a filter management table.

    TODO: Implement filters (saving/loading)
    TODO: string-ified search query
    TODO: integration with global tree-view
    """
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

    def __init__(
        self,
        *args,
        client: Client,
        open_page_slot: Optional[Callable] = None,
        **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        self.client = client
        self.open_page_slot = open_page_slot
        self.model: Optional[ResultModel] = None

        self.type_checkboxes: List[QtWidgets.QCheckBox] = [
            self.snapshot_checkbox, self.collection_checkbox,
            self.setpoint_checkbox, self.readback_checkbox,
        ]
        self.setup_ui()

    def setup_ui(self) -> None:
        # set up filter option widgets
        self.start_dt_edit.setDate(QtCore.QDate.currentDate().addDays(-365))
        self.end_dt_edit.setDate(QtCore.QDate.currentDate())
        self.apply_filter_button.clicked.connect(self.show_current_filter)

        self.collection_checkbox.setIcon(qta.icon(ICON_MAP[Collection]))
        self.snapshot_checkbox.setIcon(qta.icon(ICON_MAP[Snapshot]))
        self.setpoint_checkbox.setIcon(qta.icon(ICON_MAP[Setpoint]))
        self.readback_checkbox.setIcon(qta.icon(ICON_MAP[Readback]))

        # set up filter table view
        self.model = ResultModel(entries=[])
        self.proxy_model = ResultFilterProxyModel(open_page_slot=self.open_page_slot)
        self.proxy_model.setSourceModel(self.model)
        self.results_table_view.setModel(self.proxy_model)
        self.results_table_view.setSortingEnabled(True)
        horiz_header = self.results_table_view.horizontalHeader()
        horiz_header.setSectionResizeMode(horiz_header.Interactive)

        self.open_delegate = ButtonDelegate(button_text='open me')
        del_col = len(ResultModel.headers) - 1
        self.results_table_view.setItemDelegateForColumn(del_col, self.open_delegate)
        self.open_delegate.clicked.connect(self.proxy_model.open_row)

        self.name_subfilter_line_edit.textChanged.connect(self.subfilter_results)

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

    def show_current_filter(self) -> None:
        """
        Gather filter options and update source model with valid entries
        """
        # gather filter details
        search_kwargs = self._gather_search_terms()
        entries = self.client.search(**search_kwargs)

        # update source table model
        self.model.modelAboutToBeReset.emit()
        self.model.entries = list(entries)
        self.model.modelReset.emit()

    def subfilter_results(self) -> None:
        """Filter the table once more by name"""
        self.proxy_model.name_regexp.setPattern(self.name_subfilter_line_edit.text())
        self.proxy_model.invalidateFilter()


class ResultModel(QtCore.QAbstractTableModel):
    headers: List[str] = ['Name', 'Type', 'Description', 'Created', 'Open']

    def __init__(self, *args, entries: List[Entry] = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.entries: List[Entry] = entries or []

    def data(self, index: QtCore.QModelIndex, role: int) -> Any:
        """
        Returns the data stored under the given role for the item
        referred to by the index.

        Parameters
        ----------
        index : QtCore.QModelIndex
            An index referring to a cell of the TableView
        role : int
            The requested data role.

        Returns
        -------
        Any
            the requested data
        """
        entry: Entry = self.entries[index.row()]

        # Special handling for open button delegate
        if index.column() == (len(self.headers) - 1):
            if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
                return 'open'

        if role != QtCore.Qt.DisplayRole:
            # table is read only
            return QtCore.QVariant()

        if index.column() == 0:  # name column
            name_text = getattr(entry, 'title', getattr(entry, 'pv_name', '<N/A>'))
            return name_text
        elif index.column() == 1:  # Type
            return type(entry).__name__
        elif index.column() == 2:  # Description
            return getattr(entry, 'description', '<no desc>')
        elif index.column() == 3:  # Creation time
            return entry.creation_time.strftime('%Y/%m/%d %H:%M')

        # if nothing is found, return invalid QVariant
        return QtCore.QVariant()

    def rowCount(self, index):
        return len(self.entries)

    def columnCount(self, index):
        return len(self.headers)

    def headerData(
        self,
        section: int,
        orientation: QtCore.Qt.Orientation,
        role: int
    ) -> Any:
        """
        Returns the header data for the model.
        Currently only displays horizontal header data
        """
        if role != QtCore.Qt.DisplayRole:
            return

        if orientation == QtCore.Qt.Horizontal:
            return self.headers[section]

    def flags(self, index: QtCore.QModelIndex) -> QtCore.Qt.ItemFlag:
        """
        Returns the item flags for the given ``index``.  The returned
        item flag controls what behaviors the item supports.

        Parameters
        ----------
        index : QtCore.QModelIndex
            the index referring to a cell of the TableView

        Returns
        -------
        QtCore.Qt.ItemFlag
            the ItemFlag corresponding to the cell
        """
        if (index.column() == len(self.headers) - 1):
            return QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled
        else:
            return QtCore.Qt.ItemIsEnabled


class ButtonDelegate(QtWidgets.QStyledItemDelegate):
    clicked = QtCore.Signal(QtCore.QModelIndex)

    def __init__(self, *args, button_text: str = '', **kwargs):
        self.button_text = button_text
        super().__init__(*args, **kwargs)

    def createEditor(
        self,
        parent: QtWidgets.QWidget,
        option,
        index: QtCore.QModelIndex
    ) -> QtWidgets.QWidget:
        button = QtWidgets.QPushButton(self.button_text, parent)
        button.clicked.connect(
            lambda _, index=index: self.clicked.emit(index)
        )
        return button

    def updateEditorGeometry(
        self,
        editor: QtWidgets.QWidget,
        option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex
    ) -> None:
        return editor.setGeometry(option.rect)


class ResultFilterProxyModel(QtCore.QSortFilterProxyModel):
    """
    Filter proxy model specifically for ResultModel.  Enables per-column sorting
    and filtering table contents by name.
    """

    name_regexp: QtCore.QRegularExpression
    sourceModel: ResultModel

    def __init__(
        self,
        *args,
        open_page_slot: Optional[Callable] = None,
        **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        self.open_page_slot = open_page_slot
        self.name_regexp = QtCore.QRegularExpression()

    def filterAcceptsRow(
        self,
        source_row: int,
        source_parent: QtCore.QModelIndex
    ) -> bool:
        name_ok = True

        name_index = self.sourceModel().index(source_row, 0, source_parent)
        name = self.sourceModel().data(name_index, QtCore.Qt.DisplayRole)
        name_ok = self.name_regexp.match(name).hasMatch()

        return name_ok

    def open_row(self, proxy_index: QtCore.QModelIndex) -> None:
        """opens page for entry data at ``row`` (in proxy model)"""
        if self.open_page_slot is not None:
            source_row = self.mapToSource(proxy_index)
            logger.debug(f'Open page button for row: {proxy_index.row()}')
            self.open_page_slot(self.sourceModel().entries[source_row.row()])
