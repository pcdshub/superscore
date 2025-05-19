from qtpy import QtWidgets
from qtpy.QtGui import QCloseEvent


class Page(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self.live_models = set()

    def closeEvent(self, a0: QCloseEvent) -> None:
        for model in self.live_models:
            try:
                model.close()
            except AttributeError:
                continue
        super().closeEvent(a0)
