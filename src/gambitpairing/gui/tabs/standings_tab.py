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

from gambitpairing.constants import (
    CSV_FILTER,
    TB_CUMULATIVE,
    TB_CUMULATIVE_OPP,
    TB_MEDIAN,
    TB_MOST_BLACKS,
    TB_SOLKOFF,
    TB_SONNENBORN_BERGER,
    TIEBREAK_NAMES,
)
from gambitpairing.gui.notournament_placeholder import NoTournamentPlaceholder


class StandingsTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tournament = None
        self.parent_window = parent  # Store reference to main window
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.standings_group = QtWidgets.QGroupBox("Standings")
        standings_layout = QtWidgets.QVBoxLayout(self.standings_group)

        # Add round info label
        self.lbl_round_info = QtWidgets.QLabel("")
        self.lbl_round_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = self.lbl_round_info.font()
        font.setPointSize(font.pointSize() + 1)
        font.setBold(True)
        self.lbl_round_info.setFont(font)
        self.lbl_round_info.setStyleSheet("color: #666; margin: 5px;")
        standings_layout.addWidget(self.lbl_round_info)

        self.table_standings = QtWidgets.QTableWidget(0, 3)
        self.table_standings.setHorizontalHeaderLabels(["Rank", "Player", "Score"])
        self.table_standings.setToolTip(
            "Player standings sorted by Score and configured Tiebreakers."
        )
        self.table_standings.horizontalHeader().setSectionResizeMode(
            1, QtWidgets.QHeaderView.ResizeMode.Stretch
        )
        self.table_standings.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table_standings.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table_standings.setAlternatingRowColors(True)
        standings_layout.addWidget(self.table_standings)
        self.btn_print_standings = QtWidgets.QPushButton("Print Standings")
        self.btn_print_standings.setToolTip("Print the current standings table")
        standings_layout.addWidget(self.btn_print_standings)
        self.main_layout.addWidget(self.standings_group)
        self.btn_print_standings.clicked.connect(self.print_standings)

        # Add no tournament placeholder
        self.no_tournament_placeholder = NoTournamentPlaceholder(self, "Standings")
        self.no_tournament_placeholder.create_tournament_requested.connect(
            self._trigger_create_tournament
        )
        self.no_tournament_placeholder.import_tournament_requested.connect(
            self._trigger_import_tournament
        )
        self.no_tournament_placeholder.hide()
        self.main_layout.addWidget(self.no_tournament_placeholder)

    def set_tournament(self, tournament):
        self.tournament = tournament
        # Update the group box title with tournament name
        if tournament and tournament.name:
            self.standings_group.setTitle(f"Standings - {tournament.name}")
        else:
            self.standings_group.setTitle("Standings")
        self._update_visibility()

    def _update_visibility(self):
        """Show/hide content based on tournament existence."""
        if not self.tournament:
            self.no_tournament_placeholder.show()
            self.standings_group.hide()
        else:
            self.no_tournament_placeholder.hide()
            self.standings_group.show()

    def _get_current_round_info(self):
        """Get current round information for display in titles/headers."""
        from gambitpairing.utils.print import TournamentPrintUtils

        # Use unified round information retrieval
        if hasattr(self.parent_window, "tournament_tab"):
            return TournamentPrintUtils.get_round_info(
                self.parent_window.tournament_tab
            )
        return ""

    def update_standings_table_headers(self):
        if not self.tournament:
            return
        base_headers = ["Rank", "Player", "Score"]
        tb_headers = [
            TIEBREAK_NAMES.get(key, key.upper())
            for key in self.tournament.tiebreak_order
        ]  # Use upper for unknown keys
        full_headers = base_headers + tb_headers
        self.table_standings.setColumnCount(len(full_headers))
        self.table_standings.setHorizontalHeaderLabels(full_headers)
        self.table_standings.horizontalHeader().setSectionResizeMode(
            1, QtWidgets.QHeaderView.ResizeMode.Stretch
        )  # Player name
        for i in range(len(full_headers)):
            if i != 1:
                self.table_standings.horizontalHeader().setSectionResizeMode(
                    i, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
                )
        header_tooltips = ["Rank", "Player Name (Rating)", "Total Score"] + [
            TIEBREAK_NAMES.get(key, f"Tiebreak: {key}")
            for key in self.tournament.tiebreak_order
        ]
        for i, tip in enumerate(header_tooltips):
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

    def _update_visibility(self):
        """Show/hide content based on tournament existence."""
        if not self.tournament:
            self.no_tournament_placeholder.show()
            self.standings_group.hide()
        else:
            self.no_tournament_placeholder.hide()
            self.standings_group.show()

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

            self.table_standings.setRowCount(len(standings))

            tb_formats = {
                TB_MEDIAN: ".2f",
                TB_SOLKOFF: ".2f",
                TB_CUMULATIVE: ".1f",  # Using .2f for Median/Solkoff for finer detail
                TB_CUMULATIVE_OPP: ".1f",
                TB_SONNENBORN_BERGER: ".2f",
                TB_MOST_BLACKS: ".0f",
            }

            for rank, player in enumerate(standings):
                row = rank
                rank_str = str(rank + 1)
                status_str = ""  # Standings usually only show active players from get_standings()
                # If inactive players were included in `standings`:
                # status_str = "" if player.is_active else " (I)"

                item_rank = QtWidgets.QTableWidgetItem(rank_str)
                item_player = QtWidgets.QTableWidgetItem(
                    f"{player.name} ({player.rating or 'NR'})" + status_str
                )  # NR for No Rating
                item_score = QtWidgets.QTableWidgetItem(f"{player.score:.1f}")

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
                for i, tb_key in enumerate(self.tournament.tiebreak_order):
                    value = player.tiebreakers.get(tb_key, 0.0)
                    format_spec = tb_formats.get(tb_key, ".2f")  # Default format .2f
                    item_tb = QtWidgets.QTableWidgetItem(f"{value:{format_spec}}")
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

                header = [
                    self.table_standings.horizontalHeaderItem(i).text()
                    for i in range(self.table_standings.columnCount())
                ]
                if writer:
                    writer.writerow(header)
                else:
                    f.write(delimiter.join(header) + "\n")

                tb_formats = {
                    TB_MEDIAN: ".2f",
                    TB_SOLKOFF: ".2f",
                    TB_CUMULATIVE: ".1f",
                    TB_CUMULATIVE_OPP: ".1f",
                    TB_SONNENBORN_BERGER: ".2f",
                    TB_MOST_BLACKS: ".0f",
                }

                for rank, player in enumerate(standings):
                    rank_str = str(rank + 1)
                    player_str = f"{player.name} ({player.rating or 'NR'})"
                    # If exporting all players, including inactive:
                    # player_str += (" (I)" if not player.is_active else "")
                    score_str = f"{player.score:.1f}"
                    data_row = [rank_str, player_str, score_str]

                    for tb_key in self.tournament.tiebreak_order:
                        value = player.tiebreakers.get(tb_key, 0.0)
                        format_spec = tb_formats.get(tb_key, ".2f")
                        data_row.append(f"{value:{format_spec}}")

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

    def print_standings(self):
        """Print the current standings table in a clean, ink-friendly, professional format with a polished legend."""
        from gambitpairing.utils.print import (
            PrintOptionsDialog,
            TournamentPrintUtils,
        )

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

            # Build title with optional tournament name
            main_title = "Standings"
            if include_tournament_name and tournament_name:
                main_title += f" - {tournament_name}"

            tb_keys = []
            tb_legend = []
            for i, tb_key in enumerate(self.tournament.tiebreak_order):
                short = f"TB{i+1}"
                tb_keys.append(short)
                tb_legend.append((short, TIEBREAK_NAMES.get(tb_key, tb_key.title())))
            html = f"""
            <html>
            <head>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        color: #000;
                        background: #fff;
                        margin: 0;
                        padding: 0;
                    }}
                    h2 {{
                        text-align: center;
                        margin: 0 0 0.5em 0;
                        font-size: 1.35em;
                        font-weight: normal;
                        letter-spacing: 0.03em;
                    }}
                    .subtitle {{
                        text-align: center;
                        font-size: 1.05em;
                        margin-bottom: 1.2em;
                    }}
                    table.standings {{
                        border-collapse: collapse;
                        width: 100%;
                        margin: 0 auto 1.5em auto;
                    }}
                    table.standings th, table.standings td {{
                        border: 1px solid #222;
                        padding: 6px 10px;
                        text-align: center;
                        font-size: 11pt;
                        white-space: nowrap;
                    }}
                    table.standings th {{
                        font-weight: bold;
                        background: none;
                    }}
                    .legend {{
                        width: 100%;
                        margin: 0 auto 1.5em auto;
                        font-size: 10.5pt;
                        color: #222;
                        border: 1px solid #bbb;
                        background: none;
                        padding: 8px 12px;
                        text-align: left;
                    }}
                    .legend-title {{
                        font-weight: bold;
                        font-size: 11pt;
                        margin-bottom: 0.3em;
                        display: block;
                        letter-spacing: 0.02em;
                    }}
                    .legend-table {{
                        border-collapse: collapse;
                        margin-top: 0.2em;
                    }}
                    .legend-table td {{
                        border: none;
                        padding: 2px 10px 2px 0;
                        font-size: 10pt;
                        vertical-align: top;
                    }}
                    .footer {{
                        text-align: center;
                        font-size: 9pt;
                        margin-top: 2em;
                        color: #888;
                        letter-spacing: 0.04em;
                    }}
                </style>
            </head>
            <body>
                <h2>{main_title}</h2>
                <div class="subtitle">{round_subtitle}</div>
                <div class="legend">
                    <span class="legend-title">Tiebreaker Legend</span>
                    <table class="legend-table">
            """
            for short, name in tb_legend:
                html += f"<tr><td><b>{short}</b></td><td>{name}</td></tr>"
            html += """
                    </table>
                </div>
                <table class="standings">
                    <tr>
                        <th style="width:6%;">#</th>
                        <th style="width:32%;">Player</th>
                        <th style="width:10%;">Score</th>
            """
            for short in tb_keys:
                html += f'<th style="width:7%;">{short}</th>'
            html += "</tr>"
            # --- Table Rows ---
            for row in range(self.table_standings.rowCount()):
                html += "<tr>"
                for col in range(self.table_standings.columnCount()):
                    item = self.table_standings.item(row, col)
                    cell = item.text() if item else ""
                    # Rank and Score columns bold
                    if col == 0 or col == 2:
                        html += f'<td style="font-weight:bold;">{cell}</td>'
                    else:
                        html += f"<td>{cell}</td>"
                html += "</tr>"
            html += f"""
                </table>
                <div class="footer">
                    Printed by Gambit Pairing &mdash; {QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm")}
                </div>
            </body>
            </html>
            """
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
