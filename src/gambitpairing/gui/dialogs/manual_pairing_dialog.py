"""Manual adjustments to GP pairings."""

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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import json
from typing import List, Tuple

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import QMimeData, Qt, pyqtSignal
from PyQt6.QtGui import QDrag
from PyQt6.QtWidgets import QApplication

from gambitpairing.controllers.pairing.manual_pairing_controller import (
    ManualPairingController,
    build_stats_text,
    build_unresolved_players_message,
    build_validation_projection,
    repeat_pairing_boards,
    unresolved_active_players,
)
from gambitpairing.gui.gui_utils import update_widget_style
from gambitpairing.gui.ui_loader import load_ui_into, required_child
from gambitpairing.gui.widgets.drag_list import DragListWidget
from gambitpairing.models.player import Player
from gambitpairing.representation.manual_pairing import (
    build_pairings_export_data,
    parse_pairings_import_data,
)


class DroppableByeListWidget(DragListWidget):
    """Custom list widget for bye players that supports drag and drop operations."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(60)
        self.setMaximumHeight(120)
        self.setProperty("class", "ManualPairingByeList")

    def startDrag(self, supported_actions):
        """Start drag operation from bye pool."""
        current_item = self.currentItem()
        if not current_item:
            return

        player = current_item.data(Qt.ItemDataRole.UserRole)
        if not player:
            return

        # indicate drag by global setting of cursor
        QApplication.setOverrideCursor(Qt.CursorShape.ClosedHandCursor)

        # Create drag for bye player
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(f"player:{player.id}")
        drag.setMimeData(mime_data)

        # Create drag pixmap for bye player
        pixmap = QtGui.QPixmap(250, 35)
        pixmap.fill(QtGui.QColor(255, 255, 255, 200))
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        # Draw border - special color for bye player
        border_color = QtGui.QColor(255, 193, 7)  # Warning yellow for bye
        bg_color = QtGui.QColor(255, 248, 220, 180)

        painter.setPen(QtGui.QPen(border_color, 2))
        painter.setBrush(QtGui.QBrush(bg_color))
        painter.drawRoundedRect(1, 1, 248, 33, 4, 4)

        # Draw text
        painter.setPen(QtGui.QColor(0, 0, 0))
        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)

        text = f"{player.name} (Bye)"
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, text)
        painter.end()

        drag.setPixmap(pixmap)
        drag.setHotSpot(QtCore.QPoint(125, 17))

        try:
            drag.exec(supported_actions)
        finally:
            self._reset_drag_state()

    def dragEnterEvent(self, event):
        """Handle drag enter events for bye pool."""
        if event.mimeData().hasText() and event.mimeData().text().startswith("player:"):
            event.acceptProposedAction()
            self.setProperty("class", "PairingSelected")
            update_widget_style(self)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        """Handle drag leave events, restoring completely cursor."""
        self._reset_drag_state()
        super().dragLeaveEvent(event)

    def _reset_drag_state(self):
        """Restore the list's normal appearance and any overridden cursor."""
        while QApplication.overrideCursor() is not None:
            QApplication.restoreOverrideCursor()
        self.setProperty("class", "ManualPairingByeList")
        update_widget_style(self)

    def dropEvent(self, event):
        """Assign the dragged player to the bye pool."""
        self.byePoolDropEvent(event)

    def byePoolDropEvent(self, event):
        """Handle drop events for bye pool."""
        dialog = self.parent_dialog
        if dialog is None or not event.mimeData().hasText():
            event.ignore()
            self._reset_drag_state()
            return

        data = event.mimeData().text()
        if not data.startswith("player:"):
            event.ignore()
            self._reset_drag_state()
            return

        player_id = data.split(":", 1)[1]
        player = next(
            (p for p in dialog.players if p.id == player_id), None
        )

        if not player:
            event.ignore()
            self._reset_drag_state()
            return

        dialog._set_player_as_bye(player)

        event.acceptProposedAction()
        self._reset_drag_state()


