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
from typing import List, Optional, Tuple

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import QMimeData, Qt, pyqtSignal
from PyQt6.QtGui import QDrag
from PyQt6.QtWidgets import QApplication, QDockWidget, QHBoxLayout, QVBoxLayout, QWidget

from gambitpairing.gui.gui_utils import reset_and_set_cursor, update_widget_style
from gambitpairing.gui.widgets.drag_list import DragListWidget
from gambitpairing.controllers.pairing.dutch_swiss import create_dutch_swiss_pairings
from gambitpairing.models.player import Player


class DroppableByeListWidget(DragListWidget):
    """Custom list widget for bye players that supports drag and drop operations."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(60)
        self.setMaximumHeight(120)
        self.setStyleSheet("""
            QListWidget {
                background-color: #fff3cd;
                border: 2px dashed #e2c290;
                border-radius: 8px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 6px 8px;
                margin: 1px;
                border-radius: 3px;
                background-color: #fff8e1;
                border: 1px solid #e2c290;
                color: #8b5c2b;
                font-weight: bold;
            }
            QListWidget::item:hover {
                background-color: #ffecb3;
                border-color: #d4ac0d;
            }
            QListWidget::item:selected {
                background-color: #d4ac0d;
                color: white;
                border-color: #b7950b;
            }
        """)

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

        drag.exec(supported_actions)

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
        return
        # If there are stacked over ride cursors remove them all.
        while QApplication.overrideCursor():
            QApplication.restoreOverrideCursor()

        # Reset to normal styling
        self.setProperty("class", "ManualPairingDialog")
        update_widget_style(self)

    def byePoolDropEvent(self, event):
        """Handle drop events for bye pool."""
        if not event.mimeData().hasText():
            self.dragLeaveEvent(event)
            return

        data = event.mimeData().text()
        if not data.startswith("player:"):
            self.dragLeaveEvent(event)
            return

        player_id = data.split(":", 1)[1]
        player = next(
            (p for p in self.parent_dialog.players if p.id == player_id), None
        )

        if not player:
            event.ignore()
            self.dragLeaveEvent(event)
            return

        # Save state before any modifications
        self.parent_dialog._save_state_for_undo()

        # Remove player from any existing pairing
        for i, (white, black) in enumerate(self.parent_dialog.pairings):
            if (white and white.id == player_id) or (black and black.id == player_id):
                if white and white.id == player_id:
                    self.parent_dialog.pairings[i] = (None, black)
                elif black and black.id == player_id:
                    self.parent_dialog.pairings[i] = (white, None)
                break

        # Remove empty pairings
        self.parent_dialog.pairings = [
            (w, b)
            for w, b in self.parent_dialog.pairings
            if w is not None or b is not None
        ]

        # Add player to bye pool if not already there
        if player not in self.parent_dialog.bye_players:
            self.parent_dialog.bye_players.append(player)

        # Update all displays
        self.parent_dialog._populate_player_pool()
        self.parent_dialog._update_pairings_display()
        self.parent_dialog._update_bye_display()
        self.parent_dialog._update_stats()
        self.parent_dialog._update_validation()

        event.acceptProposedAction()
        self.dragLeaveEvent(event)


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

        # Ensure we have enough pairings
        while len(self.parent_dialog.pairings) <= row:
            self.parent_dialog.pairings.append((None, None))

        # Place the player in the specified position
        try:
            if col == 1:  # White column
                self.parent_dialog._place_player_in_pairing(player_id, row, "white")
            elif col == 2:  # Black column
                self.parent_dialog._place_player_in_pairing(player_id, row, "black")

            event.acceptProposedAction()
        except Exception as e:
            # If placement fails, accept anyway as _place_player_in_pairing handles errors
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
        self.tournament = tournament
        self.pairings = []  # List of (Player, Player) tuples
        self.bye_players = []  # List of players with byes

        # Click-to-place functionality
        self._selected_for_placement = None

        # Undo system
        self.pairing_history = []
        self.max_history = 10

        # Load existing data
        if existing_pairings:
            self.pairings = list(existing_pairings)
        if existing_bye:
            # Handle both single bye player (legacy) and list of bye players
            if isinstance(existing_bye, list):
                self.bye_players = list(existing_bye)
            else:
                self.bye_players = [existing_bye] if existing_bye else []

        self._setup_ui()
        self._setup_shortcuts()
        self._populate_player_pool()
        self._update_pairings_display()

        # Connect the floating window close event to reattach functionality
        self._setup_floating_window_handling()

    def _setup_floating_window_handling(self):
        """Setup proper handling for floating window close events."""
        # We'll override the closeEvent in the dock widget's top level window when it becomes floating
        pass

    def closeEvent(self, event):
        """Handle dialog close event - ensure floating dock closes too."""
        # Close any floating dock widget
        if hasattr(self, "player_pool_dock"):
            self.player_pool_dock.close()
        super().closeEvent(event)

    def _setup_ui(self):
        """Init the user interface."""
        # Apply dialog-wide styling using the chess color scheme

        main_layout = QVBoxLayout(self)

        # Create a main window widget for proper dock widget support
        self.main_window_widget = QtWidgets.QMainWindow()

        self.main_window_widget.setProperty("class", "ManualPairingDialog")

        # Create detachable player pool
        self._create_detachable_player_pool()

        # Set the pairings panel as the central widget
        self.main_window_widget.setCentralWidget(self._create_pairings_panel())

        # Add the dock widget to the main window
        self.main_window_widget.addDockWidget(
            Qt.DockWidgetArea.LeftDockWidgetArea, self.player_pool_dock
        )

        # Add the main window widget to the dialog's layout
        main_layout.addWidget(self.main_window_widget)

        # Add validation panel and dialog buttons below the main content
        main_layout.addWidget(self._create_validation_panel())
        main_layout.addWidget(self._create_dialog_buttons())

        # Track selected player for click-to-place functionality
        self._selected_for_placement = None

    def _create_detachable_player_pool(self):
        """Create the detachable player pool dock widget with reattach capability."""
        self.player_pool_dock = QDockWidget("Player Pool", self)

        # Enable docking features but disable closing (we'll handle X button differently)
        # Disable floating to prevent "detachable" issues
        self.player_pool_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
        )

        # Allow docking to all sides
        self.player_pool_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea
            | Qt.DockWidgetArea.RightDockWidgetArea
            | Qt.DockWidgetArea.TopDockWidgetArea
            | Qt.DockWidgetArea.BottomDockWidgetArea
        )

        # Style the dock widget with the class ManualPairingDialog
        self.player_pool_dock.setProperty("class", "ManualPairingDialog")

        # Connect dock widget events for reattachment functionality
        self.player_pool_dock.topLevelChanged.connect(self._on_dock_detached)

        pool_widget = QWidget()
        pool_layout = QVBoxLayout(pool_widget)

        # Instructions
        pool_info = QtWidgets.QLabel(
            "Drag players to create pairings\nDouble-click to auto-pair • Right-click for options"
        )
        pool_info.setStyleSheet(
            "color: #6b7280; font-style: italic; padding: 5px; font-size: 10pt;"
        )
        pool_layout.addWidget(pool_info)

        # Search functionality
        pool_layout.addLayout(self._create_search_box())

        # Player list
        self.player_pool = self._create_player_list()
        pool_layout.addWidget(self.player_pool)

        # Bye player section
        pool_layout.addWidget(self._create_bye_section())

        self.player_pool_dock.setWidget(pool_widget)
        self.player_pool_dock.setMinimumWidth(250)

    def _create_search_box(self):
        """Create the search box layout with chess theme styling."""
        search_layout = QHBoxLayout()

        search_label = QtWidgets.QLabel("Search:")
        search_label.setStyleSheet("color: #2d5a27; font-weight: 600; font-size: 10pt;")
        search_layout.addWidget(search_label)

        self.search_box = QtWidgets.QLineEdit()
        self.search_box.setPlaceholderText("Search players by name or rating...")
        self.search_box.textChanged.connect(self._filter_player_pool)

        # Style the search box with chess theme
        self.search_box.setStyleSheet("""
            QLineEdit {
                background: #fff;
                border: 1.5px solid #e3e7ee;
                border-radius: 6px;
                padding: 6px 10px;
                color: #23272f;
                font-size: 10pt;
            }
            QLineEdit:focus {
                border-color: #e2c290;
                background: #f7fafd;
            }
            QLineEdit:disabled {
                background: #f3f7fc;
                color: #a1a7b3;
                border-color: #e5e7eb;
            }
        """)

        search_layout.addWidget(self.search_box)

        return search_layout

    def _create_player_list(self):
        """Create the player pool list widget."""
        player_pool = DragListWidget(self)
        player_pool.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
        )
        player_pool.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.DragDrop)
        player_pool.setDefaultDropAction(Qt.DropAction.MoveAction)

        # Connect signals
        player_pool.itemDoubleClicked.connect(self._auto_pair_selected_player)
        player_pool.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        player_pool.customContextMenuRequested.connect(self._show_pool_context_menu)

        return player_pool

    def _create_bye_section(self):
        """Create the bye players section."""
        bye_group = QtWidgets.QGroupBox("Bye Players")
        bye_layout = QVBoxLayout(bye_group)

        # Instructions
        bye_info = QtWidgets.QLabel(
            "Drop players here to assign byes • Drag back to remove"
        )
        bye_info.setStyleSheet(
            "color: #6b7280; font-style: italic; padding: 5px; font-size: 10pt;"
        )
        bye_layout.addWidget(bye_info)

        self.bye_list = DroppableByeListWidget(self)
        self.bye_list.setToolTip(
            "Drag players here to assign them a bye for this round\nDrag bye players back to pool or pairings to remove"
        )
        bye_layout.addWidget(self.bye_list)

        return bye_group

    def _create_pairings_panel(self):
        """Create the main pairings panel."""
        pairings_widget = QWidget()
        pairings_layout = QVBoxLayout(pairings_widget)

        # Toolbar with buttons
        pairings_layout.addLayout(self._create_toolbar())

        # Pairings table
        pairings_group = QtWidgets.QGroupBox("Pairings")
        pairings_group_layout = QVBoxLayout(pairings_group)

        pairings_info = QtWidgets.QLabel(
            "Drag players between White/Black columns or back to pool"
        )
        pairings_info.setStyleSheet("color: #666; font-style: italic; padding: 5px;")
        pairings_group_layout.addWidget(pairings_info)

        self.pairings_table = self._create_pairings_table()
        pairings_group_layout.addWidget(self.pairings_table)

        # Statistics display
        self.stats_label = QtWidgets.QLabel()
        self.stats_label.setStyleSheet(
            "color: #666; font-size: 10pt; padding: 5px; "
            "background-color: #f8f9fa; border-radius: 3px;"
        )
        self.stats_label.setWordWrap(True)
        pairings_group_layout.addWidget(self.stats_label)

        pairings_layout.addWidget(pairings_group)
        return pairings_widget

    def _create_toolbar(self):
        """Create the compact toolbar with small buttons."""
        toolbar_layout = QHBoxLayout()

        # Core pairing controls (removed "New Pairing" button as requested)
        self.clear_all_btn = self._create_button(
            "Clear All",
            "Remove all pairings and return players to pool",
            self._clear_all_pairings,
        )
        toolbar_layout.addWidget(self.clear_all_btn)

        self.undo_btn = self._create_button(
            "Undo", "Undo the last pairing action", self._undo_last_action
        )
        self.undo_btn.setEnabled(False)
        toolbar_layout.addWidget(self.undo_btn)

        # Auto-pair remaining button
        self.auto_pair_btn = self._create_button(
            "Auto Pair",
            "Auto-pair all remaining players using Dutch algorithm (Ctrl+A)",
            self._auto_pair_remaining,
        )
        toolbar_layout.addWidget(self.auto_pair_btn)

        toolbar_layout.addStretch()

        # Utility controls
        self.export_btn = self._create_button(
            "Export", "Export current pairings to file", self._export_pairings
        )
        toolbar_layout.addWidget(self.export_btn)

        self.import_btn = self._create_button(
            "Import", "Import pairings from file", self._import_pairings
        )
        toolbar_layout.addWidget(self.import_btn)

        return toolbar_layout

    def _create_button(
        self, text: str, tooltip: str, callback, css_class="ManualPairingDialog"
    ):
        """Create a button of some css_class for use in manual pairing dialog."""
        button = QtWidgets.QPushButton(text)
        button.setToolTip(tooltip)
        button.clicked.connect(callback)

        button.setProperty("class", css_class)

        return button

    def _create_pairings_table(self):
        """Create the pairings table widget."""
        table = DroppableTableWidget(self)
        table.setRowCount(0)
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Board", "White", "Black"])

        # Configure headers
        header = table.horizontalHeader()
        header.setSectionResizeMode(
            0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.Stretch)

        table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(self._show_pairing_context_menu)

        return table

    def _create_validation_panel(self):
        """Create the validation information panel."""
        self.validation_label = QtWidgets.QLabel()
        self.validation_label.setWordWrap(True)
        self.validation_label.setStyleSheet(
            "padding: 10px; border-radius: 5px; font-weight: bold;"
        )
        return self.validation_label

    def _create_dialog_buttons(self):
        """Create the dialog button box."""
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._confirm_finalize_pairings)
        buttons.rejected.connect(self.reject)
        return buttons

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
        total_players = len(self.players)
        active_players = len([p for p in self.players if p.is_active])
        withdrawn_players = total_players - active_players

        paired_players = sum(1 for white, black in self.pairings if white and black) * 2
        incomplete_pairings = sum(
            1 for white, black in self.pairings if not (white and black)
        )
        bye_count = len(self.bye_players)
        remaining_active_players = active_players - paired_players - bye_count

        stats_text = (
            f"Players: {paired_players}/{active_players} active paired • "
            f"{remaining_active_players} active remaining • "
            f"{incomplete_pairings} incomplete boards"
        )

        if withdrawn_players > 0:
            stats_text += f" • {withdrawn_players} withdrawn"

        if self.bye_players:
            if len(self.bye_players) == 1:
                status = " (Withdrawn)" if not self.bye_players[0].is_active else ""
                stats_text += f" • Bye: {self.bye_players[0].name}{status}"
            else:
                active_byes = [p for p in self.bye_players if p.is_active]
                withdrawn_byes = [p for p in self.bye_players if not p.is_active]
                bye_text = f" • Byes: {len(self.bye_players)} players"
                if withdrawn_byes:
                    bye_text += f" ({len(withdrawn_byes)} withdrawn)"
                stats_text += bye_text

        self.stats_label.setText(stats_text)

    def _update_validation(self):
        """Update validation status and warnings."""
        warnings = []

        # Check for incomplete pairings
        incomplete_count = sum(
            1 for white, black in self.pairings if not (white and black)
        )
        if incomplete_count > 0:
            warnings.append(f"{incomplete_count} incomplete boards need completion")

        # Check for unpaired active players
        active_unpaired = []
        accounted_players = set()

        # Add players in pairings
        for white, black in self.pairings:
            if white:
                accounted_players.add(white.id)
            if black:
                accounted_players.add(black.id)

        # Add bye players
        for bye_player in self.bye_players:
            accounted_players.add(bye_player.id)

        # Find active players not accounted for
        for player in self.players:
            if player.is_active and player.id not in accounted_players:
                active_unpaired.append(player)

        if active_unpaired:
            player_names = ", ".join([p.name for p in active_unpaired])
            warnings.append(
                f"{len(active_unpaired)} active player(s) not paired: {player_names}"
            )

        # Check for repeat pairings
        if (
            hasattr(self.tournament, "previous_matches")
            and self.tournament.previous_matches
        ):
            repeat_boards = self._check_repeat_pairings()
            if repeat_boards:
                warnings.append(
                    f"Repeat pairings on boards: {', '.join(repeat_boards)}"
                )

        # Update display
        if warnings:
            warning_text = "⚠️ " + " • ".join(warnings)
            self.validation_label.setText(warning_text)
            self.validation_label.setStyleSheet(
                "padding: 10px; border-radius: 5px; font-weight: bold; "
                "background-color: #fff3cd; color: #856404; border: 1px solid #ffeaa7;"
            )
        else:
            self.validation_label.setText("✅ All validations passed")
            self.validation_label.setStyleSheet(
                "padding: 10px; border-radius: 5px; font-weight: bold; "
                "background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb;"
            )

    def _check_repeat_pairings(self) -> List[str]:
        """Check for repeat pairings and return list of board numbers."""
        repeat_boards = []

        for i, (white, black) in enumerate(self.pairings):
            if white and black:
                # Check against previous matches (frozensets of player IDs)
                for player_pair in self.tournament.previous_matches:
                    if (
                        isinstance(player_pair, frozenset)
                        and len(player_pair) == 2
                        and white.id in player_pair
                        and black.id in player_pair
                    ):
                        repeat_boards.append(str(i + 1))
                        break

        return repeat_boards

    # === Undo System ===

    def _save_state_for_undo(self):
        """Save current state for undo functionality."""
        current_state = (
            [tuple(pair) for pair in self.pairings],
            list(self.bye_players),
        )
        self.pairing_history.append(current_state)

        # Limit history size
        if len(self.pairing_history) > self.max_history:
            self.pairing_history.pop(0)

        self.undo_btn.setEnabled(True)

    def _undo_last_action(self):
        """Undo the last pairing action."""
        if not self.pairing_history:
            self.undo_btn.setEnabled(False)
            return

        previous_pairings, previous_byes = self.pairing_history.pop()
        self.pairings = list(previous_pairings)
        self.bye_players = list(previous_byes)

        self._populate_player_pool()
        self._update_pairings_display()
        self._update_bye_display()
        self._update_stats()
        self._update_validation()
        if not self.pairing_history:
            self.undo_btn.setEnabled(False)

    # === Action Methods ===

    def _clear_all_pairings(self):
        """Clear all pairings and return players to pool."""
        if not self.pairings and not self.bye_players:
            return

        self._save_state_for_undo()
        self.pairings.clear()
        self.bye_players.clear()
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
        if 0 <= row < len(self.pairings):
            self._save_state_for_undo()
            del self.pairings[row]
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
                    self._save_state_for_undo()
                    self.pairings.append((white, black))
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

            self._save_state_for_undo()
            self.pairings.extend(auto_pairings)
            if auto_bye:
                self.bye_players.append(auto_bye)

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

    def _auto_pair_selected_player(self, item):
        """Auto-pair the selected player with the best available opponent."""
        player = item.data(Qt.ItemDataRole.UserRole)
        if not player:
            return

        # Find best opponent among available players
        available_players = []
        for i in range(self.player_pool.count()):
            pool_item = self.player_pool.item(i)
            if pool_item and not pool_item.isHidden():
                pool_player = pool_item.data(Qt.ItemDataRole.UserRole)
                if (
                    pool_player
                    and pool_player.id != player.id
                    and pool_player.is_active
                ):
                    available_players.append(pool_player)

        if not available_players:
            QtWidgets.QMessageBox.information(
                self, "Auto-Pair", "No available opponents found."
            )
            return

        # Simple logic: find closest rating
        best_opponent = min(
            available_players, key=lambda p: abs(p.rating - player.rating)
        )

        self._save_state_for_undo()

        # Add to pairings
        self.pairings.append((player, best_opponent))

        self._populate_player_pool()
        self._update_pairings_display()
        self._update_stats()
        self._update_validation()

    def _is_player_available(self, player: Player) -> bool:
        """Check if a player is available for pairing."""
        # Withdrawn players are not available for pairing
        if not player.is_active:
            return False

        # Check if in current pairings
        for white, black in self.pairings:
            if (white and white.id == player.id) or (black and black.id == player.id):
                return False

        # Check if bye player
        for bye_player in self.bye_players:
            if bye_player.id == player.id:
                return False

        return True

    def _get_dutch_pairings(self, available_players: List[Player]):
        """Get pairings using the Dutch algorithm."""
        if not self.tournament:
            # Fallback: simple pairing without tournament context
            pairings = []
            players_copy = available_players.copy()

            while len(players_copy) >= 2:
                white = players_copy.pop(0)
                black = players_copy.pop(0)
                pairings.append((white, black))

            bye_player = players_copy[0] if players_copy else None
            return pairings, bye_player

        # Use actual Dutch algorithm
        def get_eligible_bye_player(players):
            """Bye player selection - pick lowest rated player who hasn't had bye."""
            for player in sorted(players, key=lambda p: p.rating):
                if not hasattr(player, "has_had_bye") or not player.has_had_bye:
                    return player
            return players[0] if players else None

        pairings, bye_player, round_pairings_ids, bye_player_id = (
            create_dutch_swiss_pairings(
                available_players,
                self.round_number,
                (
                    self.tournament.previous_matches
                    if hasattr(self.tournament, "previous_matches")
                    else set()
                ),
                get_eligible_bye_player,
                None,  # allow_repeat_pairing_callback
                self.tournament.num_rounds if self.tournament else 5,
            )
        )

        # Return only the values expected by callers
        return pairings, bye_player

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
                export_data = {
                    "round_number": self.round_number,
                    "pairings": [
                        {
                            "white": (
                                {"id": white.id, "name": white.name} if white else None
                            ),
                            "black": (
                                {"id": black.id, "name": black.name} if black else None
                            ),
                        }
                        for white, black in self.pairings
                    ],
                    "bye_players": [
                        {"id": player.id, "name": player.name}
                        for player in self.bye_players
                    ],
                }

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

                # Validate import data
                if not isinstance(import_data, dict) or "pairings" not in import_data:
                    raise ValueError("Invalid pairings file format")

                # Create player lookup
                player_lookup = {p.id: p for p in self.players}

                # Import pairings
                imported_pairings = []
                for pairing_data in import_data["pairings"]:
                    white_data = pairing_data.get("white")
                    black_data = pairing_data.get("black")

                    white = player_lookup.get(white_data["id"]) if white_data else None
                    black = player_lookup.get(black_data["id"]) if black_data else None

                    imported_pairings.append((white, black))

                # Import bye players - handle both legacy single bye and new multi-bye format
                imported_byes = []
                if "bye_players" in import_data:
                    # New format with multiple bye players
                    for bye_data in import_data["bye_players"]:
                        bye_player = player_lookup.get(bye_data["id"])
                        if bye_player:
                            imported_byes.append(bye_player)
                elif "bye_player" in import_data and import_data["bye_player"]:
                    # Legacy format with single bye player
                    bye_data = import_data["bye_player"]
                    bye_player = player_lookup.get(bye_data["id"])
                    if bye_player:
                        imported_byes.append(bye_player)

                # Apply imported data
                self._save_state_for_undo()
                self.pairings = imported_pairings
                self.bye_players = imported_byes

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
        if player not in self.bye_players:
            self._save_state_for_undo()
            self.bye_players.append(player)
            self._populate_player_pool()
            self._update_bye_display()
            self._update_stats()

    def _toggle_player_withdrawal(self, player: Player):
        """Toggle a player's withdrawal status."""
        self._save_state_for_undo()
        player.is_active = not player.is_active

        # If withdrawing a player, remove them from any pairings or bye
        if not player.is_active:
            # Remove from bye position
            if player in self.bye_players:
                self.bye_players.remove(player)

            # Remove from pairings
            for i, (white, black) in enumerate(self.pairings):
                if (white and white.id == player.id) or (
                    black and black.id == player.id
                ):
                    if white and white.id == player.id:
                        self.pairings[i] = (None, black)
                    elif black and black.id == player.id:
                        self.pairings[i] = (white, None)
                    break

            # Remove empty pairings
            self.pairings = [
                (w, b) for w, b in self.pairings if w is not None or b is not None
            ]

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

        self._save_state_for_undo()

        # Get the current player in the target position (if any)
        current_pairings = list(self.pairings)

        # Ensure we have enough pairings
        while len(current_pairings) <= row:
            current_pairings.append((None, None))

        # Get current players in the row
        white, black = (
            current_pairings[row] if row < len(current_pairings) else (None, None)
        )

        # Remove selected player from current positions first
        self._remove_player_from_all_positions(self._selected_for_placement.id)

        # Place the selected player and handle displaced player
        if color == "white":
            if white:
                # White position occupied, send current white player back to pool
                pass  # They'll automatically appear in pool when we update
            current_pairings[row] = (self._selected_for_placement, black)
        else:  # black
            if black:
                # Black position occupied, send current black player back to pool
                pass  # They'll automatically appear in pool when we update
            current_pairings[row] = (white, self._selected_for_placement)

        # Update pairings
        self.pairings = current_pairings

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
        # Remove from bye position
        self.bye_players = [p for p in self.bye_players if p.id != player_id]

        # Remove from pairings
        for i, (white, black) in enumerate(self.pairings):
            if (white and white.id == player_id) or (black and black.id == player_id):
                if white and white.id == player_id:
                    self.pairings[i] = (None, black)
                elif black and black.id == player_id:
                    self.pairings[i] = (white, None)

        # Clean up empty pairings
        self.pairings = [
            (w, b) for w, b in self.pairings if w is not None or b is not None
        ]

    def _swap_colors_at_row(self, row: int):
        """Swap colors for pairing at specified row."""
        if 0 <= row < len(self.pairings):
            self._save_state_for_undo()
            white, black = self.pairings[row]
            self.pairings[row] = (black, white)
            self._update_pairings_display()

    def _place_player_in_pairing(self, player_id: str, row: int, color: str):
        """Place a player in a specific pairing position - comprehensive handling."""
        player = next((p for p in self.players if p.id == player_id), None)
        if not player:
            return

        self._save_state_for_undo()

        # Remove player from current position (pairings and bye)
        # Inline _remove_player_from_pairings logic
        for i, (white, black) in enumerate(self.pairings):
            if white and white.id == player_id:
                self.pairings[i] = (None, black)
            elif black and black.id == player_id:
                self.pairings[i] = (white, None)

        # Remove from bye players
        self.bye_players = [p for p in self.bye_players if p.id != player_id]

        self.pairings = [
            (w, b) for w, b in self.pairings if w is not None or b is not None
        ]

        # Ensure we have enough pairings
        while len(self.pairings) <= row:
            self.pairings.append((None, None))

        # Place in new position
        if 0 <= row < len(self.pairings):
            white, black = self.pairings[row]

            if color == "white":
                self.pairings[row] = (player, black)
            else:  # black
                self.pairings[row] = (white, player)

        # Update all displays
        self._populate_player_pool()
        self._update_pairings_display()
        self._update_bye_display()
        self._update_stats()
        self._update_validation()

    def accept(self):
        """Override accept to validate all players are accounted for, then finalize immediately."""
        # Find unresolved active players: not paired, not bye, and also those in pairings with no opponent
        accounted_players = set()
        unresolved_players = set()

        # Add paired/bye player IDs
        for white, black in self.pairings:
            if white:
                accounted_players.add(white.id)
            if black:
                accounted_players.add(black.id)
        for bye_player in self.bye_players:
            accounted_players.add(bye_player.id)

        # Find players in pairings with no opponent (single player on a board)
        for i, (white, black) in enumerate(self.pairings):
            if white and not black and white.is_active:
                unresolved_players.add(white)
            if black and not white and black.is_active:
                unresolved_players.add(black)

        # Find active players not accounted for at all
        for player in self.players:
            if player.is_active and player.id not in accounted_players:
                unresolved_players.add(player)

        if unresolved_players:
            player_names = [f"• {p.name} ({p.rating})" for p in unresolved_players]
            names_text = "\n".join(player_names)
            message = f"The following {len(unresolved_players)} active player(s) are not paired, given a bye, or withdrawn:\n\n{names_text}\n\nWould you like to withdraw all these players from the tournament?"
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
                self._save_state_for_undo()
                for player in unresolved_players:
                    player.is_active = False
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
        return complete_pairings, self.bye_players

    # === Dock Widget Management ===

    def _on_dock_detached(self, floating: bool):
        """Handle when the dock widget is detached/reattached."""
        if floating:
            # Dock is detached - keep original title
            self.player_pool_dock.setWindowTitle("Player Pool")
        else:
            # Dock is reattached - restore original title
            self.player_pool_dock.setWindowTitle("Player Pool")

    def _install_floating_close_handler(self):
        """Install close event handler for floating dock widget."""
        # This method provides a hook for future floating window management
        # Currently not needed as Qt handles floating dock widgets automatically
        pass


#  LocalWords:  ManualPairingDialog PairingSelected
