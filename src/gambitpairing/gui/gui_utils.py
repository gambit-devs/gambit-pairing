"""Utilities for managing the GUI."""

from collections.abc import Callable

from PyQt6 import QtCore, QtGui, QtWidgets


def get_native_icon(
    theme_name: str, fallback: QtWidgets.QStyle.StandardPixmap
) -> QtGui.QIcon:
    """Get a theme icon with a fallback supplied by the active Qt style.

    A bundled Python Qt runtime may not have access to the desktop icon theme,
    while the active style still knows how to draw standard application icons.
    This keeps actions legible without adding application-specific styling.
    """
    icon = QtGui.QIcon.fromTheme(theme_name)
    if not icon.isNull():
        return icon

    app = QtWidgets.QApplication.instance()
    if app is not None:
        return app.style().standardIcon(fallback)

    return QtGui.QIcon()


def set_native_icon(
    label: QtWidgets.QLabel,
    theme_name: str,
    fallback: QtWidgets.QStyle.StandardPixmap = QtWidgets.QStyle.StandardPixmap.SP_FileIcon,
    size: int | None = None,
) -> None:
    """Show a platform/theme icon in a label using the active Qt metrics."""
    icon = get_native_icon(theme_name, fallback)
    if icon.isNull():
        return
    if size is None:
        size = label.style().pixelMetric(
            QtWidgets.QStyle.PixelMetric.PM_LargeIconSize, None, label
        )
    pixmap = icon.pixmap(QtCore.QSize(size, size))
    if not pixmap.isNull():
        label.setPixmap(pixmap)
        label.setText("")


def set_native_heading(label: QtWidgets.QLabel) -> None:
    """Use the platform's title font for a section heading."""
    label.setFont(
        QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.TitleFont)
    )


def create_action(
    self, text: str, slot: Callable, shortcut: str = "", tooltip: str = ""
) -> QtGui.QAction:
    """Create and configure a QAction.

    Parameters
    ----------
    text : str
        The text to display for the action.
    slot : callable
        The function to call when the action is triggered.
    shortcut : str, optional
        Optional keyboard shortcut (e.g., "Ctrl+N"),
        must be understood by QtGui.QKeySequence
    tooltip : str, optional
        Optional tooltip to show on hover. The default is ""

    Returns
    -------
        The configured QAction.
    """
    action = QtGui.QAction(text, self)
    action.triggered.connect(slot)
    if shortcut:
        action.setShortcut(QtGui.QKeySequence(shortcut))
    if tooltip:
        action.setToolTip(tooltip)
        action.setStatusTip(tooltip)
    return action