class DroppableTableWidget(QtWidgets.QTableWidget):
    """Custom table widget that supports drag and drop operations."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_dialog = parent
        self.setAcceptDrops(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDropIndicatorShown(True)
        self.drag_preview_row = -1
        self.drag_preview_col = -1

        # Auto-scroll timer for drag operations
        self.auto_scroll_timer = QtCore.QTimer(self)
        self.auto_scroll_timer.timeout.connect(self._auto_scroll)
        self.auto_scroll_direction = 0  # -1 for up, 1 for down, 0 for no scroll

    def dragEnterEvent(self, event):
        """Handle drag enter events for pairings table."""
        if event.mimeData().hasText() and event.mimeData().text().startswith("player:"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """Handle drag move events for pairings table."""
        if event.mimeData().hasText() and event.mimeData().text().startswith("player:"):
            # Handle different PyQt6 versions
            try:
                pos = event.position().toPoint()
            except AttributeError:
                pos = event.pos()

            row = self.rowAt(pos.y())
            col = self.columnAt(pos.x())

            # Auto-scroll logic
            scroll_margin = 30  # pixels from edge to start scrolling
            viewport_height = self.viewport().height()

            if pos.y() < scroll_margin and self.verticalScrollBar().value() > 0:
                # Near top, scroll up
                self.auto_scroll_direction = -1
                if not self.auto_scroll_timer.isActive():
                    self.auto_scroll_timer.start(50)  # 50ms intervals
            elif (
                pos.y() > (viewport_height - scroll_margin)
                and self.verticalScrollBar().value()
                < self.verticalScrollBar().maximum()
            ):
                # Near bottom, scroll down
                self.auto_scroll_direction = 1
                if not self.auto_scroll_timer.isActive():
                    self.auto_scroll_timer.start(50)
            else:
                # Stop auto-scrolling
                self.auto_scroll_direction = 0
                self.auto_scroll_timer.stop()

            # Clear previous preview
            if self.drag_preview_row >= 0 and self.drag_preview_col >= 0:
                self._clear_drag_preview()

            # Show preview if valid drop location
            if col in [1, 2] and row >= 0:  # White or Black columns
                self.drag_preview_row = row
                self.drag_preview_col = col
                self._show_drag_preview(row, col)

            event.acceptProposedAction()
        else:
            self.auto_scroll_timer.stop()
            event.ignore()

    def _auto_scroll(self):
        """Perform auto-scrolling during drag operations."""
        if self.auto_scroll_direction == -1:
            # Scroll up
            current_value = self.verticalScrollBar().value()
            self.verticalScrollBar().setValue(current_value - 10)
        elif self.auto_scroll_direction == 1:
            # Scroll down
            current_value = self.verticalScrollBar().value()
            self.verticalScrollBar().setValue(current_value + 10)

    def dragLeaveEvent(self, event):
        """Handle drag leave events."""
        self._clear_drag_preview()
        self.auto_scroll_timer.stop()
        self.auto_scroll_direction = 0

    def _show_drag_preview(self, row, col):
        """Show visual preview of where drop will occur."""
        if row < self.rowCount() and col < self.columnCount():
            item = self.item(row, col)
            if item:
                item.setBackground(QtGui.QColor(255, 243, 205))  # Light yellow

    def _clear_drag_preview(self):
        """Clear drag preview highlighting."""
        if self.drag_preview_row >= 0 and self.drag_preview_col >= 0:
            if (
                self.drag_preview_row < self.rowCount()
                and self.drag_preview_col < self.columnCount()
            ):
                item = self.item(self.drag_preview_row, self.drag_preview_col)
                if item:
                    item.setBackground(QtGui.QColor())  # Clear background
        self.drag_preview_row = -1
        self.drag_preview_col = -1

    def dropEvent(self, event):
        """Handle drop events for pairings table - comprehensive handling."""
        self._clear_drag_preview()
        # Stop auto-scrolling
        self.auto_scroll_timer.stop()
        self.auto_scroll_direction = 0

        if not event.mimeData().hasText():
            return

        data = event.mimeData().text()
        if not data.startswith("player:"):
            return

        player_id = data.split(":", 1)[1]
        player = next(
            (p for p in self.parent_dialog.players if p.id == player_id), None
        )

        if not player:
            event.ignore()
            return

        # Get drop position - handle different PyQt6 versions
        try:
            pos = event.position().toPoint()
        except AttributeError:
            pos = event.pos()

        row = self.rowAt(pos.y())
        col = self.columnAt(pos.x())

        # If dropped outside table or on invalid column, add new pairing
        if row < 0 or col not in [1, 2]:
            row = len(self.parent_dialog.pairings)
            col = 1  # Default to white

        # Place the player in the specified position
        if col == 1:  # White column
            self.parent_dialog._place_player_in_pairing(player_id, row, "white")
        elif col == 2:  # Black column
            self.parent_dialog._place_player_in_pairing(player_id, row, "black")

        event.acceptProposedAction()

    def mousePressEvent(self, event):
        """Handle mouse press to start drag operations from table cells or place selected player."""
        super().mousePressEvent(event)

        if event.button() == Qt.MouseButton.LeftButton:
            # Handle different PyQt6 versions
            try:
                pos = event.position().toPoint()
            except AttributeError:
                pos = event.pos()

            item = self.itemAt(pos)

            # Check if we're in click-to-place mode
            if (
                hasattr(self.parent_dialog, "_selected_for_placement")
                and self.parent_dialog._selected_for_placement
            ):
                if item and item.column() in [1, 2]:  # White or Black column
                    row = item.row()
                    color = "white" if item.column() == 1 else "black"
                    self.parent_dialog._place_selected_player(row, color)
                    return

            # Normal drag functionality
            if item and item.column() > 0:  # White or Black column
                # Check if there's a player in the cell
                player_data = item.data(Qt.ItemDataRole.UserRole)
                if player_data is not None:
                    # Start drag from table
                    drag = QDrag(self)
                    mime_data = QMimeData()
                    mime_data.setText(f"player:{player_data.id}")
                    drag.setMimeData(mime_data)

                    # Create improved drag pixmap
                    pixmap = QtGui.QPixmap(250, 35)
                    pixmap.fill(QtGui.QColor(255, 255, 255, 200))
                    painter = QtGui.QPainter(pixmap)
                    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

                    # Draw border with color coding
                    if item.column() == 1:  # White piece
                        border_color = QtGui.QColor(76, 175, 80)  # Green for white
                        bg_color = QtGui.QColor(232, 245, 233, 180)
                    else:  # Black piece
                        border_color = QtGui.QColor(158, 158, 158)  # Gray for black
                        bg_color = QtGui.QColor(245, 245, 245, 180)

                    painter.setPen(QtGui.QPen(border_color, 2))
                    painter.setBrush(QtGui.QBrush(bg_color))
                    painter.drawRoundedRect(1, 1, 248, 33, 4, 4)

                    # Draw text
                    painter.setPen(QtGui.QColor(0, 0, 0))
                    font = painter.font()
                    font.setPointSize(10)
                    painter.setFont(font)

                    color_text = "White" if item.column() == 1 else "Black"
                    text = f"{player_data.name} ({color_text})"
                    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, text)
                    painter.end()

                    drag.setPixmap(pixmap)
                    drag.setHotSpot(QtCore.QPoint(125, 17))

                    drag.exec(Qt.DropAction.MoveAction)


class ManualPairingDialog(QtWidgets.QDialog):
    # Signal to notify when player status changes
    player_status_changed = pyqtSignal()

    def __init__(
        self,
        players: List[Player],
        existing_pairings=None,
        existing_bye=None,
        round_number=1,
        parent=None,
        tournament=None,
    ):
        super().__init__(parent)
        self.setWindowTitle(f"Edit Pairings - Round {round_number}")
        self.setMinimumSize(900, 650)
        self.resize(1100, 750)

        # Core data
        self.players = players
        self.round_number = round_number
        self.controller = ManualPairingController(
            players,
            existing_pairings=existing_pairings,
            existing_byes=existing_bye,
            round_number=round_number,
            tournament=tournament,
        )
        self.pairing_history = self.controller.history
        self.max_history = self.controller.max_history

        # Click-to-place functionality
        self._selected_for_placement = None

        self._setup_ui()
        self._setup_shortcuts()
        self._populate_player_pool()
        self._update_pairings_display()
        self._update_bye_display()

    def closeEvent(self, event):
        """Handle dialog close and clear transient interaction state."""
        self._restore_override_cursors()
        super().closeEvent(event)

    @staticmethod
    def _restore_override_cursors() -> None:
        """Clear cursors left by click-to-place or drag interactions."""
        while QApplication.overrideCursor() is not None:
            QApplication.restoreOverrideCursor()

    @property
    def pairings(self):
        """Compatibility view of the controller-owned board state."""
        return self.controller.pairings

    @pairings.setter
    def pairings(self, value):
        self.controller.pairings = list(value)

    @property
    def bye_players(self):
        """Compatibility view of the controller-owned bye state."""
        return self.controller.bye_players

    @bye_players.setter
    def bye_players(self, value):
        self.controller.bye_players = list(value)

    def _setup_ui(self):
        """Load the static Designer layout and bind its behavior.

        The widgets and their layout are deliberately declared in
        ``manual_pairing_dialog.ui``.  This method only connects signals and
        applies the runtime configuration required by the drag/drop controls.
        """
        load_ui_into(self, "manual_pairing_dialog.ui")
        self.setWindowTitle(f"Edit Pairings - Round {self.round_number}")
        self.setProperty("class", "ManualPairingDialog")
        self.main_layout = required_child(
            self, QtWidgets.QVBoxLayout, "main_layout"
        )
        self.main_window_widget = required_child(
            self, QtWidgets.QMainWindow, "main_window_widget"
        )
        self.central_widget = required_child(
            self, QtWidgets.QWidget, "central_widget"
        )
        self.player_pool_dock = required_child(
            self, QtWidgets.QDockWidget, "player_pool_dock"
        )
        self.toolbar_layout = required_child(
            self, QtWidgets.QHBoxLayout, "toolbar_layout"
        )
        self.pairings_group = required_child(
            self, QtWidgets.QGroupBox, "pairings_group"
        )
        self.pairings_group_layout = required_child(
            self, QtWidgets.QVBoxLayout, "pairings_group_layout"
        )
        self.validation_label = required_child(
            self, QtWidgets.QLabel, "validation_label"
        )
        self.buttons = required_child(self, QtWidgets.QDialogButtonBox, "buttons")

        self.clear_all_btn = required_child(
            self, QtWidgets.QPushButton, "clear_all_btn"
        )
        self.undo_btn = required_child(self, QtWidgets.QPushButton, "undo_btn")
        self.auto_pair_btn = required_child(
            self, QtWidgets.QPushButton, "auto_pair_btn"
        )
        self.export_btn = required_child(self, QtWidgets.QPushButton, "export_btn")
        self.import_btn = required_child(self, QtWidgets.QPushButton, "import_btn")
        self.search_box = required_child(self, QtWidgets.QLineEdit, "search_box")
        self.player_pool = required_child(
            self, DragListWidget, "player_pool"
        )
        self.bye_list = required_child(
            self, DroppableByeListWidget, "bye_list"
        )
        self.bye_placeholder_label = required_child(
            self, QtWidgets.QLabel, "bye_placeholder_label"
        )
        self.pairings_table = required_child(
            self, DroppableTableWidget, "pairings_table"
        )
        self.stats_label = required_child(self, QtWidgets.QLabel, "stats_label")

        # Designer creates custom widgets with their immediate UI parent.  The
        # drag/drop implementations need the dialog as their behavior owner.
        self.player_pool.parent_dialog = self
        self.bye_list.parent_dialog = self
        self.pairings_table.parent_dialog = self

        self.main_window_widget.setProperty("class", "ManualPairingMainWindow")
        # QMainWindow defaults to a top-level window flag even when Designer
        # gives it a dialog parent.  Clear that flag so the composed editor is
        # actually rendered inside this dialog's layout.
        self.main_window_widget.setWindowFlags(Qt.WindowType.Widget)
        # A Designer-created QMainWindow remains explicitly hidden when it is
        # embedded in a dialog, so make the composed central view visible.
        self.main_window_widget.show()
        self.player_pool_dock.setProperty("class", "ManualPairingDialog")
        self.player_pool.setProperty("class", "ManualPairingDialog")
        self.search_box.setProperty("class", "ManualPairingDialog")
        self.bye_placeholder_label.setAttribute(
            QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )

        self._configure_player_pool()
        self._configure_pairings_table()

        self.buttons.accepted.connect(self._confirm_finalize_pairings)
        self.buttons.rejected.connect(self.reject)
        self.clear_all_btn.clicked.connect(self._clear_all_pairings)
        self.undo_btn.clicked.connect(self._undo_last_action)
        self.auto_pair_btn.clicked.connect(self._auto_pair_remaining)
        self.export_btn.clicked.connect(self._export_pairings)
        self.import_btn.clicked.connect(self._import_pairings)
        self.search_box.textChanged.connect(self._filter_player_pool)
        self.player_pool.itemDoubleClicked.connect(self._auto_pair_selected_player)
        self.player_pool.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.player_pool.customContextMenuRequested.connect(
            self._show_pool_context_menu
        )
        self.pairings_table.customContextMenuRequested.connect(
            self._show_pairing_context_menu
        )

    def _configure_player_pool(self) -> None:
        """Configure the Designer-created player pool's interaction hooks."""
        self.player_pool.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
        )
        self.player_pool.setDragDropMode(
            QtWidgets.QAbstractItemView.DragDropMode.DropOnly
        )
        self.player_pool.setDragEnabled(False)
        self.player_pool.setDefaultDropAction(Qt.DropAction.MoveAction)

    def _configure_pairings_table(self) -> None:
        """Configure table behavior that depends on runtime callbacks."""
        header = self.pairings_table.horizontalHeader()
        header.setSectionResizeMode(
            0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.Stretch)

    def _confirm_finalize_pairings(self):
        reply = QtWidgets.QMessageBox.question(
            self,
            "Finalize Pairings",
            "Are you sure you want to finalize these pairings?",
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No,
        )
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            self.accept()
        # If No, do nothing and return to dialog

    def _setup_shortcuts(self):
        """Create keyboard shortcuts."""
        shortcuts = [
            ("Ctrl+A", self._auto_pair_remaining),
            ("Delete", self._delete_selected_pairing),
        ]

        for key_sequence, callback in shortcuts:
            shortcut = QtGui.QShortcut(QtGui.QKeySequence(key_sequence), self)
            shortcut.activated.connect(callback)

    # === Core Functionality Methods ===

    def _populate_player_pool(self):
        """Populate the player pool with unpaired players."""
        self.player_pool.clear()

        # Get players not in current pairings
        paired_players = set()
        for white, black in self.pairings:
            if white:
                paired_players.add(white.id)
            if black:
                paired_players.add(black.id)

        # Add bye players to paired set
        for bye_player in self.bye_players:
            paired_players.add(bye_player.id)

        # Separate active and withdrawn players
        active_unpaired = []
        withdrawn_unpaired = []

        for player in self.players:
            if player.id not in paired_players:
                if player.is_active:
                    active_unpaired.append(player)
                else:
                    withdrawn_unpaired.append(player)

        # Add active players first
        for player in active_unpaired:
            item = QtWidgets.QListWidgetItem()
            item.setText(f"{player.name} ({player.rating})")
            item.setData(Qt.ItemDataRole.UserRole, player)
            self.player_pool.addItem(item)

        # Add withdrawn players at the bottom with visual effects
        for player in withdrawn_unpaired:
            item = QtWidgets.QListWidgetItem()
            item.setText(f"{player.name} ({player.rating}) - Withdrawn")
            item.setData(Qt.ItemDataRole.UserRole, player)

            # Apply visual styling for withdrawn players
            font = item.font()
            font.setItalic(True)
            item.setFont(font)
            item.setForeground(QtGui.QColor("gray"))

            # Set a different background color
            item.setBackground(QtGui.QColor(245, 245, 245))

            self.player_pool.addItem(item)

    def _update_pairings_display(self):
        """Update the pairings table display."""
        self.pairings_table.setRowCount(len(self.pairings))

        for i, (white, black) in enumerate(self.pairings):
            # Board number
            board_item = QtWidgets.QTableWidgetItem(str(i + 1))
            board_item.setFlags(board_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.pairings_table.setItem(i, 0, board_item)

            # White player
            white_text = white.name if white else "Empty"
            if white and not white.is_active:
                white_text += " (Withdrawn)"
            white_item = QtWidgets.QTableWidgetItem(white_text)
            white_item.setData(Qt.ItemDataRole.UserRole, white)
            if white:
                if white.is_active:
                    white_item.setBackground(QtGui.QColor(255, 255, 255))
                else:
                    white_item.setBackground(QtGui.QColor(245, 245, 245))
                    white_item.setForeground(QtGui.QColor("gray"))
                    font = white_item.font()
                    font.setItalic(True)
                    white_item.setFont(font)
            self.pairings_table.setItem(i, 1, white_item)

            # Black player
            black_text = black.name if black else "Empty"
            if black and not black.is_active:
                black_text += " (Withdrawn)"
            black_item = QtWidgets.QTableWidgetItem(black_text)
            black_item.setData(Qt.ItemDataRole.UserRole, black)
            if black:
                if black.is_active:
                    black_item.setBackground(QtGui.QColor(220, 220, 220))
                else:
                    black_item.setBackground(QtGui.QColor(245, 245, 245))
                    black_item.setForeground(QtGui.QColor("gray"))
                    font = black_item.font()
                    font.setItalic(True)
                    black_item.setFont(font)
            self.pairings_table.setItem(i, 2, black_item)

        self._update_stats()
        self._update_validation()

    def _update_stats(self):
        """Update pairing statistics display."""
        self.stats_label.setText(
            build_stats_text(self.players, self.pairings, self.bye_players)
        )

    def _update_validation(self):
        """Update validation status and warnings."""
        projection = build_validation_projection(
            self.players,
            self.pairings,
            self.bye_players,
            self.controller.previous_matches,
        )
        self.validation_label.setText(projection.text)
        self.validation_label.setProperty(
            "state", "warning" if projection.has_warnings else "success"
        )
        update_widget_style(self.validation_label)

    def _check_repeat_pairings(self) -> List[str]:
        """Check for repeat pairings and return list of board numbers."""
        return repeat_pairing_boards(
            self.pairings, self.controller.previous_matches or []
        )

    # === Undo System ===

    def _save_state_for_undo(self):
        """Save current state for undo functionality."""
        self.controller.save_state_for_undo()
        self.undo_btn.setEnabled(self.controller.can_undo)

    def _undo_last_action(self):
        """Undo the last pairing action."""
        if not self.controller.undo():
            self.undo_btn.setEnabled(False)
            return

        self._populate_player_pool()
        self._update_pairings_display()
        self._update_bye_display()
        self._update_stats()
        self._update_validation()
        self.undo_btn.setEnabled(self.controller.can_undo)

    # === Action Methods ===

    def _clear_all_pairings(self):
        """Clear all pairings and return players to pool."""
        if not self.controller.clear_pairings():
            return

        self._populate_player_pool()
        self._update_pairings_display()
        self._update_bye_display()
        self._update_validation()

    def _delete_selected_pairing(self):
        """Delete the currently selected pairing."""
        current_row = self.pairings_table.currentRow()
        if current_row >= 0:
            self._delete_pairing_at_row(current_row)

    def _delete_pairing_at_row(self, row: int):
        """Delete pairing at specified row."""
        if self.controller.delete_pairing(row):
            self._populate_player_pool()
            self._update_pairings_display()
            self._update_validation()

    def _auto_pair_selected_player(self, item):
        """Auto-pair the selected player using Dutch algorithm."""
        player = item.data(Qt.ItemDataRole.UserRole)
        if not player:
            return

        # Check if player is withdrawn
        if not player.is_active:
            QtWidgets.QMessageBox.information(
                self,
                "Auto-Pair",
                f"Cannot auto-pair withdrawn player {player.name}. Reactivate them first.",
            )
            return

        # Get remaining active players
        remaining_players = [
            p
            for p in self.players
            if p.id not in {player.id} and self._is_player_available(p)
        ]

        if not remaining_players:
            QtWidgets.QMessageBox.information(
                self,
                "Auto-Pair",
                f"No available active players to pair with {player.name}.",
            )
            return

        # Use Dutch algorithm to find best pairing
        try:
            auto_pairings, auto_bye = self._get_dutch_pairings(
                [player] + remaining_players
            )

            # Find the pairing containing our selected player
            for white, black in auto_pairings:
                if white.id == player.id or black.id == player.id:
                    self.controller.add_pairings([(white, black)])
                    self._populate_player_pool()
                    self._update_pairings_display()
                    self._update_validation()
                    break

        except Exception as e:
            QtWidgets.QMessageBox.warning(
                self, "Auto-Pair Error", f"Could not auto-pair: {str(e)}"
            )

    def _auto_pair_remaining(self):
        """Auto-pair all remaining players using Dutch algorithm."""
        remaining_players = [p for p in self.players if self._is_player_available(p)]

        if len(remaining_players) < 2:
            if len(remaining_players) == 1:
                QtWidgets.QMessageBox.information(
                    self,
                    "Auto-Pair",
                    f"Only 1 active player ({remaining_players[0].name}) remaining. "
                    f"Assign them a bye or pair them manually.",
                )
            else:
                QtWidgets.QMessageBox.information(
                    self,
                    "Auto-Pair",
                    "Need at least 2 remaining active players to auto-pair.",
                )
            return

        try:
            auto_pairings, auto_bye = self._get_dutch_pairings(remaining_players)

            self.controller.add_pairings(auto_pairings, auto_bye)

            self._populate_player_pool()
            self._update_pairings_display()
            self._update_bye_display()
            self._update_validation()

        except Exception as e:
            QtWidgets.QMessageBox.warning(
                self,
                "Auto-Pair Error",
                f"Could not auto-pair remaining players: {str(e)}",
            )

    def _is_player_available(self, player: Player) -> bool:
        """Check if a player is available for pairing."""
        return self.controller.is_player_available(player)

    def _get_dutch_pairings(self, available_players: List[Player]):
        """Get pairings using the Dutch algorithm."""
        return self.controller.get_dutch_pairings(available_players)

    # === Utility Methods ===

    def _filter_player_pool(self, search_text: str):
        """Filter the player pool based on search text."""
        search_text = search_text.lower().strip()

        for i in range(self.player_pool.count()):
            item = self.player_pool.item(i)
            if item:
                player = item.data(Qt.ItemDataRole.UserRole)
                if player:
                    visible = (
                        not search_text
                        or search_text in player.name.lower()
                        or search_text in str(player.rating)
                        or search_text in str(player.score)
                        or (
                            not player.is_active
                            and (
                                "withdrawn" in search_text or "inactive" in search_text
                            )
                        )
                    )
                    item.setHidden(not visible)

    def _update_bye_display(self):
        """Update the bye players display."""
        self.bye_list.clear()
        self.bye_placeholder_label.setVisible(not self.bye_players)

        for bye_player in self.bye_players:
            item = QtWidgets.QListWidgetItem()
            status_text = " (Withdrawn)" if not bye_player.is_active else ""
            item.setText(f"{bye_player.name} ({bye_player.rating}){status_text}")
            item.setData(Qt.ItemDataRole.UserRole, bye_player)

            # Apply special styling for withdrawn bye players
            if not bye_player.is_active:
                font = item.font()
                font.setItalic(True)
                item.setFont(font)
                item.setForeground(QtGui.QColor("gray"))

            self.bye_list.addItem(item)

    # === Export/Import Methods ===

    def _export_pairings(self):
        """Export current pairings to a JSON file."""
        if not self.pairings:
            QtWidgets.QMessageBox.information(self, "Export", "No pairings to export.")
            return

        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export Pairings",
            f"pairings_round_{self.round_number}.json",
            "JSON Files (*.json)",
        )

        if filename:
            try:
                export_data = build_pairings_export_data(
                    self.round_number, self.pairings, self.bye_players
                )

                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)

                QtWidgets.QMessageBox.information(
                    self, "Export Complete", f"Pairings exported to {filename}"
                )

            except Exception as e:
                QtWidgets.QMessageBox.warning(
                    self, "Export Error", f"Failed to export pairings: {str(e)}"
                )

    def _import_pairings(self):
        """Import pairings from a JSON file."""
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Import Pairings", "", "JSON Files (*.json)"
        )

        if filename:
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    import_data = json.load(f)

                # Create player lookup
                player_lookup = {p.id: p for p in self.players}

                imported_pairings, imported_byes = parse_pairings_import_data(
                    import_data, player_lookup
                )

                # Apply imported data
                self.controller.replace_pairings(imported_pairings, imported_byes)

                self._populate_player_pool()
                self._update_pairings_display()
                self._update_bye_display()

                QtWidgets.QMessageBox.information(
                    self, "Import Complete", f"Pairings imported from {filename}"
                )

            except Exception as e:
                QtWidgets.QMessageBox.warning(
                    self, "Import Error", f"Failed to import pairings: {str(e)}"
                )

    # === Context Menu Methods ===

    def _show_pool_context_menu(self, position):
        """Show context menu for player pool."""
        item = self.player_pool.itemAt(position)
        if not item:
            return

        player = item.data(Qt.ItemDataRole.UserRole)
        if not player:
            return

        menu = QtWidgets.QMenu(self)

        auto_pair_action = menu.addAction("Auto-pair this player")
        auto_pair_action.triggered.connect(
            lambda: self._auto_pair_selected_player(item)
        )

        set_bye_action = menu.addAction("Set as bye player")
        set_bye_action.triggered.connect(lambda: self._set_player_as_bye(player))

        # Add withdraw/reactivate player option
        withdraw_text = "Withdraw Player" if player.is_active else "Reactivate Player"
        withdraw_action = menu.addAction(withdraw_text)
        withdraw_action.triggered.connect(
            lambda: self._toggle_player_withdrawal(player)
        )

        menu.exec(self.player_pool.mapToGlobal(position))

    def _show_pairing_context_menu(self, position):
        """Show context menu for pairings table."""
        row = self.pairings_table.rowAt(position.y())
        if row < 0:
            return

        menu = QtWidgets.QMenu(self)

        delete_action = menu.addAction("Delete this pairing")
        delete_action.triggered.connect(lambda: self._delete_pairing_at_row(row))

        swap_colors_action = menu.addAction("Swap colors")
        swap_colors_action.triggered.connect(lambda: self._swap_colors_at_row(row))

        menu.exec(self.pairings_table.mapToGlobal(position))

    def _set_player_as_bye(self, player: Player):
        """Set a player as a bye player."""
        if self.controller.assign_bye(player):
            self._populate_player_pool()
            self._update_bye_display()
            self._update_stats()
            self._update_validation()

    def _toggle_player_withdrawal(self, player: Player):
        """Toggle a player's withdrawal status."""
        self.controller.toggle_player_withdrawal(player)

        # Update all displays
        self._populate_player_pool()
        self._update_pairings_display()
        self._update_bye_display()
        self._update_stats()
        self._update_validation()

        # Emit signal to notify parent that player status has changed
        self.player_status_changed.emit()

    def _enable_click_to_place_mode(self, player: Player):
        """Enable click-to-place mode with the selected player."""
        self._selected_for_placement = player
        # Change cursor to indicate placement mode
        QApplication.setOverrideCursor(Qt.CursorShape.PointingHandCursor)

    def _place_selected_player(self, row: int, color: str):
        """Place the selected player in the specified position."""
        if not self._selected_for_placement:
            return

        self.controller.place_player(
            self._selected_for_placement.id, row, color
        )
        self._restore_override_cursors()

        # Clear selection mode
        self._selected_for_placement = None
        self.pairings_table.setCursor(Qt.CursorShape.ArrowCursor)
        self.player_pool.clearSelection()

        # Update displays
        self._populate_player_pool()
        self._update_pairings_display()
        self._update_stats()
        self._update_validation()

    def _remove_player_from_all_positions(self, player_id: str):
        """Remove a player from all current positions (pairings and bye)."""
        self.controller.remove_player_from_all_positions(player_id)

    def _swap_colors_at_row(self, row: int):
        """Swap colors for pairing at specified row."""
        if self.controller.swap_colors(row):
            self._update_pairings_display()

    def _place_player_in_pairing(self, player_id: str, row: int, color: str):
        """Place a player in a specific pairing position - comprehensive handling."""
        if not self.controller.place_player(player_id, row, color):
            return

        # Update all displays
        self._populate_player_pool()
        self._update_pairings_display()
        self._update_bye_display()
        self._update_stats()
        self._update_validation()

    def accept(self):
        """Override accept to validate all players are accounted for, then finalize immediately."""
        # Find unresolved active players: not paired, not bye, and also those in pairings with no opponent
        unresolved_players = unresolved_active_players(
            self.players, self.pairings, self.bye_players
        )

        if unresolved_players:
            message = build_unresolved_players_message(unresolved_players)
            reply = QtWidgets.QMessageBox.question(
                self,
                "Unpaired Active Players",
                message,
                QtWidgets.QMessageBox.StandardButton.Yes
                | QtWidgets.QMessageBox.StandardButton.No
                | QtWidgets.QMessageBox.StandardButton.Cancel,
                QtWidgets.QMessageBox.StandardButton.Cancel,
            )
            if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                # Withdraw all unresolved active players
                self.controller.withdraw_players(unresolved_players)
                self._populate_player_pool()
                self._update_stats()
                self._update_validation()
                self.player_status_changed.emit()
                # After withdrawal, finalize immediately
                super().accept()
            elif reply == QtWidgets.QMessageBox.StandardButton.No:
                QtWidgets.QMessageBox.information(
                    self,
                    "Pairings Incomplete",
                    "Please pair all active players, assign them a bye, or withdraw them before finalizing.",
                )
                return
            else:  # Cancel
                return
        else:
            # All active players are accounted for, finalize immediately
            super().accept()

    # === Public Interface ===

    def get_pairings_and_bye(self) -> Tuple[List[Tuple[Player, Player]], List[Player]]:
        """Get the final pairings and bye players."""
        complete_pairings = [
            (white, black)
            for white, black in self.pairings
            if white is not None and black is not None
        ]
        return complete_pairings, list(self.bye_players)

#  LocalWords:  ManualPairingDialog PairingSelected
