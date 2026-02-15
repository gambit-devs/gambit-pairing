"""A toggle button that displays a checkmark when checked."""


class CheckableButton(QtWidgets.QPushButton):
    """
    A toggle button that displays a checkmark when checked.

    Used for result selection buttons in the tournament pairings table.
    The checkmark is drawn in the top-right corner when the button is checked.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setCheckable(True)
        self.check_icon = get_colored_icon("checkmark-white.svg", "white", 12)
        self.setProperty("class", "ResultSelectorButton")

    def paintEvent(self, a0):
        """Custom paint event to draw checkmark on checked buttons."""
        super().paintEvent(a0)
        if self.isChecked():
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

            rect = self.rect()
            # Move checkmark further left for White win and Draw to avoid clipping
            if self.text() in ["1-0", "½-½"]:
                offset = 20
            else:
                offset = 18
            checkmark_rect = QtCore.QRect(rect.right() - offset, rect.top() + 2, 12, 12)
            if not self.check_icon.isNull():
                self.check_icon.paint(painter, checkmark_rect)
            else:
                # Fallback
                painter.setPen(QtGui.QPen(QtGui.QColor("white"), 2))
                font = QtGui.QFont(painter.font())
                font.setPointSize(10)
                font.setBold(True)
                painter.setFont(font)
                painter.drawText(checkmark_rect, Qt.AlignmentFlag.AlignCenter, "✓")
