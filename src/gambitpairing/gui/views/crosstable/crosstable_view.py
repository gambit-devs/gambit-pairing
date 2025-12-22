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


from PyQt6 import QtGui, QtWidgets
from PyQt6.QtCore import Qt

from gambitpairing.constants import DRAW_SCORE, LOSS_SCORE, WIN_SCORE
from gambitpairing.gui.notournament_placeholder import NoTournamentPlaceholder
from gambitpairing.gui.widgets.header import TabHeader


class CrosstableView(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tournament = None
        self.main_layout = QtWidgets.QVBoxLayout(self)

        # Header
        self.header = TabHeader("Crosstable")
        self.main_layout.addWidget(self.header)

        self.crosstable_group = QtWidgets.QGroupBox()
        self.crosstable_group.setStyleSheet(
            "QGroupBox { border: none; margin-top: 0px; }"
        )
        crosstable_layout = QtWidgets.QVBoxLayout(self.crosstable_group)
        crosstable_layout.setContentsMargins(0, 0, 0, 0)

        self.table_crosstable = QtWidgets.QTableWidget(0, 0)
        self.table_crosstable.setToolTip("Grid showing results between players.")
        self.table_crosstable.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table_crosstable.setAlternatingRowColors(True)
        font = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.FixedFont)
        self.table_crosstable.setFont(font)
        crosstable_layout.addWidget(self.table_crosstable)
        self.main_layout.addWidget(self.crosstable_group)

        # Add no tournament placeholder
        self.no_tournament_placeholder = NoTournamentPlaceholder(self, "Crosstable")
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
        self.update_ui_state()
        self._update_visibility()

    def _update_visibility(self):
        """Show/hide content based on tournament existence."""
        if not self.tournament:
            self.no_tournament_placeholder.show()
            self.crosstable_group.hide()
        else:
            self.no_tournament_placeholder.hide()
            self.crosstable_group.show()

    def update_crosstable(self):
        self._update_visibility()

        if not self.tournament or not self.tournament.players:
            return

        sorted_players = self.tournament.get_standings()
        if not sorted_players:
            self.table_crosstable.setRowCount(0)
            self.table_crosstable.setColumnCount(0)
            return

        player_id_to_rank_map = {p.id: i for i, p in enumerate(sorted_players)}
        n = len(sorted_players)

        self.table_crosstable.setRowCount(n)
        self.table_crosstable.setColumnCount(n + 3)  # Num, Name, Score + Opponent Ranks

        headers = ["#", "Player", "Score"] + [str(i + 1) for i in range(n)]
        self.table_crosstable.setHorizontalHeaderLabels(headers)
        v_headers = [
            f"{i+1}. {p.name} ({p.rating or 'NR'})"
            for i, p in enumerate(sorted_players)
        ]
        self.table_crosstable.setVerticalHeaderLabels(v_headers)

        for r_idx, p1 in enumerate(sorted_players):
            rank_item = QtWidgets.QTableWidgetItem(str(r_idx + 1))
            rank_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_crosstable.setItem(r_idx, 0, rank_item)
            name_item = QtWidgets.QTableWidgetItem(f"{p1.name} ({p1.rating or 'NR'})")
            self.table_crosstable.setItem(r_idx, 1, name_item)
            score_item = QtWidgets.QTableWidgetItem(f"{p1.score:.1f}")
            score_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_crosstable.setItem(r_idx, 2, score_item)

            for round_num, opp_id_for_p1 in enumerate(p1.opponent_ids):
                if round_num >= len(p1.results):
                    continue
                result_char = ""
                color = None
                tooltip = ""
                if opp_id_for_p1 is None:
                    continue  # Byes not shown in grid
                elif opp_id_for_p1 in player_id_to_rank_map:
                    opp_rank_in_list = player_id_to_rank_map[opp_id_for_p1]
                    col_idx_for_opp = opp_rank_in_list + 3
                    result_val = p1.results[round_num]
                    color_played = p1.color_history[round_num]
                    opp_display_rank = opp_rank_in_list + 1
                    if result_val == WIN_SCORE:
                        result_char = f"+{opp_display_rank}"
                        color = QtGui.QColor("green")
                        tooltip = "Win"
                    elif result_val == DRAW_SCORE:
                        result_char = f"={opp_display_rank}"
                        color = QtGui.QColor("#888888")
                        tooltip = "Draw"
                    elif result_val == LOSS_SCORE:
                        result_char = f"-{opp_display_rank}"
                        color = QtGui.QColor("red")
                        tooltip = "Loss"
                    else:
                        result_char = f"?{opp_display_rank}"
                        color = QtGui.QColor("black")
                        tooltip = "Unknown"
                    if color_played == "White":
                        result_char += "w"
                        tooltip += " as White"
                    elif color_played == "Black":
                        result_char += "b"
                        tooltip += " as Black"
                    item = QtWidgets.QTableWidgetItem(result_char)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    if color:
                        item.setForeground(color)
                    if tooltip:
                        item.setToolTip(tooltip)
                    self.table_crosstable.setItem(r_idx, col_idx_for_opp, item)
            # Diagonal: player vs self
            diag_item = QtWidgets.QTableWidgetItem("X")
            diag_item.setBackground(QtGui.QColor(220, 220, 220))
            diag_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            font = diag_item.font()
            font.setBold(True)
            diag_item.setFont(font)
            diag_item.setToolTip("Player's own cell")
            self.table_crosstable.setItem(r_idx, r_idx + 3, diag_item)

        self.table_crosstable.resizeColumnsToContents()
        self.table_crosstable.resizeRowsToContents()

    def update_ui_state(self):
        self.update_crosstable()
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
