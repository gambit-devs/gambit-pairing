import logging
from typing import List, Optional, Tuple

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt, pyqtSignal

from gambitpairing.constants import (
    BYE_SCORE,
    DRAW_SCORE,
    LOSS_SCORE,
    RESULT_BLACK_WIN,
    RESULT_DRAW,
    RESULT_WHITE_WIN,
    WIN_SCORE,
)
from gambitpairing.gui.views.tournament.components.tournament_widgets import (
    ResultSelector,
)
from gambitpairing.models.player import Player
from gambitpairing.utils import setup_logger

logger = setup_logger(__name__)


class PairingsTable(QtWidgets.QWidget):
    """
    Widget for displaying pairings and entering results.
    Includes the pairings table and the bye player information bar.
    """

    context_menu_requested = pyqtSignal(QtCore.QPoint)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "PairingsTableContainer")

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ===== PAIRINGS TABLE =====
        self.table = QtWidgets.QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Board", "White", "Black", "Result"])
        self.table.setProperty("class", "PairingsTable")

        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.context_menu_requested.emit)

        # Increase row height for a more spacious table
        self.table.verticalHeader().setDefaultSectionSize(65)

        # Configure column sizing modes
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.Stretch)
        # Use ResizeToContents for the result column to ensure it fits the buttons
        header.setSectionResizeMode(
            3, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )

        self.table.setColumnWidth(0, 70)  # Board column - wider for header

        layout.addWidget(self.table, 1)  # Give table stretch priority

        # ===== BYE INFO BAR =====
        self.bye_container = QtWidgets.QWidget()
        self.bye_container.setProperty("class", "ByeInfoBar")
        bye_layout = QtWidgets.QHBoxLayout(self.bye_container)
        bye_layout.setContentsMargins(16, 12, 16, 12)
        bye_layout.setSpacing(8)

        bye_icon = QtWidgets.QLabel("👤")
        bye_icon.setProperty("class", "ByeIcon")
        bye_layout.addWidget(bye_icon)

        self.lbl_bye = QtWidgets.QLabel("Bye: None")
        self.lbl_bye.setProperty("class", "ByeLabel")
        bye_layout.addWidget(self.lbl_bye)
        bye_layout.addStretch()

        self.bye_container.hide()
        layout.addWidget(self.bye_container)

    def display_pairings(
        self,
        pairings: List[Tuple[Player, Player]],
        bye_players: List[Player],
        current_round_index: int,
    ):
        self.table.clearContents()
        self.table.setRowCount(len(pairings))

        for row, pair in enumerate(pairings):
            # Support (Player, Player, color) tuples
            if len(pair) == 3:
                p1, p2, color = pair
                if color == "W":
                    white, black = p1, p2
                else:
                    white, black = p2, p1
            else:
                white, black = pair
                color = None

            # Board number column
            board_num = row + 1
            item_board = QtWidgets.QTableWidgetItem(str(board_num))
            item_board.setFlags(item_board.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item_board.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_board.setFont(
                QtGui.QFont(item_board.font().family(), -1, QtGui.QFont.Weight.Bold)
            )
            self.table.setItem(row, 0, item_board)

            # White player column
            item_white = QtWidgets.QTableWidgetItem(
                f"{white.name} ({white.rating})"
                + (" (I)" if not white.is_active else "")
            )
            item_white.setFlags(item_white.flags() & ~Qt.ItemFlag.ItemIsEditable)
            color_info = f"Color: {color}" if color else ""
            item_white.setToolTip(
                f"ID: {white.id}\nColor History: {' '.join(c or '_' for c in white.color_history)}\n{color_info}"
            )
            if not white.is_active:
                item_white.setForeground(QtGui.QColor("gray"))
            self.table.setItem(row, 1, item_white)

            # Black player column
            item_black = QtWidgets.QTableWidgetItem(
                f"{black.name} ({black.rating})"
                + (" (I)" if not black.is_active else "")
            )
            item_black.setFlags(item_black.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item_black.setToolTip(
                f"ID: {black.id}\nColor History: {' '.join(c or '_' for c in black.color_history)}"
            )
            if not black.is_active:
                item_black.setForeground(QtGui.QColor("gray"))
            self.table.setItem(row, 2, item_black)

            # Result selector widget
            result_selector = ResultSelector()
            result_selector.setProperty("row", row)
            result_selector.setProperty("white_id", white.id)
            result_selector.setProperty("black_id", black.id)

            # Auto-set result for inactive players
            if not white.is_active and not black.is_active:
                result_selector.setResult(RESULT_DRAW)  # 0-0 or F-F
            elif not white.is_active:
                result_selector.setResult(RESULT_BLACK_WIN)  # Black wins by forfeit
            elif not black.is_active:
                result_selector.setResult(RESULT_WHITE_WIN)  # White wins by forfeit

            self.table.setCellWidget(row, 3, result_selector)

        # Handle bye players display
        if bye_players:
            if len(bye_players) == 1:
                player = bye_players[0]
                status = " (Inactive)" if not player.is_active else ""
                bye_score_info = BYE_SCORE if player.is_active else 0.0
                self.lbl_bye.setText(
                    f"{player.name} ({player.rating}){status} receives {bye_score_info} point"
                )
            else:
                active_byes = [p for p in bye_players if p.is_active]
                inactive_byes = [p for p in bye_players if not p.is_active]

                player_details = []
                for player in bye_players:
                    status = " (Inactive)" if not player.is_active else ""
                    player_details.append(f"{player.name} ({player.rating}){status}")

                bye_text = ", ".join(player_details)

                if active_byes and inactive_byes:
                    bye_text += f" — {len(active_byes)} receive {BYE_SCORE}pts, {len(inactive_byes)} receive 0pts"
                elif active_byes:
                    bye_text += f" — Each receives {BYE_SCORE} point{'s' if BYE_SCORE != 1 else ''}"
                elif inactive_byes:
                    bye_text += " — Each receives 0 points"

                self.lbl_bye.setText(bye_text)

            self.bye_container.show()
        else:
            self.lbl_bye.setText("No bye this round")
            self.bye_container.hide()

    def get_results(self) -> Tuple[Optional[List[Tuple[str, str, float]]], bool]:
        results_data = []
        all_entered = True
        if (
            self.table.rowCount() == 0 and not self.bye_container.isVisible()
        ):  # No pairings, no bye
            return (
                [],
                True,
            )  # Valid state of no results to record

        for row in range(self.table.rowCount()):
            result_selector = self.table.cellWidget(row, 3)  # Column 3 for results
            if isinstance(result_selector, ResultSelector):
                result_const = result_selector.selectedResult()
                white_id = result_selector.property("white_id")
                black_id = result_selector.property("black_id")

                if not result_const:
                    all_entered = False
                    break

                white_score = -1.0
                if result_const == RESULT_WHITE_WIN:
                    white_score = WIN_SCORE
                elif result_const == RESULT_DRAW:
                    white_score = DRAW_SCORE
                elif result_const == RESULT_BLACK_WIN:
                    white_score = LOSS_SCORE

                if white_score >= 0 and white_id and black_id:
                    results_data.append((white_id, black_id, white_score))
                else:
                    logger.error(
                        f"Invalid result data in table row {row}: Result='{result_const}', W_ID='{white_id}', B_ID='{black_id}'"
                    )
                    if not white_id or not black_id:
                        return None, False
                    all_entered = False
                    break
            else:
                logger.error(
                    f"Missing ResultSelector in pairings table, row {row}. Table improperly configured."
                )
                return None, False
        return results_data, all_entered

    def clear(self):
        self.table.setRowCount(0)
        self.lbl_bye.setText("No bye this round")
        self.bye_container.hide()

    def rowCount(self):
        return self.table.rowCount()

    def itemAt(self, pos):
        return self.table.itemAt(pos)

    def cellWidget(self, row, col):
        return self.table.cellWidget(row, col)

    def viewport(self):
        return self.table.viewport()

    def item(self, row, col):
        return self.table.item(row, col)
