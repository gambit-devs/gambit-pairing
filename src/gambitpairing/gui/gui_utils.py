"""Utilities for managing the GUI."""

from PyQt6 import QtGui, QtWidgets
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QCursor
from PyQt6.QtCore import Qt

from gambitpairing.resources.resource_utils import get_resource_path


def set_svg_icon(
    label: QtWidgets.QLabel, icon_name: str, color: str = "#2d5a27", size: int = 24
):
    """Help set an SVG icon on a QLabel with color overlay."""
    icon_path = get_resource_path(icon_name, "icons")
    # Use QIcon to load SVG and generate pixmap at desired size
    icon = QtGui.QIcon(str(icon_path))
    pixmap = icon.pixmap(size, size)

    if not pixmap.isNull():
        # Apply color overlay
        painter = QtGui.QPainter(pixmap)
        painter.setCompositionMode(
            QtGui.QPainter.CompositionMode.CompositionMode_SourceIn
        )
        painter.fillRect(pixmap.rect(), QtGui.QColor(color))
        painter.end()
        label.setPixmap(pixmap)
        label.setText("")


def get_colored_icon(
    icon_name: str, color: str = "#2d5a27", size: int = 24
) -> QtGui.QIcon:
    """Help getting a colored QIcon from SVG."""
    icon_path = get_resource_path(icon_name, "icons")
    pixmap = QtGui.QPixmap(str(icon_path))
    if not pixmap.isNull():
        pixmap = pixmap.scaled(
            size,
            size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        painter = QtGui.QPainter(pixmap)
        painter.setCompositionMode(
            QtGui.QPainter.CompositionMode.CompositionMode_SourceIn
        )
        painter.fillRect(pixmap.rect(), QtGui.QColor(color))
        painter.end()
        return QtGui.QIcon(pixmap)
    return QtGui.QIcon()


def update_widget_style(widget: QWidget) -> None:
    """Change the style on a widget."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def reset_and_set_cursor(cursor_shape: Qt.CursorShape):
    """Remove all override cursors and set a new one."""
    # Remove all existing override cursors
    while QApplication.overrideCursor() is not None:
        QApplication.restoreOverrideCursor()

    # Set new override cursor
    QApplication.setOverrideCursor(QCursor(cursor_shape))
