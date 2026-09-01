"""Spreadsheet-style pairings and result-entry table for the Rounds tab."""

# Gambit Pairing
# Copyright (C) 2025  Gambit Pairing developers
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt, pyqtSignal

from gambitpairing.constants import (
    BYE_SCORE,
    DRAW_SCORE,
    LOSS_SCORE,
    OUTCOME_DOUBLE_FORFEIT,
    OUTCOME_FORFEIT_WIN,
    OUTCOME_NORMAL_GAME,
    RESULT_BLACK_FORFEIT_WIN,
    RESULT_BLACK_WIN,
    RESULT_DOUBLE_FORFEIT,
    RESULT_DRAW,
    RESULT_WHITE_FORFEIT_WIN,
    RESULT_WHITE_WIN,
    WIN_SCORE,
)
from gambitpairing.gui.ui_loader import load_ui_into, required_child
from gambitpairing.models.player import Player
from gambitpairing.utils import setup_logger

from .result_selector import ResultSelector

logger = setup_logger(__name__)


class PairingsTable(QtWidgets.QWidget):
    """Display pairings and, in compact mode, provide keyboard-first entry.

    ``compact=True`` is used by the redesigned Rounds tab.  The default keeps
    the legacy widget presentation available to older callers while sharing
    the same result and persistence API.
    """

    context_menu_requested = pyqtSignal(QtCore.QPoint)
    result_changed = pyqtSignal(int, str, str)
    result_undone = pyqtSignal(int, str)
    selection_changed = pyqtSignal(int)

    def __init__(self, parent=None, compact: bool = False):
        super().__init__(parent)
        load_ui_into(self, "pairings_table.ui")

        self._compact = compact
        self._editable = True
        self._show_ratings = False
        self._players_by_row: Dict[int, Tuple[Player, Player]] = {}
        self._row_metadata: Dict[int, Dict[str, Any]] = {}
        self._result_history: List[Tuple[int, str, str]] = []
        self._suppress_result_events = False

        self.table = required_child(self, QtWidgets.QTableWidget, "table")
        self.table.setRowCount(0)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Board", "White", "Black", "Result"])
        for column in (0, 3):
            header_item = self.table.horizontalHeaderItem(column)
            if header_item is not None:
                header_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.context_menu_requested.emit)
        self.table.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.table.currentCellChanged.connect(self._on_current_cell_changed)
        self.table.cellClicked.connect(self._on_cell_clicked)
        self.table.installEventFilter(self)
        self.table.viewport().installEventFilter(self)

        if compact:
            self.table.setSelectionBehavior(
                QtWidgets.QAbstractItemView.SelectionBehavior.SelectItems
            )
            self.table.setSelectionMode(
                QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
            )
            self.table.verticalHeader().setDefaultSectionSize(32)
            self.table.verticalHeader().setMinimumSectionSize(30)
            self.table.setSizeAdjustPolicy(
                QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents
            )
        else:
            self.table.setSelectionBehavior(
                QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
            )
            self.table.verticalHeader().setDefaultSectionSize(65)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(
            3,
            QtWidgets.QHeaderView.ResizeMode.Fixed
            if compact
            else QtWidgets.QHeaderView.ResizeMode.ResizeToContents,
        )
        self.table.setColumnWidth(0, 62 if compact else 70)
        if compact:
            self.table.setColumnWidth(3, 96)

        self.bye_container = required_child(self, QtWidgets.QWidget, "bye_container")
        self.bye_icon = required_child(self, QtWidgets.QLabel, "bye_icon")
        self.lbl_bye = required_child(self, QtWidgets.QLabel, "lbl_bye")
        self.bye_container.hide()

    @property
    def compact(self) -> bool:
        return self._compact

    def display_pairings(
        self,
        pairings: List[Tuple[Player, Player]],
        bye_players: List[Player],
        current_round_index: int,
        results: Optional[Sequence[Any]] = None,
        editable: bool = True,
    ):
        """Populate the table with pairings, results, and optional bye row."""
        self._editable = editable
        self._players_by_row.clear()
        self._row_metadata.clear()
        self._result_history.clear()
        self._suppress_result_events = True

        bye_player = bye_players[0] if bye_players else None
        row_count = len(pairings) + (1 if self._compact and bye_player else 0)
        self.table.clearContents()
        self.table.setRowCount(row_count)

        result_map = self._build_result_map(results or [])
        fallback_numbers: Dict[str, int] = {}
        next_fallback_number = 1

        for row, pair in enumerate(pairings):
            white, black, color = self._normalise_pair(pair)
            for player in (white, black):
                if player.id not in fallback_numbers:
                    fallback_numbers[player.id] = next_fallback_number
                    next_fallback_number += 1

            self._players_by_row[row] = (white, black)
            self._row_metadata[row] = {
                "white_id": white.id,
                "black_id": black.id,
                "is_bye": False,
                "board": row + 1,
            }

            self.table.setItem(row, 0, self._board_item(row + 1))
            self.table.setItem(
                row,
                1,
                self._player_item(
                    white,
                    fallback_numbers[white.id],
                    color_info=f"Color: {color}" if color else "",
                ),
            )
            self.table.setItem(
                row,
                2,
                self._player_item(black, fallback_numbers[black.id]),
            )

            selector = ResultSelector(compact=self._compact)
            selector.setProperty("row", row)
            selector.setProperty("white_id", white.id)
            selector.setProperty("black_id", black.id)
            selector.result_changed.connect(
                lambda new, previous, row=row: self._on_result_changed(
                    row, new, previous
                )
            )
            selector.activated.connect(
                lambda row=row: self._activate_result_cell(row)
            )
            selector.key_pressed.connect(
                lambda key, text, modifiers, row=row: self._handle_selector_key(
                    row, key, text, modifiers
                )
            )
            selector.installEventFilter(self)
            selector.menu_button.installEventFilter(self)

            result_constant = result_map.get((white.id, black.id), "")
            if not result_constant:
                result_constant = self._automatic_result_for_inactive_players(
                    white, black
                )
            selector.setResult(result_constant, emit=False)
            selector.setEditable(self._compact and editable or not self._compact)
            self.table.setCellWidget(row, 3, selector)

        if bye_player:
            self._add_bye_row(
                len(pairings),
                bye_player,
                fallback_numbers.get(bye_player.id, next_fallback_number),
            )

        self._update_bye_bar(bye_players)
        self._suppress_result_events = False

        if self._compact:
            self.bye_container.hide()
            if pairings:
                self.table.setCurrentCell(0, 3)
                self._update_selected_result_cell()
        elif pairings:
            self.table.setCurrentCell(0, 0)

    def _normalise_pair(
        self, pair: Tuple[Player, Player] | Tuple[Player, Player, str]
    ) -> Tuple[Player, Player, Optional[str]]:
        if len(pair) == 3:
            p1, p2, color = pair
            return (p1, p2, color) if color == "W" else (p2, p1, color)
        white, black = pair
        return white, black, None

    def _board_item(self, board_number: int) -> QtWidgets.QTableWidgetItem:
        item = QtWidgets.QTableWidgetItem(str(board_number))
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item

    def _player_number(self, player: Player, fallback: int) -> int:
        return int(
            getattr(player, "pairing_number", None)
            or getattr(player, "bsn", None)
            or fallback
        )

    def _player_item(
        self,
        player: Player,
        fallback_number: int,
        color_info: str = "",
    ) -> QtWidgets.QTableWidgetItem:
        number = self._player_number(player, fallback_number)
        if self._compact:
            text = f"#{number} {player.name}"
            if self._show_ratings:
                text += f" ({player.rating})"
        else:
            text = f"{player.name} ({player.rating})"
        if not player.is_active:
            text += " (I)"

        item = QtWidgets.QTableWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        item.setToolTip(
            f"ID: {player.id}\n"
            f"Color History: {' '.join(str(c or '_') for c in player.color_history)}"
            + (f"\n{color_info}" if color_info else "")
        )
        if not player.is_active:
            item.setForeground(QtGui.QColor("gray"))
        return item

    def _add_bye_row(
        self,
        row: int,
        player: Player,
        fallback_number: int,
    ) -> None:
        number = self._player_number(player, fallback_number)
        score = BYE_SCORE if player.is_active else 0.0
        score_text = f"{score:g} point" if score == 1 else f"{score:g} points"
        board = QtWidgets.QTableWidgetItem("—")
        white = QtWidgets.QTableWidgetItem(
            f"#{number} {player.name}" + (" (I)" if not player.is_active else "")
        )
        black = QtWidgets.QTableWidgetItem("— Bye —")
        result = QtWidgets.QTableWidgetItem(score_text)
        for item in (board, white, black, result):
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item.setBackground(QtGui.QColor("#fff7df"))
            item.setForeground(QtGui.QColor("#805b12"))
            font = item.font()
            font.setItalic(True)
            item.setFont(font)
        board.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        result.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, 0, board)
        self.table.setItem(row, 1, white)
        self.table.setItem(row, 2, black)
        self.table.setItem(row, 3, result)
        self._row_metadata[row] = {
            "is_bye": True,
            "bye_player_id": player.id,
            "board": None,
        }
        self.table.setRowHeight(row, 30)

    def _update_bye_bar(self, bye_players: List[Player]) -> None:
        if not bye_players:
            self.lbl_bye.setText("No bye this round")
            self.bye_container.hide()
            return
        details = []
        for player in bye_players:
            score = BYE_SCORE if player.is_active else 0.0
            details.append(f"{player.name} ({player.rating}) — {score:g} point")
        self.lbl_bye.setText("; ".join(details))
        if self._compact:
            self.bye_container.hide()
        else:
            self.bye_container.show()

    def _build_result_map(self, results: Sequence[Any]) -> Dict[Tuple[str, str], str]:
        result_map: Dict[Tuple[str, str], str] = {}
        for result in results:
            if hasattr(result, "white_id"):
                white_id = result.white_id
                black_id = result.black_id
                result_map[(white_id, black_id)] = self._result_constant_from_model(
                    result
                )
                continue
            if len(result) < 3:
                continue
            white_id, black_id, white_score = result[:3]
            outcome = result[3] if len(result) > 3 and isinstance(result[3], str) else OUTCOME_NORMAL_GAME
            if len(result) > 4 and isinstance(result[4], str):
                outcome = result[4]
            result_map[(white_id, black_id)] = self._result_constant_from_score(
                float(white_score), outcome
            )
        return result_map

    @staticmethod
    def _result_constant_from_model(result: Any) -> str:
        return PairingsTable._result_constant_from_score(
            float(result.white_score), getattr(result, "outcome_type", OUTCOME_NORMAL_GAME)
        )

    @staticmethod
    def _result_constant_from_score(white_score: float, outcome_type: str) -> str:
        if outcome_type == OUTCOME_DOUBLE_FORFEIT:
            return RESULT_DOUBLE_FORFEIT
        if outcome_type == OUTCOME_FORFEIT_WIN:
            return (
                RESULT_WHITE_FORFEIT_WIN
                if white_score > DRAW_SCORE
                else RESULT_BLACK_FORFEIT_WIN
            )
        if white_score > DRAW_SCORE:
            return RESULT_WHITE_WIN
        if white_score < DRAW_SCORE:
            return RESULT_BLACK_WIN
        return RESULT_DRAW

    @staticmethod
    def _automatic_result_for_inactive_players(
        white: Player, black: Player
    ) -> str:
        if not white.is_active and not black.is_active:
            return RESULT_DOUBLE_FORFEIT
        if not white.is_active:
            return RESULT_BLACK_FORFEIT_WIN
        if not black.is_active:
            return RESULT_WHITE_FORFEIT_WIN
        return ""

    def _on_result_changed(self, row: int, new: str, previous: str) -> None:
        if self._suppress_result_events or new == previous:
            return
        if not self._editable or self._row_metadata.get(row, {}).get("is_bye"):
            return
        self._result_history.append((row, previous, new))
        self.result_changed.emit(row, new, previous)

    def _activate_result_cell(self, row: int) -> None:
        if 0 <= row < self.table.rowCount() and not self._row_metadata.get(row, {}).get(
            "is_bye"
        ):
            self.table.setCurrentCell(row, 3)
            self.table.setFocus(Qt.FocusReason.MouseFocusReason)

    def _on_cell_clicked(self, row: int, column: int) -> None:
        if column == 3 and not self._row_metadata.get(row, {}).get("is_bye"):
            self._activate_result_cell(row)

    def _on_current_cell_changed(
        self,
        current_row: int,
        current_column: int,
        _previous_row: int,
        _previous_column: int,
    ) -> None:
        self._update_selected_result_cell()
        if current_column == 3 and current_row >= 0:
            if not self._row_metadata.get(current_row, {}).get("is_bye"):
                self.selection_changed.emit(current_row)

    def _update_selected_result_cell(self) -> None:
        for row in range(self.table.rowCount()):
            selector = self.table.cellWidget(row, 3)
            if not isinstance(selector, ResultSelector):
                continue
            selected = row == self.table.currentRow() and self.table.currentColumn() == 3
            selector.setProperty("selected", selected)
            selector.menu_button.setProperty("selected", selected)
            selector.menu_button.style().unpolish(selector.menu_button)
            selector.menu_button.style().polish(selector.menu_button)
            selector.style().unpolish(selector)
            selector.style().polish(selector)

    def _handle_selector_key(
        self, row: int, key: int, text: str, modifiers: int
    ) -> None:
        self._handle_result_key(row, key, text, modifiers)

    def _handle_result_key(
        self, row: int, key: int, text: str, modifiers: int = 0
    ) -> bool:
        if row < 0 or row >= self.table.rowCount():
            return False
        if self._row_metadata.get(row, {}).get("is_bye"):
            return False
        self.table.setCurrentCell(row, 3)

        key_enum = Qt.Key(key)
        modifier_flags = Qt.KeyboardModifier(modifiers)
        if modifier_flags & Qt.KeyboardModifier.ControlModifier and key_enum == Qt.Key.Key_Z:
            return self.undo_last_edit()

        if key_enum in {Qt.Key.Key_Up, Qt.Key.Key_Down}:
            direction = -1 if key_enum == Qt.Key.Key_Up else 1
            self._move_result_selection(row, direction)
            return True
        if key_enum in {Qt.Key.Key_Return, Qt.Key.Key_Enter}:
            self._commit_and_advance(row)
            return True
        if key_enum in {Qt.Key.Key_Delete, Qt.Key.Key_Backspace}:
            self._set_result(row, "")
            return True

        normalized = text.strip().upper()
        if normalized == "1":
            self._set_result(row, RESULT_WHITE_WIN)
            self._move_result_selection(row, 1)
            return True
        if normalized == "0":
            self._set_result(row, RESULT_BLACK_WIN)
            self._move_result_selection(row, 1)
            return True
        if key_enum == Qt.Key.Key_Equal or normalized in {"D", "="}:
            self._set_result(row, RESULT_DRAW)
            self._move_result_selection(row, 1)
            return True
        return False

    def _set_result(self, row: int, result: str) -> None:
        selector = self.table.cellWidget(row, 3)
        if isinstance(selector, ResultSelector) and self._editable:
            selector.setResult(result)

    def _move_result_selection(self, row: int, direction: int) -> None:
        target = row + direction
        while 0 <= target < self.table.rowCount():
            if not self._row_metadata.get(target, {}).get("is_bye"):
                self.table.setCurrentCell(target, 3)
                selector = self.table.cellWidget(target, 3)
                if isinstance(selector, ResultSelector):
                    selector.setFocus(Qt.FocusReason.OtherFocusReason)
                return
            target += direction

    def _commit_and_advance(self, row: int) -> None:
        self._move_result_selection(row, 1)

    def undo_last_edit(self) -> bool:
        """Undo the most recent cell edit, if there is one."""
        if not self._editable or not self._result_history:
            return False
        row, previous, current = self._result_history.pop()
        selector = self.table.cellWidget(row, 3)
        if not isinstance(selector, ResultSelector):
            return False
        self._suppress_result_events = True
        selector.setResult(previous, emit=False)
        self._suppress_result_events = False
        self.result_changed.emit(row, previous, current)
        self.result_undone.emit(row, previous)
        self.table.setCurrentCell(row, 3)
        return True

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if event.type() == QtCore.QEvent.Type.KeyPress:
            key_event = event
            if isinstance(key_event, QtGui.QKeyEvent):
                if watched is self.table or watched is self.table.viewport():
                    row = self.table.currentRow()
                    if self.table.currentColumn() == 3 and self._handle_result_key(
                        row,
                        key_event.key(),
                        key_event.text(),
                        key_event.modifiers().value,
                    ):
                        key_event.accept()
                        return True
                elif isinstance(watched, ResultSelector):
                    row = watched.property("row")
                    if isinstance(row, int) and self._handle_result_key(
                        row,
                        key_event.key(),
                        key_event.text(),
                        key_event.modifiers().value,
                    ):
                        key_event.accept()
                        return True
                elif watched is not None:
                    row = watched.property("row")
                    if isinstance(row, int) and self._handle_result_key(
                        row,
                        key_event.key(),
                        key_event.text(),
                        key_event.modifiers().value,
                    ):
                        key_event.accept()
                        return True
        if event.type() == QtCore.QEvent.Type.FocusIn:
            row = watched.property("row")
            if isinstance(row, int) and not self._row_metadata.get(row, {}).get(
                "is_bye"
            ):
                self.table.setCurrentCell(row, 3)
        return super().eventFilter(watched, event)

    def set_show_ratings(self, show: bool) -> None:
        """Toggle optional rating text without adding a rating column."""
        self._show_ratings = show
        if not self._compact:
            return
        for row, (white, black) in self._players_by_row.items():
            for column, player in ((1, white), (2, black)):
                item = self.table.item(row, column)
                if item is None:
                    continue
                fallback = getattr(player, "pairing_number", None) or getattr(
                    player, "bsn", None
                ) or row + 1
                item.setText(self._player_item(player, int(fallback)).text())

    def progress(self) -> Tuple[int, int]:
        """Return ``(entered, boards)`` excluding bye rows."""
        total = 0
        entered = 0
        for row, metadata in self._row_metadata.items():
            if metadata.get("is_bye"):
                continue
            total += 1
            selector = self.table.cellWidget(row, 3)
            if isinstance(selector, ResultSelector) and selector.selectedResult():
                entered += 1
        return entered, total

    def board_count(self) -> int:
        return self.progress()[1]

    def has_bye(self) -> bool:
        return any(metadata.get("is_bye") for metadata in self._row_metadata.values())

    def selected_board_number(self) -> Optional[int]:
        row = self.table.currentRow()
        metadata = self._row_metadata.get(row, {})
        return metadata.get("board") if not metadata.get("is_bye") else None

    def is_bye_row(self, row: int) -> bool:
        return bool(self._row_metadata.get(row, {}).get("is_bye"))

    def get_results(self) -> Tuple[Optional[List[tuple]], bool]:
        """Collect results as tuples accepted by ``Tournament.record_results``."""
        results_data: List[tuple] = []
        all_entered = True

        for row, metadata in self._row_metadata.items():
            if metadata.get("is_bye"):
                continue
            selector = self.table.cellWidget(row, 3)
            if not isinstance(selector, ResultSelector):
                logger.error("Missing ResultSelector in row %s", row)
                return None, False
            result_const = selector.selectedResult()
            if not result_const:
                all_entered = False
                continue

            white_id = metadata.get("white_id")
            black_id = metadata.get("black_id")
            if not white_id or not black_id:
                return None, False
            white_score = LOSS_SCORE
            outcome_type = OUTCOME_NORMAL_GAME
            if result_const in {RESULT_WHITE_WIN, RESULT_WHITE_FORFEIT_WIN}:
                white_score = WIN_SCORE
            elif result_const == RESULT_DRAW:
                white_score = DRAW_SCORE
            elif result_const in {RESULT_BLACK_WIN, RESULT_BLACK_FORFEIT_WIN}:
                white_score = LOSS_SCORE
            elif result_const == RESULT_DOUBLE_FORFEIT:
                white_score = LOSS_SCORE

            if result_const in {
                RESULT_WHITE_FORFEIT_WIN,
                RESULT_BLACK_FORFEIT_WIN,
            }:
                outcome_type = OUTCOME_FORFEIT_WIN
            elif result_const == RESULT_DOUBLE_FORFEIT:
                outcome_type = OUTCOME_DOUBLE_FORFEIT

            if outcome_type == OUTCOME_NORMAL_GAME:
                results_data.append((white_id, black_id, white_score))
            else:
                results_data.append((white_id, black_id, white_score, outcome_type))

        return results_data, all_entered

    def reset_display(self):
        """Remove all rows and reset the bye bar."""
        self.table.setRowCount(0)
        self._players_by_row.clear()
        self._row_metadata.clear()
        self._result_history.clear()
        self.lbl_bye.setText("No bye this round")
        self.bye_container.hide()

    def rowCount(self) -> int:
        return self.table.rowCount()

    def itemAt(self, pos: QtCore.QPoint) -> QtWidgets.QTableWidgetItem | None:
        return self.table.itemAt(pos)

    def cellWidget(self, row: int, col: int) -> QtWidgets.QWidget | None:
        return self.table.cellWidget(row, col)

    def viewport(self) -> QtWidgets.QWidget:
        viewport = self.table.viewport()
        assert viewport is not None
        return viewport

    def item(self, row: int, col: int) -> QtWidgets.QTableWidgetItem | None:
        return self.table.item(row, col)
