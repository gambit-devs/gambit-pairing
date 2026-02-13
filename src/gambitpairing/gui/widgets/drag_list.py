"""Contains Drag list widget class."""

# Gambit Pairing
# Copyright (C) 2025  Gambit Pairing developers
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from typing import Any, Optional

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import QMimeData, Qt
from PyQt6.QtGui import (
    QDrag,
    QDragEnterEvent,
    QDragLeaveEvent,
    QDragMoveEvent,
    QDropEvent,
    QMouseEvent,
)


class DragListWidget(QtWidgets.QListWidget):
    """QListWidget subclass that implements drag-and-drop and click-to-place functionality for managing tournament players."""

    parent_dialog: Any
    selected_player: Optional["Player"]

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self.parent_dialog: Any = parent
        self.selected_player: Optional["Player"] = None

        self.setAcceptDrops(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)

    def startDrag(self, supported_actions: Qt.DropActions) -> None:
        """Start drag operation from player pool."""
        current_item: Optional[QtWidgets.QListWidgetItem] = self.currentItem()
        if not current_item:
            return

        player: Optional["Player"] = current_item.data(Qt.ItemDataRole.UserRole)
        if not player:
            return

        if not player.is_active:
            QtWidgets.QToolTip.showText(
                QtGui.QCursor.pos(),
                "Withdrawn players cannot be paired. Right-click to reactivate.",
                self,
                QtCore.QRect(),
                2000,
            )
            return

        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(f"player:{player.id}")
        drag.setMimeData(mime_data)

        pixmap = QtGui.QPixmap(250, 35)
        pixmap.fill(QtGui.QColor(255, 255, 255, 200))

        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        painter.setPen(QtGui.QPen(QtGui.QColor(33, 150, 243), 2))
        painter.setBrush(QtGui.QBrush(QtGui.QColor(227, 242, 253, 180)))
        painter.drawRoundedRect(1, 1, 248, 33, 4, 4)

        painter.setPen(QtGui.QColor(0, 0, 0))
        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)

        painter.drawText(
            pixmap.rect(),
            Qt.AlignmentFlag.AlignCenter,
            f"{player.name} ({player.rating})",
        )
        painter.end()

        drag.setPixmap(pixmap)
        drag.setHotSpot(QtCore.QPoint(125, 17))

        drag.exec(supported_actions)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press for click-to-select functionality."""
        super().mousePressEvent(event)

        if event.button() == Qt.MouseButton.LeftButton:
            item: Optional[QtWidgets.QListWidgetItem] = self.itemAt(event.pos())
            if not item:
                return

            player: Optional["Player"] = item.data(Qt.ItemDataRole.UserRole)

            if player and player.is_active:
                self.selected_player = player
                reset_and_set_cursor(Qt.CursorShape.ClosedHandCursor)
                self.setCurrentItem(item)
                self.parent_dialog._enable_click_to_place_mode(player)

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        """Handle drag move events."""
        if event.mimeData().hasText() and event.mimeData().text().startswith("player:"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Handle drag enter events."""
        if event.mimeData().hasText() and event.mimeData().text().startswith("player:"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        """Handle drag leave events."""
        QtWidgets.QApplication.restoreOverrideCursor()
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        """Handle drop events."""
        QtWidgets.QApplication.restoreOverrideCursor()

        if not event.mimeData().hasText():
            event.ignore()
            return

        data: str = event.mimeData().text()
        if not data.startswith("player:"):
            event.ignore()
            return

        player_id: str = data.split(":", 1)[1]

        self.parent_dialog._save_state_for_undo()

        event.acceptProposedAction()
