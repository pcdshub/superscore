"""
Enhanced widgets.  Widgets that subclass standard qt widgets and add functionality
"""
from qtpy import QtCore, QtWidgets


class FilterComboBox(QtWidgets.QComboBox):
    """
    ComboBox with the LineEdit enabled with autocomplete and option filtering
    Adapted from https://stackoverflow.com/a/50639066
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setEditable(True)

        # add a filter model to filter matching items
        self.filter_model = QtCore.QSortFilterProxyModel(self)
        self.filter_model.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.filter_model.setSourceModel(self.model())

        # add a completer, which uses the filter model
        self.setCompleter(QtWidgets.QCompleter(self.filter_model, self))
        # always show all (filtered) completions
        self.completer().setCompletionMode(QtWidgets.QCompleter.UnfilteredPopupCompletion)

        # connect signals
        self.lineEdit().textEdited.connect(self.filter_model.setFilterFixedString)
        self.completer().activated.connect(self.on_completer_activated)

    def on_completer_activated(self, text):
        """
        on selection of an item from the completer, select the corresponding item
        """
        if text:
            index = self.findText(text)
            self.setCurrentIndex(index)
            self.activated[str].emit(self.itemText(index))

    def setModel(self, model):
        """
        on model change, update the models of the filter and completer as well
        """
        super().setModel(model)
        self.filter_model.setSourceModel(model)
        self.completer().setModel(self.filter_model)

    def setModelColumn(self, column):
        """
        on model column change, update the model column of the filter and completer
        """
        self.completer().setCompletionColumn(column)
        self.filter_model.setFilterKeyColumn(column)
        super().setModelColumn(column)
