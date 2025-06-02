from logging import getLogger
from uuid import UUID

from qtpy import QtWidgets
from qtpy.QtGui import QCloseEvent

from superscore.widgets.pv_table import PVTableModel

logger = getLogger(__name__)


class Page(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)
        self.pv_table_models: dict[UUID: PVTableModel] = {}

    def closeEvent(self, a0: QCloseEvent) -> None:
        for model in self.pv_table_models.values():
            try:
                model.close()
            except AttributeError:
                logger.warning(f"Model {model} does not have a close method.")
        super().closeEvent(a0)
