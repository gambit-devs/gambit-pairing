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

import csv
import logging

from PyQt6 import QtGui, QtWidgets
from PyQt6.QtCore import QDateTime, Qt

from gambitpairing.constants import CSV_FILTER
from gambitpairing.gui.views.standings.standings_presentation import (
    build_export_rows,
    build_print_standings_html,
    build_standings_headers,
    build_standings_table_html,
    project_standings_rows,
)
from gambitpairing.gui.ui_loader import load_ui_into, required_child
from gambitpairing.gui.widgets.tournament_placeholder import TournamentPlaceholder
from gambitpairing.gui.widgets.header import TabHeader


class StandingsView(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tournament = None
        self.parent_window = parent  # Store reference to main window
        load_ui_into(self, "standings_view.ui")
        self.main_layout = required_child(
            self, QtWidgets.QVBoxLayout, "main_layout"
        )
        header_layout = required_child(self, QtWidgets.QVBoxLayout, "header_layout")
        placeholder_layout = required_child(
            self, QtWidgets.QVBoxLayout, "placeholder_layout"
        )

        # ===== STANDINGS HEADER =====
        self.header = TabHeader("Standings")
        self.btn_print_standings = self.header.add_action_button(
            "print.svg", "Print Standings", self.open_print_dialog
        )
        header_layout.addWidget(self.header)

        # ===== STANDINGS TABLE =====
        self.standings_group = required_child(
            self, QtWidgets.QGroupBox, "standings_group"
        )

        # Add round info label
        self.lbl_round_info = required_child(self, QtWidgets.QLabel, "lbl_round_info")
        font = self.lbl_round_info.font()
        font.setPointSize(font.pointSize() + 1)
        font.setBold(True)
        self.lbl_round_info.setFont(font)

        self.table_standings = required_child(
            self, QtWidgets.QTableWidget, "table_standings"
        )
        self.table_standings.horizontalHeader().setSectionResizeMode(
            1, QtWidgets.QHeaderView.ResizeMode.Stretch
        )

        # Add no tournament placeholder
        self.tournament_placeholder = TournamentPlaceholder(self, "Standings")
        self.tournament_placeholder.create_tournament_requested.connect(
            self._trigger_create_tournament
        )
        self.tournament_placeholder.import_tournament_requested.connect(
            self._trigger_import_tournament
        )
        self.tournament_placeholder.hide()
        placeholder_layout.addWidget(self.tournament_placeholder)

    def reset_display(self) -> None:
        """Reset the UI to default state."""
        # clear standings table
        self.table_standings.setRowCount(0)

    def set_tournament(self, tournament):
        self.tournament = tournament
        # Update the header title with tournament name
        if tournament and tournament.name:
            self.header.set_title(f"Standings - {tournament.name}")
        else:
            self.header.set_title("Standings")
        self._update_visibility()

    def _update_visibility(self):
        """Show/hide content based on tournament existence."""
        if not self.tournament:
            self.tournament_placeholder.show()
            self.header.hide()
            self.standings_group.hide()
        else:
            self.tournament_placeholder.hide()
            self.header.show()
            self.standings_group.show()

    def _get_current_round_info(self):
        """Get current round information for display in titles/headers."""
        from gambitpairing.utils.print import TournamentPrintUtils

        # Use unified round information retrieval
        if hasattr(self.parent_window, "rounds_tab"):
            return TournamentPrintUtils.get_round_info(self.parent_window.rounds_tab)
        return ""

    def update_standings_table_headers(self):
        if not self.tournament:
            return
        projection = build_standings_headers(self.tournament.tiebreak_order)
        self.table_standings.setColumnCount(len(projection.headers))
        self.table_standings.setHorizontalHeaderLabels(projection.headers)
        self.table_standings.horizontalHeader().setSectionResizeMode(
            1, QtWidgets.QHeaderView.ResizeMode.Stretch
        )  # Player name
        for i in range(len(projection.headers)):
            if i != 1:
                self.table_standings.horizontalHeader().setSectionResizeMode(
                    i, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
                )
        for i, tip in enumerate(projection.tooltips):
            if i < self.table_standings.columnCount():  # Check index is valid
                header_item = self.table_standings.horizontalHeaderItem(i)
                if header_item:  # Ensure the QTableWidgetItem for header exists
                    header_item.setToolTip(tip)

    def _set_player_column_minimum_width(self):
        """Set minimum width for player column based on longest player name."""
        if not self.tournament or self.table_standings.rowCount() == 0:
            return

        # Get font metrics for accurate width calculation
        font_metrics = self.table_standings.fontMetrics()

        # Find the longest player name text
        max_width = 0
        header_text = "Player"  # Include header text in calculation
        max_width = max(max_width, font_metrics.horizontalAdvance(header_text))

        for row in range(self.table_standings.rowCount()):
            item = self.table_standings.item(row, 1)  # Player column is index 1
            if item:
                text_width = font_metrics.horizontalAdvance(item.text())
                max_width = max(max_width, text_width)

        # Add padding for cell margins and some extra space
        padding = 40  # Account for cell padding and some breathing room
        minimum_width = max_width + padding

        # Ensure a reasonable minimum (at least 150 pixels)
        minimum_width = max(minimum_width, 150)

        # Set the minimum width for the player column
        header = self.table_standings.horizontalHeader()
        header.setMinimumSectionSize(minimum_width)
        self.table_standings.setColumnWidth(1, minimum_width)

    def update_standings_table(self) -> None:
        self._update_visibility()

        if not self.tournament:
            return

        try:
            # Update round info display
            round_info = self._get_current_round_info()
            self.lbl_round_info.setText(round_info)

            # Ensure headers match current config first
            expected_col_count = 3 + len(self.tournament.tiebreak_order)
            if self.table_standings.columnCount() != expected_col_count:
                self.update_standings_table_headers()

            standings = (
                self.tournament.get_standings()
            )  # Gets sorted *active* players by default
            # If you want to show all players (active then inactive):
            # all_players_sorted = sorted(
            #    list(self.tournament.players.values()),
            #    key=functools.cmp_to_key(lambda p1, p2: (0 if p1.is_active else 1) - (0 if p2.is_active else 1) or self.tournament._compare_players(p1, p2)),
            #    reverse=False # custom sort, reverse for score happens in _compare_players
            # )
            # standings = all_players_sorted # Use this if showing all players.

            rows = project_standings_rows(
                standings, self.tournament.tiebreak_order
            )
            self.table_standings.setRowCount(len(rows))

            for rank, row_projection in enumerate(rows):
                row = rank
                item_rank = QtWidgets.QTableWidgetItem(row_projection.rank)
                item_player = QtWidgets.QTableWidgetItem(row_projection.player)
                item_score = QtWidgets.QTableWidgetItem(row_projection.score)

                item_rank.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item_score.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                row_color = self.table_standings.palette().color(
                    QtGui.QPalette.ColorRole.Text
                )
                # if not player.is_active: row_color = QtGui.QColor("gray") # If showing inactive

                item_rank.setForeground(row_color)
                item_player.setForeground(row_color)
                item_score.setForeground(row_color)

                self.table_standings.setItem(row, 0, item_rank)
                self.table_standings.setItem(row, 1, item_player)
                self.table_standings.setItem(row, 2, item_score)

                col_offset = 3
                for i, value in enumerate(row_projection.tiebreaks):
                    item_tb = QtWidgets.QTableWidgetItem(value)
                    item_tb.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    item_tb.setForeground(row_color)
                    self.table_standings.setItem(row, col_offset + i, item_tb)

            self.table_standings.resizeColumnsToContents()
            self.table_standings.resizeRowsToContents()

            # Set minimum width for player column based on longest name
            self._set_player_column_minimum_width()

        except Exception as e:
            logging.exception("Error updating standings table:")
            QtWidgets.QMessageBox.warning(
                self, "Standings Error", f"Could not update standings: {e}"
            )

    def export_standings(self) -> None:
        if not self.tournament:
            QtWidgets.QMessageBox.information(
                self, "Export Error", "No tournament data."
            )
            return
        standings = self.tournament.get_standings()  # Gets active sorted players
        if not standings:
            QtWidgets.QMessageBox.information(
                self, "Export Error", "No standings available to export."
            )
            return

        filename, selected_filter = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export Standings", "", CSV_FILTER
        )
        if not filename:
            return

        try:
            with open(filename, "w", encoding="utf-8", newline="") as f:
                is_csv = selected_filter.startswith("CSV")
                delimiter = "," if is_csv else "\t"
                writer = csv.writer(f, delimiter=delimiter) if is_csv else None

                header = build_standings_headers(
                    self.tournament.tiebreak_order
                ).headers
                if writer:
                    writer.writerow(header)
                else:
                    f.write(delimiter.join(header) + "\n")

                rows = project_standings_rows(
                    standings, self.tournament.tiebreak_order
                )
                for data_row in build_export_rows(rows):
                    if writer:
                        writer.writerow(data_row)
                    else:
                        f.write(delimiter.join(data_row) + "\n")

            QtWidgets.QMessageBox.information(
                self, "Export Successful", f"Standings exported to {filename}"
            )
            if self.parent() and hasattr(self.parent(), "statusBar"):
                self.parent().statusBar().showMessage(
                    f"Standings exported to {filename}"
                )
        except Exception as e:
            logging.exception("Error exporting standings:")
            QtWidgets.QMessageBox.critical(
                self, "Export Error", f"Could not save standings:\n{e}"
            )
            if self.parent() and hasattr(self.parent(), "statusBar"):
                self.parent().statusBar().showMessage("Error exporting standings.")

    def open_print_dialog(self):
        """Open the print options dialog via the Tournament tab."""
        if hasattr(self.parent_window, "rounds_tab"):
            # Delegate to TournamentView's print dialog, defaulting to Standings only
            self.parent_window.rounds_tab.open_print_dialog(
                default_pairings=False, default_standings=True
            )

    def print_standings_only(self):
        """Print the current standings table in a clean, ink-friendly, professional format with an enhanced legend."""
        from gambitpairing.utils.print import TournamentPrintUtils

        if self.table_standings.rowCount() == 0:
            QtWidgets.QMessageBox.information(
                self, "Print Standings", "No standings to print."
            )
            return

        # Always include tournament name
        tournament_name = ""
        if self.tournament and self.tournament.name:
            tournament_name = self.tournament.name
        printer, preview = TournamentPrintUtils.create_print_preview_dialog(
            self, "Print Preview - Standings"
        )
        include_tournament_name = True

        def render_preview(printer_obj):
            doc = QtGui.QTextDocument()

            # Get proper round information using unified utility
            round_subtitle = self._get_current_round_info()
            rows = project_standings_rows(
                self.tournament.get_standings(), self.tournament.tiebreak_order
            )
            html = build_print_standings_html(
                tournament_name=tournament_name,
                round_subtitle=round_subtitle,
                rows=rows,
                tiebreak_order=self.tournament.tiebreak_order,
                printed_at=QDateTime.currentDateTime().toString(
                    "yyyy-MM-dd hh:mm"
                ),
                include_tournament_name=include_tournament_name,
            )
            doc.setHtml(html)
            doc.print(printer_obj)

        preview.paintRequested.connect(render_preview)
        preview.exec()

    def update_ui_state(self):
        # Disable print standings if there are no standings
        has_standings = (
            self.tournament is not None and self.table_standings.rowCount() > 0
        )
        self.btn_print_standings.setEnabled(has_standings)
        self._update_visibility()

    def _trigger_create_tournament(self):
        parent = self.parent()
        while parent is not None:
            if hasattr(parent, "prompt_new_tournament"):
                parent.prompt_new_tournament()
                return
            parent = parent.parent()

    def _trigger_import_tournament(self):
        parent = self.parent()
        while parent is not None:
            if hasattr(parent, "load_tournament"):
                parent.load_tournament()
                return
            parent = parent.parent()

    def get_standings_html(self) -> str:
        """Generate HTML for the standings table."""
        if (
            self.table_standings.rowCount() == 0
            or not self.tournament
            or not hasattr(self.tournament, "tiebreak_order")
        ):
            return ""
        rows = project_standings_rows(
            self.tournament.get_standings(), self.tournament.tiebreak_order
        )
        return build_standings_table_html(rows, self.tournament.tiebreak_order)
