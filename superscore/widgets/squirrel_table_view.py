from qtpy import QtCore, QtWidgets


class SquirrelTableView(QtWidgets.QTableView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setShowGrid(False)
        self.verticalHeader().hide()
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MiddleButton:
            self.copy_address(self.indexAt(event.position().toPoint()))
        else:
            super().mousePressEvent(event)

    def copy_address(self, index):
        text = self.model().data(index, QtCore.Qt.ToolTipRole)
        clipboard = QtWidgets.QApplication.clipboard()
        if clipboard.supportsSelection():
            mode = clipboard.Selection
        else:
            mode = clipboard.Clipboard
        clipboard.setText(text, mode=mode)
