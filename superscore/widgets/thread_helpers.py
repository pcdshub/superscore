from typing import ClassVar

from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtCore import QEvent


def set_wait_cursor():
    app = QtWidgets.QApplication.instance()
    app.setOverrideCursor(QtGui.QCursor(QtCore.Qt.WaitCursor))


def reset_cursor():
    app = QtWidgets.QApplication.instance()
    app.restoreOverrideCursor()


def busy_cursor(func):
    """
    Decorator for making the cursor busy while a function is running
    Will run in the GUI thread, therefore blocking GUI interaction
    """
    def wrapper(*args, **kwargs):
        set_wait_cursor()
        try:
            func(*args, **kwargs)
        finally:
            reset_cursor()

    return wrapper


class IgnoreInteractionFilter(QtCore.QObject):
    interaction_events = (
        QEvent.KeyPress, QEvent.KeyRelease, QEvent.MouseButtonPress,
        QEvent.MouseButtonRelease, QEvent.MouseButtonDblClick
    )

    def eventFilter(self, a0: QtCore.QObject, a1: QEvent) -> bool:
        """ignore all interaction events while this filter is installed"""
        if a1.type() in self.interaction_events:
            return True
        else:
            return super().eventFilter(a0, a1)


FILTER = IgnoreInteractionFilter()


class BusyCursorThread(QtCore.QThread):
    """
    Thread to switch the cursor while a task is running.  Pushes the task to a
    thread, allowing GUI interaction in the main thread.

    To use, you should initialize this thread with the function/slot you want to
    run in the thread.  Note the .start method used to kick off this thread must
    be wrapped in a function in order to run... for some reason...

    ``` python
    busy_thread = BusyCursorThread(func=slot_to_run)

    def run_thread():
        busy_thread.start()

    button.clicked.connect(run_thread)
    ```
    """
    task_finished: ClassVar[QtCore.Signal] = QtCore.Signal()
    task_starting: ClassVar[QtCore.Signal] = QtCore.Signal()
    raised_exception: ClassVar[QtCore.Signal] = QtCore.Signal(Exception)

    def __init__(self, *args, func, ignore_events: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = None
        self.func = func
        self.ignore_events = ignore_events
        self.task_starting.connect(self.set_cursor_busy)
        self.task_finished.connect(self.reset_cursor)

    def run(self) -> None:
        # called from .start().  if called directly, will block current thread
        self.task_starting.emit()
        # run the attached method
        try:
            self.func()
        except Exception as ex:
            self.raised_exception.emit(ex)
        finally:
            self.task_finished.emit()

    def set_cursor_busy(self):
        set_wait_cursor()
        if self.ignore_events:
            self.app = QtWidgets.QApplication.instance()
            self.app.installEventFilter(FILTER)

    def reset_cursor(self):
        reset_cursor()
        if self.ignore_events:
            self.app = QtWidgets.QApplication.instance()
            self.app.removeEventFilter(FILTER)
