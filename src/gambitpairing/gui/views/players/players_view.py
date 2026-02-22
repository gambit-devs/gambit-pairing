"""Organize and display Player info."""

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


from __future__ import annotations

import csv
from datetime import datetime
import logging
from pathlib import Path
from typing import Optional

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt, pyqtSignal

from gambitpairing.gui.dialogs import PlayerManagementDialog
from gambitpairing.gui.notification import show_notification
from gambitpairing.gui.widgets.tournament_placeholder import TournamentPlaceholder

from gambitpairing.gui.widgets.player_placeholder import PlayerPlaceholder
from gambitpairing.gui.widgets import TabHeader, NumericTableWidgetItem
from gambitpairing.models.player import (
    Player,
    create_player,
    create_player_from_dict,
    FidePlayer,
)

form gambitpairing.controllers.player import (import_players_csv,
                                              export_players_csv,)


class PlayersView(QtWidgets.QWidget):
    """A QWidget tab for managing tournament players.

    Provides a table-based UI for viewing, adding, editing, withdrawing,
    reactivating, removing, importing, and exporting players. Displays
    contextual placeholders when no tournament exists or no players have
    been added yet.

    Signals
    -------
    status_message : pyqtSignal(str)
        Emitted to display a short status bar message.
    history_message : pyqtSignal(str)
        Emitted to log an action to the tournament history.
    dirty : pyqtSignal()
        Emitted when tournament data has been modified and needs saving.
    request_reset_tournament : pyqtSignal()
        Emitted to request that a new tournament be created.
    standings_update_requested : pyqtSignal()
        Emitted when standings may need to be recalculated (e.g. after
        a player is withdrawn or reactivated).

    Attributes
    ----------
    main_window : GambitPairingMainWindow
        The main window, used to access the rest of the app
    tournament : Tournament or None
        The currently loaded tournament. ``None`` if no tournament is open.
    main_layout : QtWidgets.QVBoxLayout
        The top-level vertical layout of the widget.
    header : TabHeader
        The header widget displaying the tab title "Players".
    player_group : QtWidgets.QGroupBox
        Group box containing the player table and add-player button.
    table_players : QtWidgets.QTableWidget
        Table displaying all registered players with columns:
        Name, Rating, Age, Status.
    btn_add_player_detail : QtWidgets.QPushButton
        Button to open the add-player dialog.
    list_players : QtWidgets.QListWidget
        Legacy widget kept for compatibility with ``reset_tournament_state()``.
        Not visible or actively used.
    tournament_placeholder : TournamentPlaceholder
        Placeholder widget shown when no tournament is loaded.
    no_players_placeholder : PlayerPlaceholder
        Placeholder widget shown when a tournament exists but has no players.
    """

    status_message = pyqtSignal(str)
    history_message = pyqtSignal(str)
    dirty = pyqtSignal()
    request_reset_tournament = pyqtSignal()
    standings_update_requested = pyqtSignal()

    def __init__(self, main_window=None):
        """Initialize the PlayersView widget and build the UI.

        Parameters
        ----------
        parent : QtWidgets.QWidget, optional
            The parent widget, by default ``None``.

        Raises
        ------
        assertion error if no main_window reference provided
        """
        assert main_window
        super().__init__(main_window)
        self.main_window = main_window
        self.tournament = None
        self.main_layout = QtWidgets.QVBoxLayout(self)

        # Header
        self.header = TabHeader("Players")
        self.main_layout.addWidget(self.header)

        self.player_group = QtWidgets.QGroupBox()
        self.player_group.setStyleSheet("QGroupBox { border: none; margin-top: 0px; }")
        self.player_group.setToolTip("Manage players. Right-click a row for actions.")
        player_group_layout = QtWidgets.QVBoxLayout(self.player_group)
        player_group_layout.setContentsMargins(0, 0, 0, 0)

        # --- Player Table ---
        self.table_players = QtWidgets.QTableWidget()
        self.table_players.setToolTip(
            "Registered players. Right-click to Edit/Withdraw/Reactivate/Remove."
        )
        self.table_players.setColumnCount(4)  # Name, Rating, Age, Active
        self.table_players.setHorizontalHeaderLabels(
            ["Name", "Rating", "Age", "Status"]
        )
        self.table_players.setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.table_players.customContextMenuRequested.connect(
            self.on_player_context_menu
        )
        self.table_players.setAlternatingRowColors(True)
        self.table_players.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table_players.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table_players.setSortingEnabled(True)

        # Resize columns
        header = self.table_players.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.Interactive)
        self.table_players.setColumnWidth(1, 110)  # Rating
        self.table_players.setColumnWidth(2, 90)  # Age
        self.table_players.setColumnWidth(3, 130)  # Status

        header.setSortIndicatorShown(True)
        header.setSectionsClickable(True)
        header.setSectionsMovable(True)
        header.setHighlightSections(True)
        ## Enable smooth sort arrow animation (Qt6+) I do not understand this. So I do not like n
        # try:
        # header.setAnimated(True)
        # except Exception:
        # raise RuntimeError("Exception not handled in players_view: %s" % Exception)

        player_group_layout.addWidget(self.table_players)
        self.table_players.hide()  # Hide table initially

        self.btn_add_player_detail = QtWidgets.QPushButton(" Add New Player...")
        self.btn_add_player_detail.setToolTip(
            "Open dialog to add a new player with full details."
        )
        self.btn_add_player_detail.clicked.connect(self.add_player_detailed)
        player_group_layout.addWidget(self.btn_add_player_detail)
        self.main_layout.addWidget(self.player_group)

        # --- Compatibility: Legacy list_players for reset_tournament_state() ---
        self.list_players = QtWidgets.QListWidget()
        self.list_players.setVisible(False)  # Not used, but present for compatibility

        # Ensure sufficient row height for padded cells
        vheader = self.table_players.verticalHeader()
        vheader.setDefaultSectionSize(38)  # Increase default row height
        vheader.setMinimumSectionSize(38)

        # Initialize placeholders
        self.tournament_placeholder = TournamentPlaceholder(self, "Players")
        self.tournament_placeholder.create_tournament_requested.connect(
            main_window.prompt_new_tournament
        )
        self.tournament_placeholder.import_tournament_requested.connect(
            main_window.load_tournament
        )
        self.no_players_placeholder = PlayerPlaceholder(self)
        self.no_players_placeholder.import_players_requested.connect(
            self.import_players_csv
        )
        self.no_players_placeholder.add_player_requested.connect(
            self.add_player_detailed
        )

        # Hide placeholders initially
        self.tournament_placeholder.hide()
        self.no_players_placeholder.hide()
        self.main_layout.addWidget(self.tournament_placeholder)
        self.main_layout.addWidget(self.no_players_placeholder)

    def update_ui_state(self):
        self._update_visibility()

    def on_player_context_menu(self, point: QtCore.QPoint) -> None:
        """Display a context menu for the row under the cursor.

        Offers Edit, Withdraw/Reactivate, and Remove actions. Edit and
        Remove are disabled once the tournament has started. Executes the
        chosen action immediately.

        Parameters
        ----------
        point : QtCore.QPoint
            The position of the right-click in table-local coordinates.
        """
        row = self.table_players.rowAt(point.y())
        if row < 0 or not self.tournament:
            return

        player_id_item = self.table_players.item(row, 0)
        if not player_id_item:
            return

        player_id = player_id_item.data(Qt.ItemDataRole.UserRole)
        player = self.tournament.players.get(player_id)
        if not player:
            return

        tournament_started = len(self.tournament.rounds_pairings_ids) > 0

        menu = QtWidgets.QMenu(self)
        edit_action = menu.addAction("Edit Player Details...")
        withdraw_action_text = (
            "Withdraw Player" if player.is_active else "Reactivate Player"
        )
        withdraw_action = menu.addAction(withdraw_action_text)
        remove_action = menu.addAction("Remove Player")

        edit_action.setEnabled(not tournament_started)
        remove_action.setEnabled(not tournament_started)
        withdraw_action.setEnabled(True)

        action = menu.exec(self.table_players.mapToGlobal(point))

        if action == edit_action:
            dialog = PlayerManagementDialog(
                self, player_data=player.to_dict(), tournament=self.tournament
            )
            if dialog.exec():
                data = dialog.get_player_data()
                if not data["name"]:
                    QtWidgets.QMessageBox.warning(
                        self, "Edit Error", "Player name cannot be empty."
                    )
                    return
                if data["name"] != player.name and any(
                    p.name == data["name"] for p in self.tournament.players.values()
                ):
                    QtWidgets.QMessageBox.warning(
                        self,
                        "Edit Error",
                        f"Another player named '{data['name']}' already exists.",
                    )
                    return

                # Update player attributes
                self._update_player_from_data(player, data)

                self.update_player_table_row(player)
                self.history_message.emit(f"Player '{player.name}' details updated.")
                self.dirty.emit()
        elif action == withdraw_action:
            player.is_active = not player.is_active
            status_log_msg = "Withdrawn" if not player.is_active else "Reactivated"
            self.update_player_table_row(player)
            self.history_message.emit(f"Player '{player.name}' {status_log_msg}.")
            self.dirty.emit()
            self.standings_update_requested.emit()
            self.update_ui_state()
        elif action == remove_action:
            reply = QtWidgets.QMessageBox.question(
                self,
                "Remove Player",
                f"Remove player '{player.name}' permanently?",
                QtWidgets.QMessageBox.StandardButton.Yes
                | QtWidgets.QMessageBox.StandardButton.No,
                QtWidgets.QMessageBox.StandardButton.No,
            )
            if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                if player.id in self.tournament.players:
                    del self.tournament.players[player.id]
                    self.history_message.emit(
                        f"Player '{player.name}' removed from tournament."
                    )
                self.table_players.removeRow(row)
                self.status_message.emit(f"Player '{player.name}' removed.")
        self.update_ui_state()

    def add_player_detailed(self):
        """Open the player management dialog to add or edit a player.

        Blocks adding players once the tournament has started. If no
        tournament exists, emits ``request_reset_tournament`` and prompts
        the user to create one first. On successful dialog acceptance,
        either creates a new player (via ``create_player_from_dict``) or
        updates an existing one, then refreshes the table row and emits
        ``dirty``.
        """
        tournament_started = (
            self.tournament and len(self.tournament.rounds_pairings_ids) > 0
        )
        if tournament_started:
            QtWidgets.QMessageBox.warning(
                self,
                "Tournament Active",
                "Cannot add players after the tournament has started.",
            )
            return
        if not self.tournament:
            self.request_reset_tournament.emit()
            QtWidgets.QMessageBox.information(
                self,
                "New Tournament",
                "Please set up a new tournament before adding players.",
            )
            return

        dialog = PlayerManagementDialog(self, tournament=self.tournament)
        if dialog.exec():
            data = dialog.get_player_data()
            if not data["name"]:
                QtWidgets.QMessageBox.warning(
                    self, "Validation Error", "Player name cannot be empty."
                )
                return

            # Check if we're editing an existing player
            editing_player_id = dialog.get_editing_player_id()

            if editing_player_id:
                # Editing mode - update the existing player
                player = self.tournament.players.get(editing_player_id)
                if not player:
                    QtWidgets.QMessageBox.warning(
                        self, "Error", "Player not found in tournament."
                    )
                    return

                # Check for duplicate name only if the name has changed
                if data["name"] != player.name and any(
                    p.name == data["name"] for p in self.tournament.players.values()
                ):
                    QtWidgets.QMessageBox.warning(
                        self,
                        "Duplicate Player",
                        f"Player '{data['name']}' already exists.",
                    )
                    return

                # Update player attributes
                self._update_player_from_data(player, data)
                self.update_player_table_row(player)
                self.history_message.emit(f"Player '{player.name}' details updated.")
                self.dirty.emit()
            else:
                # Add mode - create new player
                if any(
                    p.name == data["name"] for p in self.tournament.players.values()
                ):
                    QtWidgets.QMessageBox.warning(
                        self,
                        "Duplicate Player",
                        f"Player '{data['name']}' already exists.",
                    )
                    return

                # Use factory to create player (automatically detects FidePlayer)
                new_player = create_player_from_dict(data)

                self.tournament.players[new_player.id] = new_player
                self.add_player_to_table(new_player)
                self.status_message.emit(f"Added player: {new_player.name}")
                self.history_message.emit(
                    f"Player '{new_player.name}' ({new_player.rating}) added."
                )
                self.dirty.emit()

            self.update_ui_state()


    def update_player_table_row(self, player: Player):
        """Find the table row for the given player and refresh its contents.

        Searches all rows for a matching ``UserRole`` data value. Updates
        the Name, Rating, Age, and Status cells, and sets the foreground
        colour to grey for inactive players.

        Parameters
        ----------
        player : Player
            The player whose row should be refreshed.
        """
        for i in range(self.table_players.rowCount()):
            item = self.table_players.item(i, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) == player.id:
                # Update Name
                item.setText(player.name)

                # Update Rating
                rating_item = self.table_players.item(i, 1)
                rating_item.setText(str(player.rating or ""))

                # Update Age - use player's age property directly
                age_item = self.table_players.item(i, 2)
                age = player.age
                age_item.setText(str(age) if age is not None else "")

                # Update Status
                status_item = self.table_players.item(i, 3)
                status_text = "Active" if player.is_active else "Inactive"
                status_item.setText(status_text)

                # Update row color
                color = (
                    QtGui.QColor("gray")
                    if not player.is_active
                    else self.table_players.palette().color(
                        QtGui.QPalette.ColorRole.Text
                    )
                )
                item.setForeground(color)
                rating_item.setForeground(color)
                age_item.setForeground(color)
                status_item.setForeground(color)
                break

    def add_player_to_table(self, player: Player):
        """Append a new row for the given player to the table.

        Temporarily disables sorting during insertion to prevent row
        index shifting. Builds a tooltip from all available player
        fields (including FIDE metadata when present) and applies it to
        every cell. Inactive players are rendered in grey.

        Parameters
        ----------
        player : Player
            The player to append. Uses ``player.id`` as ``UserRole``
            data on the Name cell for later lookup.
        """
        self.table_players.setSortingEnabled(False)  # Disable sorting during insert
        row_position = self.table_players.rowCount()
        self.table_players.insertRow(row_position)

        # Name Item
        name_item = QtWidgets.QTableWidgetItem(player.name)
        name_item.setData(Qt.ItemDataRole.UserRole, player.id)

        # Rating Item
        rating_item = NumericTableWidgetItem(str(player.rating or ""))

        # Age Item - use the player's age property directly
        age = player.age
        age_item = NumericTableWidgetItem(str(age) if age is not None else "")

        # Status Item
        status_text = "Active" if player.is_active else "Inactive"
        status_item = QtWidgets.QTableWidgetItem(status_text)

        # Set Tooltip
        tooltip_parts = [f"ID: {player.id}"]
        if player.gender:
            tooltip_parts.append(f"Gender: {player.gender}")
        if player.dob:
            tooltip_parts.append(f"Date of Birth: {player.dob}")
        if player.phone:
            tooltip_parts.append(f"Phone: {player.phone}")
        if player.email:
            tooltip_parts.append(f"Email: {player.email}")
        if player.federation:
            tooltip_parts.append(f"Federation: {player.federation}")
        # FIDE metadata if present
        if getattr(player, "fide_id", None):
            tooltip_parts.append(f"FIDE ID: {player.fide_id}")
        if getattr(player, "fide_title", None):
            tooltip_parts.append(f"Title: {player.fide_title}")
        if getattr(player, "fide_standard", None) is not None:
            tooltip_parts.append(f"Std: {player.fide_standard}")
        if getattr(player, "fide_rapid", None) is not None:
            tooltip_parts.append(f"Rapid: {player.fide_rapid}")
        if getattr(player, "fide_blitz", None) is not None:
            tooltip_parts.append(f"Blitz: {player.fide_blitz}")
        if getattr(player, "birth_year", None) is not None:
            tooltip_parts.append(f"Birth Year: {player.birth_year}")
        if getattr(player, "gender", None):
            tooltip_parts.append(f"Gender: {player.gender}")
        tooltip = "\n".join(tooltip_parts)
        name_item.setToolTip(tooltip)
        rating_item.setToolTip(tooltip)
        age_item.setToolTip(tooltip)
        status_item.setToolTip(tooltip)

        # Set color for inactive players
        if not player.is_active:
            color = QtGui.QColor("gray")
            name_item.setForeground(color)
            rating_item.setForeground(color)
            age_item.setForeground(color)
            status_item.setForeground(color)

        self.table_players.setItem(row_position, 0, name_item)
        self.table_players.setItem(row_position, 1, rating_item)
        self.table_players.setItem(row_position, 2, age_item)
        self.table_players.setItem(row_position, 3, status_item)

        self.table_players.setSortingEnabled(True)

    def import_players_csv(self):
        """Import players from a CSV file chosen via a file dialog.

        Expects a CSV with at minimum a ``Name`` column. Optionally reads
        ``Rating``, ``Gender``, ``Date of Birth``, ``Phone``, ``Email``,
        ``Club``, and ``Federation`` columns. Skips rows with empty names
        or names that already exist in the tournament. Uses
        ``create_player`` to construct each player object.

        Emits ``dirty`` and calls ``refresh_player_list`` if at least one
        player was added. Shows a success notification via
        ``show_notification`` if available, otherwise falls back to a
        ``QMessageBox``.

        Raises
        ------
        Exception
            Any file I/O or parsing error is caught, logged via
            ``logging.exception``, and reported to the user through a
            notification or ``QMessageBox``.
        """
        if self.tournament and len(self.tournament.rounds_pairings_ids) > 0:
            QtWidgets.QMessageBox.warning(
                self,
                "Import Error",
                "Cannot import players after tournament has started.",
            )
            return
        if not self.tournament:
            QtWidgets.QMessageBox.warning(
                self,
                "No Tournament",
                "Please create a tournament before importing players.",
            )
            return

        file_name, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Import Players", "", "CSV Files (*.csv);;Text Files (*.txt)"
        )
        import_players_csv(file_name)
        if added_count > 0:
            self.history_message.emit(
                f"Imported {added_count} players from {filename}."
            )
            self.dirty.emit()
            self.refresh_player_list()
            self.update_ui_state()
            # Show notification
            try:
                show_notification(
                    self,
                    f"Imported {added_count} players from {Path(filename).name}",
                    duration=3500,
                    notification_type="success",
                )
            except Exception:
                QtWidgets.QMessageBox.information(
                    self, "Import Successful", f"Imported {added_count} players."
                )
        else:
            QtWidgets.QMessageBox.warning(
                self,
                "Import Notice",
                "No new players were imported. Check for empty names or duplicates.",
            )

    def export_players_csv(self):
        """Export all players to a CSV file chosen via a save dialog.

        Writes one row per player sorted alphabetically by name, with
        columns: Name, Rating, Gender, Date of Birth, Phone, Email, Club,
        Federation, Active, ID.

        Raises
        ------
        Exception
            Any file I/O error is caught, logged via
            ``logging.exception``, and reported to the user through a
            ``QMessageBox``.
        """
        if not self.tournament or not self.tournament.players:
            QtWidgets.QMessageBox.information(
                self, "Export Error", "No players available to export."
            )

            return
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export Players", "", "CSV Files (*.csv)"
        )
        if not filename:
            return
        export_players_csv(self.tournament.players, filename)
        self.status_message.emit(f"Players exported to {filename}")

    def refresh_player_list(self):
        """Clear and repopulate the player table from the current tournament.

        Clears all existing rows, calls ``_update_visibility`` to set the
        correct placeholder/table state, then (if players exist) inserts
        them sorted alphabetically by name via ``add_player_to_table``.
        """
        self.table_players.setSortingEnabled(False)
        self.table_players.setRowCount(0)

        # Only populate table if tournament exists and has players
        if self.tournament and self.tournament.players:
            for player in sorted(
                self.tournament.players.values(), key=lambda p: p.name
            ):
                self.add_player_to_table(player)

        self.table_players.setSortingEnabled(True)


#  LocalWords:  PlayerPlaceholder TournamentPlaceholder TabHeader
