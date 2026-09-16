"""Tournament tab UI for managing tournament rounds and pairings."""

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


import logging
from typing import List, Optional, Tuple

from PyQt6 import QtCore, QtWidgets
from PyQt6.QtCore import Qt, pyqtSignal

from gambitpairing.controllers import (
    TournamentController,
)
from gambitpairing.gui.dialogs import ManualPairingDialog
from gambitpairing.gui.gui_utils import get_native_icon
from gambitpairing.gui.ui_loader import load_ui_into, required_child
from gambitpairing.gui.views.tournament.tournament_printing import (
    PairingsPrintRow,
    build_combined_tournament_print_html,
    build_page_separator,
    build_pairings_print_section,
    build_standings_print_section,
)
from gambitpairing.gui.views.tournament.tournament_view_workflow import (
    build_pairing_exception_prompt,
    build_pairing_generation_failure_prompt,
    build_recorded_round_view_update,
    build_reprepare_round_prompt,
    build_round_end_prompt,
    build_round_preparation_messages,
    build_tournament_view_state,
    format_generated_pairing_history_lines,
    format_manual_pairing_history_lines,
    format_recorded_result_history_lines,
    resolve_existing_round_pairings,
    undo_confirmation_message,
)
from gambitpairing.gui.widgets import (
    ResultSelector,
)
from gambitpairing.gui.widgets.header import TabHeader
from gambitpairing.gui.widgets.pairings_table import PairingsTable
from gambitpairing.gui.widgets.pre_tournament_start import (
    PreTournamentStart,
)
from gambitpairing.gui.widgets.round_controls import (
    RoundControlsWidget,
)
from gambitpairing.gui.widgets.tournament_placeholder import (
    TournamentPlaceholder,
)
from gambitpairing.models import (
    Player,
)
from gambitpairing.utils import setup_logger
from gambitpairing.utils.pairings_printer import PairingsPrinter

logger = setup_logger(__name__)


