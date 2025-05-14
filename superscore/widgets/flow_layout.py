from qtpy import QtCore, QtWidgets


class FlowLayout(QtWidgets.QLayout):
    """
    A custom layout that arranges child widgets in a flowing manner.

    Widgets are placed horizontally until there is no more space, then the layout
    wraps them to the next line. This layout is useful for creating a tag cloud,
    button groups, or any interface where items should wrap automatically.
    """
    def __init__(self, margin=0, spacing=-1, **kwargs):
        """
        Initialize the FlowLayout.

        Parameters
        ----------
        parent : QWidget, optional
            The parent widget for this layout. Default is None.
        margin : int, optional
            The margin to apply around the layout. Default is 0.
        spacing : int, optional
            The spacing between items. Default is -1, which means use the default spacing.
        """
        super().__init__(**kwargs)
        if self.parent() is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self.itemList = []

    def addItem(self, item: QtWidgets.QLayoutItem) -> None:
        """
        Add an item to the layout.

        Parameters
        ----------
        item : QLayoutItem
            The layout item to add.
        """
        self.itemList.append(item)

    def count(self) -> int:
        """
        Return the number of items in the layout.

        Returns
        -------
        int
            The count of items currently in the layout.
        """
        return len(self.itemList)

    def itemAt(self, index: int) -> QtWidgets.QLayoutItem:
        """
        Return the layout item at the given index.

        Parameters
        ----------
        index : int
            The index of the item.

        Returns
        -------
        QLayoutItem or None
            The layout item if index is valid; otherwise, None.
        """
        if 0 <= index < len(self.itemList):
            return self.itemList[index]
        return None

    def takeAt(self, index: int) -> QtWidgets.QLayoutItem:
        """
        Remove and return the layout item at the given index.

        Parameters
        ----------
        index : int
            The index of the item to remove.

        Returns
        -------
        QLayoutItem or None
            The removed layout item if index is valid; otherwise, None.
        """
        if 0 <= index < len(self.itemList):
            return self.itemList.pop(index)
        return None

    def expandingDirections(self) -> QtCore.Qt.Orientations:
        """
        Specify the directions in which the layout can expand.

        Returns
        -------
        Qt.Orientations
            A combination of Qt.Horizontal and Qt.Vertical indicating that the layout can expand in both directions.
        """
        return QtCore.Qt.Horizontal | QtCore.Qt.Vertical

    def hasHeightForWidth(self) -> bool:
        """
        Indicate that this layout has a height-for-width dependency.

        Returns
        -------
        bool
            True, since the layout's height depends on its width.
        """
        return True

    def heightForWidth(self, width: int) -> int:
        """
        Calculate the height of the layout given a specific width.

        Parameters
        ----------
        width : int
            The width to calculate the height for.

        Returns
        -------
        int
            The computed height based on the layout of items.
        """
        return self.doLayout(QtCore.QRect(0, 0, width, 0), True)

    def setGeometry(self, rect: QtCore.QRect) -> None:
        """
        Set the geometry of the layout and position the child items.

        Parameters
        ----------
        rect : QRect
            The rectangle that defines the area available for the layout.
        """
        super().setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self) -> QtCore.QSize:
        """
        Provide a recommended size for the layout.

        Returns
        -------
        QSize
            The recommended size, based on the minimum size of the items.
        """
        return self.minimumSize()

    def minimumSize(self) -> QtCore.QSize:
        """
        Calculate the minimum size required by the layout.

        Returns
        -------
        QSize
            The minimum size that can contain all layout items with margins.
        """
        size = QtCore.QSize()
        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QtCore.QSize(margins.left() + margins.right(),
                             margins.top() + margins.bottom())
        return size

    def doLayout(self, rect: QtCore.QRect, testOnly: bool) -> int:
        """
        Layout the items within the given rectangle.

        Items are arranged horizontally until there is no more space, then they wrap
        to the next line. This method is used both for setting the geometry and for
        calculating the required height.

        Parameters
        ----------
        rect : QRect
            The rectangle within which to layout the items.
        testOnly : bool
            If True, the layout is calculated but item geometries are not set.

        Returns
        -------
        int
            The total height required by the layout.
        """
        x = rect.x()
        y = rect.y()
        lineHeight = 0

        for item in self.itemList:
            widget = item.widget()
            spaceX = self.spacing() + widget.style().layoutSpacing(
                QtWidgets.QSizePolicy.PushButton, QtWidgets.QSizePolicy.PushButton, QtCore.Qt.Horizontal)
            spaceY = self.spacing() + widget.style().layoutSpacing(
                QtWidgets.QSizePolicy.PushButton, QtWidgets.QSizePolicy.PushButton, QtCore.Qt.Vertical)
            nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > rect.right() and lineHeight > 0:
                x = rect.x()
                y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0
            if not testOnly:
                item.setGeometry(QtCore.QRect(QtCore.QPoint(x, y), item.sizeHint()))
            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())
        return y + lineHeight - rect.y()