class TournamentView(QtWidgets.QWidget):
    def _check_minimum_players(self, for_preparation=False):
        """
        Shared minimum player/active player checks for both tournament start and round preparation.
        Returns True if checks pass, False if user cancels or not enough players.
        """
        check = self.controller.validate_minimum_players(
            for_preparation=for_preparation
        )
        title = "Prepare Error" if for_preparation else "Start Error"
        if not check.valid and not check.needs_confirmation:
            QtWidgets.QMessageBox.warning(
                self,
                title,
                check.error_message or "The tournament cannot proceed.",
            )
            return False
        if check.needs_confirmation:
            reply = QtWidgets.QMessageBox.warning(
                self,
                "Insufficient Players",
                check.confirmation_message
                or "The tournament has fewer players than recommended. Continue?",
                QtWidgets.QMessageBox.StandardButton.Yes
                | QtWidgets.QMessageBox.StandardButton.No,
                QtWidgets.QMessageBox.StandardButton.No,
            )
            if reply == QtWidgets.QMessageBox.StandardButton.No:
                return False
        return True

    status_message = pyqtSignal(str)
    history_message = pyqtSignal(str)
    dirty = pyqtSignal()
    round_completed = pyqtSignal(int)
    standings_update_requested = pyqtSignal()

    @property
    def current_round_index(self) -> int:
        """Return the controller-owned index of the next round to play."""
        return self.controller.current_round_index

    @current_round_index.setter
    def current_round_index(self, value: int) -> None:
        self.controller.set_current_round_index(max(0, int(value)))

    @property
    def last_recorded_results_data(self) -> List[tuple]:
        """Expose controller-owned undo data for the main-window bridge."""
        return self.controller.last_recorded_results_data

    @last_recorded_results_data.setter
    def last_recorded_results_data(self, value: List[tuple]) -> None:
        self.controller.last_recorded_results_data = list(value)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.controller = TournamentController()
        self.tournament = None
        self.displayed_round_index = 0
        self._rendered_round_index: Optional[int] = None
        self._final_summary_visible = False
        self.show_ratings = False

        # Create the printer helper; round state remains in the controller.
        self.printer = PairingsPrinter(self)

        load_ui_into(self, "tournament_view.ui")
        self.main_layout = required_child(self, QtWidgets.QVBoxLayout, "main_layout")
        header_layout = required_child(self, QtWidgets.QVBoxLayout, "header_layout")
        header_container = required_child(self, QtWidgets.QWidget, "header_container")
        header_container.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Maximum,
        )
        pre_tournament_layout = required_child(
            self, QtWidgets.QVBoxLayout, "pre_tournament_layout"
        )
        placeholder_layout = required_child(
            self, QtWidgets.QVBoxLayout, "placeholder_layout"
        )

        # ===== TOURNAMENT INFO HEADER =====
        self.header = TabHeader("Rounds")
        self.header.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Maximum,
        )
        # ``round_navigation`` is part of the Designer-owned header layout.
        # Insert the runtime header above it so the view only wires behavior.
        header_layout.insertWidget(0, self.header)
        self._setup_round_navigation()

        # ===== ROUND CARD CONTAINER =====
        # This is the main content area that holds pairings and results
        self._setup_round_card()

        # ===== PRE-TOURNAMENT WIDGET =====
        self.pre_tournament_start_widget = PreTournamentStart(self)
        self.pre_tournament_start_widget.start_requested.connect(self.start_tournament)
        self.pre_tournament_start_widget.hide()
        pre_tournament_layout.addWidget(self.pre_tournament_start_widget)

        # ===== NO TOURNAMENT PLACEHOLDER =====
        self.tournament_placeholder = TournamentPlaceholder(self, "Rounds")
        self.tournament_placeholder.create_tournament_requested.connect(
            self._trigger_create_tournament
        )
        self.tournament_placeholder.import_tournament_requested.connect(
            self._trigger_import_tournament
        )
        self.tournament_placeholder.hide()
        placeholder_layout.addWidget(self.tournament_placeholder)

        # Set initial UI state
        self.update_ui_state()

    def _setup_round_navigation(self) -> None:
        """Wire the Designer-owned round selector and action row."""
        self.round_navigation = required_child(
            self, QtWidgets.QWidget, "round_navigation"
        )
        self.btn_previous_round = required_child(
            self, QtWidgets.QToolButton, "btn_previous_round"
        )
        self.btn_next_round = required_child(
            self, QtWidgets.QToolButton, "btn_next_round"
        )
        self.round_selector = required_child(
            self, QtWidgets.QToolButton, "round_selector"
        )
        self.lbl_round_status = required_child(
            self, QtWidgets.QLabel, "lbl_round_status"
        )
        self.lbl_round_summary = required_child(
            self, QtWidgets.QLabel, "lbl_round_summary"
        )
        self.btn_edit_results = required_child(
            self, QtWidgets.QPushButton, "btn_edit_results"
        )
        self.btn_view = required_child(self, QtWidgets.QToolButton, "btn_view")
        self.btn_pairing_actions = required_child(
            self, QtWidgets.QToolButton, "btn_pairing_actions"
        )

        self.btn_previous_round.clicked.connect(lambda: self._navigate_round(-1))
        self.btn_next_round.clicked.connect(lambda: self._navigate_round(1))
        for button, theme_name, fallback, label in (
            (
                self.btn_previous_round,
                "go-previous",
                QtWidgets.QStyle.StandardPixmap.SP_ArrowLeft,
                "Previous round",
            ),
            (
                self.btn_next_round,
                "go-next",
                QtWidgets.QStyle.StandardPixmap.SP_ArrowRight,
                "Next round",
            ),
        ):
            button.setText("")
            button.setIcon(get_native_icon(theme_name, fallback))
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            button.setAutoRaise(True)
            button.setAccessibleName(label)
        self.btn_edit_results.clicked.connect(self._edit_selected_completed_round)

        round_menu = QtWidgets.QMenu(self.round_selector)
        self.round_selector.setMenu(round_menu)
        self.round_selector.setToolButtonStyle(
            QtCore.Qt.ToolButtonStyle.ToolButtonTextOnly
        )
        self.round_selector.setPopupMode(
            QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup
        )

        self._setup_pairing_actions_menu()

    def _setup_pairing_actions_menu(self) -> None:
        """Create the secondary pairing action menu without adding toolbar noise."""
        self.pairing_actions_menu = QtWidgets.QMenu(self.btn_pairing_actions)
        self.btn_pairing_actions.setMenu(self.pairing_actions_menu)
        for button in (self.btn_view, self.btn_pairing_actions):
            button.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextOnly)
            button.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)

        self.action_edit_displayed_pairings = self.pairing_actions_menu.addAction(
            "Edit pairings"
        )
        self.action_edit_displayed_pairings.triggered.connect(
            self._edit_displayed_pairings
        )
        self.action_repair_displayed_round = self.pairing_actions_menu.addAction(
            "Re-pair round"
        )
        self.action_repair_displayed_round.triggered.connect(
            self._repair_displayed_round
        )
        self.pairing_actions_menu.addSeparator()
        self.action_print_displayed_pairings = self.pairing_actions_menu.addAction(
            "Print pairings"
        )
        self.action_print_displayed_pairings.triggered.connect(
            lambda: self.open_print_dialog(
                default_pairings=True, default_standings=False
            )
        )

        self.view_menu = QtWidgets.QMenu(self.btn_view)
        self.btn_view.setMenu(self.view_menu)
        self.action_show_ratings = self.view_menu.addAction("Show Ratings")
        self.action_show_ratings.setCheckable(True)
        self.action_show_ratings.toggled.connect(self._toggle_show_ratings)

    def _navigate_round(self, direction: int) -> None:
        if not self.tournament:
            return
        total_rounds = self.tournament.num_rounds
        if total_rounds <= 0:
            return
        target = max(0, min(total_rounds - 1, self.displayed_round_index + direction))
        if target == self.displayed_round_index:
            return
        self._final_summary_visible = False
        self.displayed_round_index = target
        self._render_current_round()
        self.update_ui_state()

    def _select_round(self, round_index: int) -> None:
        if not self.tournament or not 0 <= round_index < self.tournament.num_rounds:
            return
        self._final_summary_visible = False
        self.displayed_round_index = round_index
        self._render_current_round()
        self.update_ui_state()

    def _round_status(self, round_index: int) -> str:
        round_data = self.controller.get_round_data(round_index)
        if round_data is None:
            return "Not Paired"
        if round_data.is_completed or round_index < self.current_round_index:
            return "Complete"
        if round_data.pairings:
            return "In Progress"
        return "Not Paired"

    def _update_round_navigation(self) -> None:
        if not self.tournament:
            self.round_navigation.hide()
            return

        total_rounds = self.tournament.num_rounds
        if total_rounds <= 0:
            self.round_navigation.hide()
            return

        index = max(0, min(total_rounds - 1, self.displayed_round_index))
        self.displayed_round_index = index
        menu = self.round_selector.menu()
        if menu is None:
            menu = QtWidgets.QMenu(self.round_selector)
            self.round_selector.setMenu(menu)
        else:
            menu.clear()
        for round_index in range(total_rounds):
            status = self._round_status(round_index)
            action = menu.addAction(f"Round {round_index + 1}   {status}")
            action.setCheckable(True)
            action.setChecked(round_index == index)
            action.triggered.connect(
                lambda _checked=False, round_index=round_index: self._select_round(
                    round_index
                )
            )
        self.round_selector.setText(f"Round {index + 1} of {total_rounds}")
        self.btn_previous_round.setEnabled(index > 0)
        self.btn_next_round.setEnabled(index < total_rounds - 1)
        displayed_status = (
            "Complete" if self._final_summary_visible else self._round_status(index)
        )
        self.lbl_round_status.setText(displayed_status)
        entered, total = self.pairings_table.progress()
        self.lbl_round_summary.setText(self._round_summary_text(entered, total))

        status = self._round_status(index)
        can_edit_latest = (
            status.startswith("Complete")
            and index == self.current_round_index - 1
            and not self._final_summary_visible
        )
        self.btn_edit_results.setVisible(can_edit_latest)
        self.btn_edit_results.setEnabled(can_edit_latest)
        self.action_edit_displayed_pairings.setEnabled(
            status == "In Progress" and index == self.current_round_index
        )
        self.action_repair_displayed_round.setEnabled(
            index == self.current_round_index
            and status in {"In Progress", "Not Paired"}
            and not self._final_summary_visible
        )
        self.action_print_displayed_pairings.setEnabled(total > 0)

    def _render_current_round(self) -> None:
        """Render the selected round without changing tournament state."""
        if not self.tournament:
            self.pairings_table.reset_display()
            self.pairings_table.hide()
            self.lbl_empty_state.hide()
            self._rendered_round_index = None
            return

        if self._final_summary_visible:
            self.pairings_table.reset_display()
            self.pairings_table.hide()
            self.lbl_empty_state.setText(
                "All scheduled rounds are complete.\n"
                "Use View Final Standings to review the tournament."
            )
            self.lbl_empty_state.show()
            self._rendered_round_index = None
            return

        round_index = self.displayed_round_index
        if not self.controller.pairings_exist_for_round(round_index):
            self.pairings_table.reset_display()
            self.pairings_table.hide()
            self.lbl_empty_state.setText(
                f"Round {round_index + 1}\n\nThis round has not been paired yet."
            )
            self.lbl_empty_state.show()
            self._rendered_round_index = round_index
            return

        existing = resolve_existing_round_pairings(self.tournament, round_index)
        round_data = self.controller.get_round_data(round_index)
        is_editable = (
            round_index == self.current_round_index
            and round_data is not None
            and not round_data.is_completed
        )
        results = self.controller.get_round_results(round_index, pending=is_editable)

        self.pairings_table.set_show_ratings(self.show_ratings)
        self.pairings_table.show()
        self.pairings_table.display_pairings(
            existing.pairings,
            existing.bye_players,
            round_index,
            results=results,
            editable=is_editable,
            bye_type=round_data.bye_type if round_data is not None else "full",
        )
        self.lbl_empty_state.hide()
        self._rendered_round_index = round_index

    @staticmethod
    def _count_text(count: int, singular: str, plural: Optional[str] = None) -> str:
        label = singular if count == 1 else (plural or f"{singular}s")
        return f"{count} {label}"

    @classmethod
    def _round_summary_text(cls, entered: int, total: int) -> str:
        return (
            f"{cls._count_text(total, 'board')} · "
            f"{cls._count_text(entered, 'result')} entered"
        )

    def _on_board_selected(self, row: int) -> None:
        board = self.pairings_table.selected_board_number()
        if board is not None and self.current_round_index == self.displayed_round_index:
            self.status_message.emit(
                f"Round {self.displayed_round_index + 1} · Board {board} selected · "
                "Type 1, D, or 0 to enter result"
            )

    def _on_result_changed(self, row: int, result: str, previous: str) -> None:
        if (
            not self.tournament
            or self.displayed_round_index != self.current_round_index
        ):
            return
        results_data, _all_entered = self.pairings_table.get_results()
        if results_data is None:
            return
        if not self.controller.set_pending_results(
            self.current_round_index, results_data
        ):
            return
        self.dirty.emit()
        board = self.pairings_table.selected_board_number()
        board = board if board is not None else row + 1
        display_result = ResultSelector.formatResult(result) or "cleared"
        self.status_message.emit(
            f"Board {board} result changed to {display_result} · Ctrl+Z to undo"
        )
        self._update_round_progress()
        self.update_ui_state()

    def _on_result_undone(self, row: int, result: str) -> None:
        board = self.pairings_table.selected_board_number()
        self.status_message.emit(
            f"Board {board if board is not None else row + 1} result changed to "
            f"{ResultSelector.formatResult(result) or 'cleared'} · Ctrl+Z to undo"
        )

    def _update_round_progress(self) -> None:
        entered, total = self.pairings_table.progress()
        if total and entered == total:
            progress_text = "All results entered"
        elif total:
            result_label = "result" if total == 1 else "results"
            progress_text = (
                f"{entered} / {total} {result_label} entered · "
                f"{total - entered} remaining"
            )
        else:
            progress_text = "0 results entered"
        self.round_controls.set_progress(progress_text)
        self.lbl_round_summary.setText(self._round_summary_text(entered, total))

    def _toggle_show_ratings(self, checked: bool) -> None:
        self.show_ratings = checked
        self.pairings_table.set_show_ratings(checked)

    def _view_final_standings(self) -> None:
        main_window = self.window()
        if hasattr(main_window, "tabs") and hasattr(main_window, "standings_tab"):
            main_window.tabs.setCurrentWidget(main_window.standings_tab)

    def _setup_round_card(self):
        """Create the round card container with pairings table and action footer."""
        self.round_card = required_child(self, QtWidgets.QWidget, "round_card")
        pairings_layout = required_child(self, QtWidgets.QVBoxLayout, "pairings_layout")
        round_controls_layout = required_child(
            self, QtWidgets.QVBoxLayout, "round_controls_layout"
        )

        # ===== PAIRINGS TABLE =====
        self.pairings_table = PairingsTable(compact=True)
        self.pairings_table.context_menu_requested.connect(
            self.show_pairing_context_menu
        )
        self.pairings_table.result_changed.connect(self._on_result_changed)
        self.pairings_table.result_undone.connect(self._on_result_undone)
        self.pairings_table.selection_changed.connect(self._on_board_selected)
        pairings_layout.addWidget(self.pairings_table, 1)

        self.lbl_empty_state = QtWidgets.QLabel()
        self.lbl_empty_state.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_empty_state.setWordWrap(True)
        self.lbl_empty_state.hide()
        pairings_layout.addWidget(self.lbl_empty_state, 1)

        # ===== ACTION FOOTER =====
        self.round_controls = RoundControlsWidget()
        self.round_controls.start_requested.connect(self.start_tournament)
        self.round_controls.prepare_requested.connect(self.prepare_next_round)
        self.round_controls.record_requested.connect(self.record_and_advance)
        self.round_controls.undo_requested.connect(self.undo_last_results)
        self.round_controls.view_standings_requested.connect(self._view_final_standings)
        self.round_controls.set_keyboard_hints(
            "1  White win   D  Draw   0  Black win   Del  Clear   Enter  Next"
        )
        round_controls_layout.addWidget(self.round_controls)

    def set_tournament(self, tournament):
        """Set the tournament and update controller."""
        self.tournament = tournament
        self.controller.set_tournament(tournament)
        if tournament is None:
            self.current_round_index = 0
            self.displayed_round_index = 0
            self._rendered_round_index = None
            self._final_summary_visible = False
        self.controller.set_current_round_index(self.current_round_index)
        if tournament is not None and tournament.num_rounds:
            if self.current_round_index >= tournament.num_rounds:
                self.displayed_round_index = tournament.num_rounds - 1
                self._final_summary_visible = True
            else:
                self.displayed_round_index = max(0, self.current_round_index)
        self.update_ui_state()

    def set_current_round_index(self, idx):
        """Set the current round index and update controller."""
        self.current_round_index = idx
        if self.tournament and self.tournament.num_rounds:
            if idx >= self.tournament.num_rounds:
                self.displayed_round_index = self.tournament.num_rounds - 1
                self._final_summary_visible = True
            else:
                self.displayed_round_index = max(0, idx)
                self._final_summary_visible = False
        self.update_ui_state()

    def _prepare_round(self, round_index: int, for_preparation: bool = False) -> bool:
        """Logic for preparing a round (either starting tournament or preparing next round).

        Parameters
        ----------
        round_index : int
            The round index to prepare (0-based)
        for_preparation : bool
            Whether this is for round preparation (affects player checks)

        Returns
        -------
        bool
            True if round was prepared successfully, False otherwise
        """
        if not self._check_minimum_players(for_preparation=for_preparation):
            return False

        if round_index >= self.tournament.num_rounds:
            prompt = build_round_end_prompt()
            QtWidgets.QMessageBox.information(
                self,
                prompt.title,
                prompt.message,
            )
            self.update_ui_state()
            return False

        # Check if pairings for this round already exist
        display_round_number = round_index + 1
        messages = build_round_preparation_messages(display_round_number)
        if self.controller.pairings_exist_for_round(round_index):
            prompt = build_reprepare_round_prompt(round_index)
            reply = QtWidgets.QMessageBox.question(
                self,
                prompt.title,
                prompt.message,
                QtWidgets.QMessageBox.StandardButton.Yes
                | QtWidgets.QMessageBox.StandardButton.No,
                QtWidgets.QMessageBox.StandardButton.No,
            )
            if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                # Replacement is committed only after generation succeeds.
                pass
            else:
                # Just display existing pairings
                existing = resolve_existing_round_pairings(self.tournament, round_index)
                self.header.set_title("Rounds")
                self.display_pairings_for_input(existing.pairings, existing.bye_players)
                self.update_ui_state()
                return True

        # Check if this is a manual pairing tournament
        if self.controller.is_manual_pairing_system():
            self._handle_manual_pairing_round(display_round_number, round_index)
            return True

        self.status_message.emit(messages.started_status)
        try:
            from gambitpairing.controllers.tournament.pairing_job import (
                commit_pairing_document,
            )
            from gambitpairing.gui.pairing_job import generate_with_progress

            expected = self.tournament.to_dict()
            generation = generate_with_progress(self, expected, round_index)
            if generation.get("cancelled"):
                self.status_message.emit("Pairing cancelled. Original round preserved.")
                return False
            if generation.get("error"):
                prompt = build_pairing_generation_failure_prompt(display_round_number)
                QtWidgets.QMessageBox.critical(
                    self,
                    prompt.title,
                    generation["error"] or prompt.message,
                )
                self.status_message.emit(messages.error_status)
                self.update_ui_state()
                return False

            if generation.get("fallback_reason"):
                reply = QtWidgets.QMessageBox.question(
                    self,
                    "BBP unavailable",
                    f"{generation['fallback_reason']}\n\nUse the pairings generated by Gambit Dutch (Experimental)?",
                    QtWidgets.QMessageBox.StandardButton.Yes
                    | QtWidgets.QMessageBox.StandardButton.No,
                    QtWidgets.QMessageBox.StandardButton.No,
                )
                if reply != QtWidgets.QMessageBox.StandardButton.Yes:
                    return False
            engine = commit_pairing_document(self.tournament, expected, generation)
            pairings, bye_player = self.controller.get_round_pairings(round_index)
            self.history_message.emit(f"Round {display_round_number} engine: {engine}")

            self.header.set_title("Rounds")
            self.display_pairings_for_input(
                pairings, [bye_player] if bye_player else []
            )
            for line in format_generated_pairing_history_lines(
                display_round_number, pairings, bye_player
            ):
                self.history_message.emit(line)
            self.dirty.emit()
            self.status_message.emit(messages.ready_status)
        except Exception as e:
            logger.exception(
                "Error generating pairings for Round %s:",
                display_round_number,
            )
            prompt = build_pairing_exception_prompt(display_round_number, e)
            QtWidgets.QMessageBox.critical(
                self,
                prompt.title,
                prompt.message,
            )
            self.status_message.emit(messages.error_status)
            return False

        return True

    def start_tournament(self) -> None:
        if not self.tournament:
            QtWidgets.QMessageBox.warning(self, "Start Error", "No tournament loaded.")
            return

        reply = QtWidgets.QMessageBox.question(
            self,
            "Start Tournament",
            f"Start a {self.tournament.num_rounds}-round tournament with {len(self.tournament.players)} players?",
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.Yes,
        )
        if reply != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        # Use current_round_index (starting at 0 for Round 1)
        self._prepare_round(self.current_round_index, for_preparation=False)

    def prepare_next_round(self) -> None:
        if not self.tournament:
            return

        self._prepare_round(self.current_round_index, for_preparation=True)

    def prompt_repeat_pairing(self, player1, player2):
        msg = (
            f"No valid new opponent found for {player1.name}.\n"
            f"Would you like to allow a repeat pairing with {player2.name} to ensure all players are paired?"
        )
        reply = QtWidgets.QMessageBox.question(
            self,
            "Repeat Pairing Needed",
            msg,
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.Yes,
        )
        return reply == QtWidgets.QMessageBox.StandardButton.Yes

    def display_pairings_for_input(
        self, pairings: List[Tuple[Player, Player]], bye_players: List[Player]
    ):
        self.displayed_round_index = self.current_round_index
        self._final_summary_visible = False
        pending_results = self.controller.get_round_results(
            self.current_round_index, pending=True
        )
        round_data = self.controller.get_round_data(self.current_round_index)
        self.pairings_table.set_show_ratings(self.show_ratings)
        self.pairings_table.show()
        self.pairings_table.display_pairings(
            pairings,
            bye_players,
            self.current_round_index,
            results=pending_results,
            editable=True,
            bye_type=round_data.bye_type if round_data is not None else "full",
        )
        self.lbl_empty_state.hide()
        self._rendered_round_index = self.current_round_index
        self._update_round_navigation()
        self._update_round_progress()

    def reset_display(self):
        """Reset the UI to default state.

        Clears the pairings table and bye player label.
        """
        self.pairings_table.reset_display()
        self.pairings_table.hide()
        self.lbl_empty_state.hide()
        self._rendered_round_index = None
        if self.tournament:
            self.header.set_title("Rounds")
        else:
            self.header.set_title("No Tournament Loaded")

    def show_pairing_context_menu(self, pos: QtCore.QPoint):
        item = self.pairings_table.itemAt(pos)
        if not item or not self.tournament:
            return

        row = item.row()
        result_selector = self.pairings_table.cellWidget(row, 3)  # Column 3 for results
        if not isinstance(result_selector, ResultSelector):
            return

        menu = QtWidgets.QMenu(self)

        # Offer option to edit all pairings for all tournaments
        edit_all_action = menu.addAction("Edit Pairings...")
        menu.addSeparator()

        adjust_action = menu.addAction("Manually Adjust Pairing...")

        # Only allow adjustment for the current round before results are recorded
        can_adjust = self.controller.pairings_exist_for_round(self.current_round_index)
        adjust_action.setEnabled(can_adjust)
        edit_all_action.setEnabled(can_adjust)

        # Use exec() which returns the triggered action
        action = menu.exec(self.pairings_table.viewport().mapToGlobal(pos))

        if action == edit_all_action:
            self._edit_all_pairings()
        elif action == adjust_action:
            # Get current round pairings and bye
            existing_pairings = None
            existing_bye = None
            display_round_number = self.current_round_index + 1
            if self.controller.pairings_exist_for_round(self.current_round_index):
                existing = resolve_existing_round_pairings(
                    self.tournament, self.current_round_index
                )
                existing_pairings = existing.pairings
                existing_bye = existing.bye_player
            active_players = self.controller.get_active_players()
            dialog = ManualPairingDialog(
                active_players,
                existing_pairings,
                existing_bye,
                display_round_number,
                self,
                self.tournament,
            )

            # Connect signal to refresh player list when player status changes
            dialog.player_status_changed.connect(self._on_player_status_changed)

            dialog.exec()

    def _on_player_status_changed(self):
        """Handle when player status changes in manual pairing dialog."""
        # Emit signal to refresh player list in players tab
        self.standings_update_requested.emit()

    def record_and_advance(self) -> None:
        if not self.tournament:
            return

        # Results are finalized only for the live/current round. Historical
        # rounds remain read-only unless the existing last-round undo workflow
        # is explicitly used.
        if self.displayed_round_index != self.current_round_index:
            return
        round_index_to_record = self.current_round_index

        if not self.controller.pairings_exist_for_round(round_index_to_record):
            QtWidgets.QMessageBox.warning(
                self,
                "Record Error",
                "No pairings available to record results for this round index.",
            )
            return

        results_data, all_entered = self.get_results_from_table()
        if not all_entered:
            QtWidgets.QMessageBox.warning(
                self, "Incomplete Results", "Please enter a result for all pairings."
            )
            return
        if results_data is None:
            QtWidgets.QMessageBox.critical(
                self,
                "Input Error",
                "Error retrieving results from table. Cannot proceed.",
            )
            return

        try:
            recording = self.controller.record_results(
                round_index_to_record, results_data
            )
            if recording.success:
                self.last_recorded_results_data = list(
                    self.controller.last_recorded_results_data
                )

                for line in format_recorded_result_history_lines(
                    self.tournament, results_data, round_index_to_record
                ):
                    self.history_message.emit(line)

                # Advance current_round_index *after* successful recording and logging
                view_update = build_recorded_round_view_update(
                    self.tournament.num_rounds, round_index_to_record
                )
                self.current_round_index = self.controller.current_round_index
                if self.current_round_index >= self.tournament.num_rounds:
                    self.displayed_round_index = max(0, self.tournament.num_rounds - 1)
                    self._final_summary_visible = True
                else:
                    self.displayed_round_index = self.current_round_index
                    self._final_summary_visible = False
                # Notify main window of round advancement
                self.round_completed.emit(self.current_round_index)

                self.standings_update_requested.emit()
                self.status_message.emit(view_update.status_message)
                for line in view_update.history_lines:
                    self.history_message.emit(line)

                self.pairings_table.reset_display()
                self.lbl_empty_state.hide()
                self._rendered_round_index = None
                self.header.set_title("Rounds")

                self.dirty.emit()
            else:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Recording Warning",
                    recording.error_message
                    or "Some results may not have been recorded properly by the backend. Check logs and player status.",
                )

        except Exception as e:
            logging.exception(
                f"Error during record_and_advance for round {round_index_to_record+1}:"
            )
            QtWidgets.QMessageBox.critical(
                self, "Recording Error", f"Recording results failed:\n{e}"
            )
            self.status_message.emit("Error recording results.")
        finally:
            self.update_ui_state()

    def open_print_dialog(self, default_pairings=True, default_standings=False):
        """Show print options dialog and print selected documents."""
        from gambitpairing.gui.dialogs import PrintOptionsDialog

        if not self.tournament:
            return

        # Check what's available to print
        has_pairings = self.pairings_table.rowCount() > 0
        has_standings = self.current_round_index > 0  # Results have been recorded

        if not has_pairings and not has_standings:
            QtWidgets.QMessageBox.information(
                self, "Print", "No pairings or standings available to print."
            )
            return

        # Get round info for display
        round_info = ""
        if has_pairings:
            round_info = self.header.title_label.text()

        # Show print options dialog
        dialog = PrintOptionsDialog(
            self,
            has_pairings=has_pairings,
            has_standings=has_standings,
            round_info=round_info,
            default_pairings=default_pairings,
            default_standings=default_standings,
        )

        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        options = dialog.get_options()

        # Get tournament name and round title
        tournament_name = self.tournament.name if self.tournament else ""
        round_title = self.header.title_label.text() if hasattr(self, "header") else ""

        if options["print_pairings"] and not options["print_standings"]:
            # Just print pairings
            self.printer.print_from_table(
                self.pairings_table,
                tournament_name,
                round_title,
                self.pairings_table.lbl_bye,
            )
        elif options["print_standings"] and not options["print_pairings"]:
            # Just print standings - delegate to standings tab
            main_window = self.window()
            if hasattr(main_window, "standings_tab"):
                main_window.standings_tab.print_standings_only()
        else:
            # Print both - generate combined document
            self._print_combined(options["separate_pages"])

    def _print_combined(self, separate_pages: bool):
        """Print both pairings and standings in a combined document."""
        from PyQt6.QtGui import QTextDocument

        from gambitpairing.utils.print import TournamentPrintUtils

        tournament_name = self.tournament.name if self.tournament else ""
        round_title = TournamentPrintUtils.get_clean_print_title(
            self.header.title_label.text()
        )

        # Create printer and preview
        printer, preview = TournamentPrintUtils.create_print_preview_dialog(
            self, "Print Preview - Tournament Documents"
        )

        def render_preview(printer_obj):
            html = self._generate_combined_html(
                tournament_name, round_title, separate_pages
            )
            doc = QTextDocument()
            doc.setHtml(html)
            doc.print(printer_obj)

        preview.paintRequested.connect(render_preview)
        preview.exec()

    def _generate_combined_html(
        self, tournament_name: str, round_title: str, separate_pages: bool
    ) -> str:
        """Generate combined HTML for pairings and standings."""
        from PyQt6.QtCore import QDateTime

        # Build pairings section
        pairings_rows = []
        for row in range(self.pairings_table.rowCount()):
            if self.pairings_table.is_bye_row(row):
                continue
            white_item = self.pairings_table.item(row, 1)
            black_item = self.pairings_table.item(row, 2)
            pairings_rows.append(
                PairingsPrintRow(
                    board=row + 1,
                    white=white_item.text() if white_item else "",
                    black=black_item.text() if black_item else "",
                )
            )

        bye_text = ""
        if (
            self.pairings_table.bye_container.isVisible()
            and self.pairings_table.lbl_bye.text()
            and self.pairings_table.lbl_bye.text() != "Bye: None"
        ):
            bye_text = self.pairings_table.lbl_bye.text()

        pairings_html = build_pairings_print_section(
            tournament_name, round_title, pairings_rows, bye_text
        )

        # Build standings section
        standings_html_content = ""
        main_window = self.window()
        if hasattr(main_window, "standings_tab") and hasattr(
            main_window.standings_tab, "get_standings_html"
        ):
            standings_html_content = main_window.standings_tab.get_standings_html()

        standings_html = build_standings_print_section(
            tournament_name,
            self.current_round_index,
            standings_html_content,
            build_page_separator(separate_pages),
        )

        return build_combined_tournament_print_html(
            pairings_html,
            standings_html,
            QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm"),
        )

    def get_results_from_table(
        self,
    ) -> Tuple[Optional[List[tuple]], bool]:
        return self.pairings_table.get_results()

    def log_results_details(self, results_data, round_index_recorded):
        for line in format_recorded_result_history_lines(
            self.tournament, results_data, round_index_recorded
        )[1:]:
            self.history_message.emit(line)

    def undo_last_results(self) -> None:
        if not self.controller.can_undo():
            QtWidgets.QMessageBox.warning(
                self,
                "Undo Error",
                "No results from a completed round are available to undo.",
            )
            return

        round_to_undo_display_num = (
            self.current_round_index
        )  # e.g. if current_round_index is 1, we undo R1 results.

        reply = QtWidgets.QMessageBox.question(
            self,
            "Undo Results",
            undo_confirmation_message(round_to_undo_display_num),
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No,
        )
        if reply != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        try:
            success, error_message = self.controller.undo_last_results()
            if not success:
                QtWidgets.QMessageBox.critical(
                    self,
                    "Undo Error",
                    error_message or "The results could not be undone.",
                )
                return

            self.current_round_index = self.controller.current_round_index
            self.displayed_round_index = self.current_round_index
            self._final_summary_visible = False

            # --- Update UI ---
            # Re-display pairings for the round being "re-opened" for input
            self.header.set_title("Rounds")

            existing = resolve_existing_round_pairings(
                self.tournament, self.current_round_index
            )
            for w_id, b_id in existing.missing_pairing_ids:
                logging.warning(
                    f"Load: Missing player for pairing ({w_id} vs {b_id}) in loaded round {self.current_round_index + 1}"
                )

            self.display_pairings_for_input(
                existing.pairings,
                existing.bye_players,
            )

            self.standings_update_requested.emit()  # Reflect reverted scores
            self.history_message.emit(
                f"--- Round {round_to_undo_display_num} Results Undone ---"
            )
            self.status_message.emit(
                f"Round {round_to_undo_display_num} results undone. Re-enter results or re-prepare round."
            )
            self.dirty.emit()
            # Notify main window of the new round index after undo
            self.round_completed.emit(self.current_round_index)

        except Exception as e:
            logging.exception(f"Error undoing results:")
            QtWidgets.QMessageBox.critical(
                self, "Undo Error", f"Undoing results failed:\n{e}"
            )
            self.status_message.emit("Error undoing results.")
        finally:
            self.update_ui_state()

    def update_ui_state(self):
        """Refresh round navigation, grid state, and tournament actions."""
        view_state = build_tournament_view_state(
            self.tournament,
            self.current_round_index,
            self.pairings_table.board_count(),
        )

        if not view_state.tournament_exists:
            self.tournament_placeholder.show()
            self.header.hide()
            self.round_navigation.hide()
            self.pre_tournament_start_widget.hide()
            self.round_card.hide()
            self.setEnabled(False)
            return

        self.tournament_placeholder.hide()
        self.header.show()
        self.header.set_title("Rounds")
        self.setEnabled(True)

        # A tournament exists but has no generated/manual round yet.
        if self.controller.generated_round_count == 0:
            active_count = len(self.controller.get_active_players())
            self.pre_tournament_start_widget.title_label.setText(
                "No rounds have been paired yet."
            )
            self.pre_tournament_start_widget.desc_label.setText(
                f"{active_count} active players\n"
                f"{self.tournament.num_rounds} rounds scheduled"
            )
            self.pre_tournament_start_widget.btn_start.setText("Pair Round 1")
            self.pre_tournament_start_widget.show()
            self.round_navigation.hide()
            self.round_card.hide()
            self.btn_view.hide()
            self.btn_pairing_actions.hide()
            self.round_controls.update_state("start")
            self.round_controls.set_primary_action(
                "Pair Round 1",
                enabled=True,
                tooltip="Generate pairings for Round 1",
            )
            self.round_controls.set_progress("0 / 0 results entered")
            self.round_controls.set_undo_visible(False)
            return

        self.pre_tournament_start_widget.hide()
        self.round_navigation.show()
        self.round_card.show()
        self.btn_view.show()
        self.btn_pairing_actions.show()

        if self._rendered_round_index != self.displayed_round_index or (
            self._final_summary_visible and self._rendered_round_index is not None
        ):
            self._render_current_round()

        self._update_round_navigation()
        self._update_round_progress()

        if self.current_round_index >= self.tournament.num_rounds:
            self.round_controls.update_state("finished")
            self.round_controls.set_primary_action(
                "View Final Standings",
                enabled=True,
                tooltip="Open the final standings",
            )
        elif self.current_round_index >= self.controller.generated_round_count:
            self.round_controls.update_state("prepare")
            self.round_controls.set_primary_action(
                f"Pair Round {self.current_round_index + 1}",
                enabled=True,
                tooltip="Generate pairings for the next round",
            )
        else:
            self.round_controls.update_state("record")
            entered, total = self.pairings_table.progress()
            complete = entered == total and (total > 0 or self.pairings_table.has_bye())
            self.round_controls.set_primary_action(
                "Complete Round",
                enabled=complete
                and self.displayed_round_index == self.current_round_index,
                tooltip=(
                    "Complete the round and advance"
                    if complete
                    else f"{max(0, total - entered)} results still required"
                ),
            )
        self.round_controls.set_undo_enabled(False)
        self.round_controls.set_undo_visible(False)

    def _open_manual_pairing_dialog(self, display_round_number: int, round_idx: int):
        """Helper to open manual pairing dialog and handle results."""
        # Get existing pairings
        existing_pairings = None
        existing_bye = None

        if self.controller.pairings_exist_for_round(round_idx):
            existing = resolve_existing_round_pairings(self.tournament, round_idx)
            existing_pairings = existing.pairings
            existing_bye = existing.bye_player

        # Open the manual pairing dialog
        active_players = self.controller.get_active_players()

        dialog = ManualPairingDialog(
            active_players,
            existing_pairings,
            existing_bye,
            display_round_number,
            self,
            self.tournament,
        )

        bye_type_combo = dialog.findChild(QtWidgets.QComboBox, "bye_type_combo")
        existing_round = self.controller.get_round_data(round_idx)
        if bye_type_combo is not None and existing_round is not None:
            bye_type_combo.setCurrentIndex(
                ("full", "half", "zero").index(existing_round.bye_type)
            )

        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            pairings, bye_players = dialog.get_pairings_and_bye()

            if len(bye_players) > 1:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Invalid byes",
                    "Only one bye per round is supported. No pairings were changed.",
                )
                return

            # For now, handle legacy compatibility by using the first bye player
            # TODO: Update tournament logic to handle multiple bye players
            bye_player = bye_players[0] if bye_players else None

            # Pairing mutations belong to the controller, not the widget.
            bye_type = (
                ("full", "half", "zero")[bye_type_combo.currentIndex()]
                if bye_type_combo is not None
                else "full"
            )
            if self.controller.set_manual_pairings(
                round_idx, pairings, bye_player, bye_type
            ):
                self.display_pairings_for_input(pairings, bye_players)

                # Log the updated pairings
                pairing_type = (
                    "Manual" if self.tournament.pairing_system == "manual" else "Edited"
                )
                for line in format_manual_pairing_history_lines(
                    display_round_number, pairing_type, pairings, bye_players
                ):
                    self.history_message.emit(line)

                self.dirty.emit()
                self.status_message.emit(
                    f"Round {display_round_number} pairings updated."
                )
            else:
                QtWidgets.QMessageBox.critical(
                    self, "Error", "Failed to update pairings."
                )

        self.update_ui_state()

    def _handle_manual_pairing_round(
        self, display_round_number: int, round_to_prepare_idx: int
    ):
        """Handle manual pairing for a round."""
        self._open_manual_pairing_dialog(display_round_number, round_to_prepare_idx)

    def _edit_selected_completed_round(self) -> None:
        """Use the existing last-round undo rules to re-open a completed round."""
        if not self.tournament:
            return
        if self.displayed_round_index != self.current_round_index - 1:
            self.status_message.emit(
                "Only the most recently completed round can be edited."
            )
            return
        self.undo_last_results()

    def _edit_displayed_pairings(self) -> None:
        if not self.tournament:
            return
        if self.displayed_round_index != self.current_round_index:
            return
        self._open_manual_pairing_dialog(
            self.displayed_round_index + 1, self.displayed_round_index
        )

    def _repair_displayed_round(self) -> None:
        if not self.tournament:
            return
        if self.displayed_round_index == self.current_round_index:
            self._prepare_round(self.current_round_index, for_preparation=True)

    def _edit_all_pairings(self):
        """Open the manual pairing dialog to edit all pairings for the current round."""
        if not self.tournament:
            return
        self._edit_displayed_pairings()

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
