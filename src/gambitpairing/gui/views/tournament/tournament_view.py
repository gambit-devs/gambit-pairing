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

"""
Tournament tab UI for managing tournament rounds and pairings.

This module provides the TournamentTab widget which handles:
- Tournament start and round preparation
- Pairings display and result entry
- Manual pairing adjustments
- Result recording and undo

The business logic is separated into:
- tournament_controller.py: Core tournament operations
- tournament_widgets.py: Reusable UI widgets
- tournament_state.py: State management
- pairings_printer.py: Printing functionality

UI Design Philosophy:
- Clear visual hierarchy with distinct sections
- Round Card container for focused pairing management
- Intuitive workflow: View Pairings → Enter Results → Advance
- Professional styling with consistent spacing
"""

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
from gambitpairing.gui.dialogs import ManualPairingDialog
from gambitpairing.gui.gui_utils import get_colored_icon, set_svg_icon
from gambitpairing.gui.notournament_placeholder import NoTournamentPlaceholder
from gambitpairing.gui.views.tournament.components.pairings_table import PairingsTable
from gambitpairing.gui.views.tournament.components.pre_tournament_widget import (
    PreTournamentWidget,
)
from gambitpairing.gui.views.tournament.components.round_controls import (
    RoundControlsWidget,
)
from gambitpairing.gui.views.tournament.components.tournament_widgets import (
    ResultSelector,
)
from gambitpairing.gui.views.tournament.tournament_controller import (
    TournamentController,
)
from gambitpairing.gui.views.tournament.tournament_state import (
    TournamentPhase,
    TournamentState,
)
from gambitpairing.gui.views.tournament.utils.pairings_printer import PairingsPrinter
from gambitpairing.gui.widgets.header import TabHeader
from gambitpairing.player import Player
from gambitpairing.resources.resource_utils import get_resource_path
from gambitpairing.utils import setup_logger

logger = setup_logger(__name__)


class TournamentView(QtWidgets.QWidget):
    def _check_minimum_players(self, for_preparation=False):
        """
        Shared minimum player/active player checks for both tournament start and round preparation.
        Returns True if checks pass, False if user cancels or not enough players.
        """
        pairing_system = getattr(self.tournament, "pairing_system", "dutch_swiss")
        if for_preparation:
            # Use only active players for round preparation
            players = [
                p
                for p in self.tournament.players.values()
                if getattr(p, "is_active", True)
            ]
        else:
            # Use all players for initial start
            players = list(self.tournament.players.values())
        num_players = len(players)
        min_players = 2**self.tournament.num_rounds

        player_type = "active " if for_preparation else ""

        if pairing_system == "round_robin":
            if num_players < 3:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Start Error" if not for_preparation else "Prepare Error",
                    f"Round Robin tournaments require at least three {player_type}players.",
                )
                return False
        elif pairing_system == "dutch_swiss":
            if num_players < 2:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Start Error" if not for_preparation else "Prepare Error",
                    f"FIDE Dutch Swiss tournaments require at least two {player_type}players.",
                )
                return False
            if num_players < min_players:
                reply = QtWidgets.QMessageBox.warning(
                    self,
                    "Insufficient Players",
                    f"For a {self.tournament.num_rounds}-round FIDE Dutch Swiss tournament, a minimum of {min_players} players is recommended. The tournament may not work properly. Do you want to continue anyway?",
                    QtWidgets.QMessageBox.StandardButton.Yes
                    | QtWidgets.QMessageBox.StandardButton.No,
                    QtWidgets.QMessageBox.StandardButton.No,
                )
                if reply == QtWidgets.QMessageBox.StandardButton.No:
                    return False
        elif pairing_system == "manual":
            if num_players < 2:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Start Error" if not for_preparation else "Prepare Error",
                    f"Manual pairing tournaments require at least two {player_type}players.",
                )
                return False
        return True

    status_message = pyqtSignal(str)
    history_message = pyqtSignal(str)
    dirty = pyqtSignal()
    round_completed = pyqtSignal(int)
    standings_update_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tournament = None
        self.current_round_index = 0
        self.last_recorded_results_data: List[Tuple[str, str, float]] = []

        # Create controller and printer helpers
        self.controller = TournamentController()
        self.printer = PairingsPrinter(self)

        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(16, 16, 16, 16)
        self.main_layout.setSpacing(0)

        # ===== TOURNAMENT INFO HEADER =====
        self.header = TabHeader("No Tournament Loaded")
        self.btn_edit_pairings = self.header.add_action_button(
            "edit.svg", "Edit Pairings", self._edit_all_pairings
        )
        self.btn_edit_pairings.hide()
        self.btn_print_pairings = self.header.add_action_button(
            "print.svg",
            "Print Pairings",
            lambda: self.open_print_dialog(
                default_pairings=True, default_standings=False
            ),
        )
        self.main_layout.addWidget(self.header)

        # ===== ROUND CARD CONTAINER =====
        # This is the main content area that holds pairings and results
        self._setup_round_card()

        # ===== PRE-TOURNAMENT WIDGET =====
        self.pre_tournament_widget = PreTournamentWidget(self)
        self.pre_tournament_widget.start_requested.connect(self.start_tournament)
        self.pre_tournament_widget.hide()
        self.main_layout.addWidget(self.pre_tournament_widget)

        # ===== NO TOURNAMENT PLACEHOLDER =====
        self.no_tournament_placeholder = NoTournamentPlaceholder(self, "Rounds")
        self.no_tournament_placeholder.create_tournament_requested.connect(
            self._trigger_create_tournament
        )
        self.no_tournament_placeholder.import_tournament_requested.connect(
            self._trigger_import_tournament
        )
        self.no_tournament_placeholder.hide()
        self.main_layout.addWidget(self.no_tournament_placeholder)

        # Set initial UI state
        self.update_ui_state()

    def _setup_round_card(self):
        """Create the round card container with pairings table and action footer."""
        # Main card container with rounded corners and shadow effect
        self.round_card = QtWidgets.QFrame()
        self.round_card.setProperty("class", "RoundCard")
        self.round_card.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        card_layout = QtWidgets.QVBoxLayout(self.round_card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # ===== STATUS BAR =====
        self.lbl_status_instruction = QtWidgets.QLabel("")
        self.lbl_status_instruction.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status_instruction.setWordWrap(True)
        self.lbl_status_instruction.setProperty("class", "StatusInstruction")
        self.lbl_status_instruction.setProperty("state", "default")
        card_layout.addWidget(self.lbl_status_instruction)

        # ===== PAIRINGS TABLE =====
        self.pairings_table = PairingsTable()
        self.pairings_table.context_menu_requested.connect(
            self.show_pairing_context_menu
        )
        card_layout.addWidget(self.pairings_table, 1)  # Give table stretch priority

        # ===== ACTION FOOTER =====
        self.round_controls = RoundControlsWidget()
        self.round_controls.start_requested.connect(self.start_tournament)
        self.round_controls.prepare_requested.connect(self.prepare_next_round)
        self.round_controls.record_requested.connect(self.record_and_advance)
        self.round_controls.undo_requested.connect(self.undo_last_results)
        card_layout.addWidget(self.round_controls)

        self.main_layout.addWidget(self.round_card, 1)  # Give card stretch priority

    def set_tournament(self, tournament):
        """Set the tournament and update controller."""
        self.tournament = tournament
        self.controller.set_tournament(tournament)
        self.update_ui_state()

    def set_current_round_index(self, idx):
        """Set the current round index and update controller."""
        self.current_round_index = idx
        self.controller.set_current_round_index(idx)
        self.update_ui_state()

    def _prepare_round(self, round_index: int, for_preparation: bool = False) -> bool:
        """
        Common logic for preparing a round (either starting tournament or preparing next round).

        Args:
            round_index: The round index to prepare (0-based)
            for_preparation: Whether this is for round preparation (affects player checks)

        Returns:
            True if round was prepared successfully, False otherwise
        """
        if not self._check_minimum_players(for_preparation=for_preparation):
            return False

        if round_index >= self.tournament.num_rounds:
            QtWidgets.QMessageBox.information(
                self,
                "Tournament End",
                "All tournament rounds have been generated and processed.",
            )
            self.update_ui_state()
            return False

        # Check if pairings for this round already exist
        if round_index < len(self.tournament.rounds_pairings_ids):
            reply = QtWidgets.QMessageBox.question(
                self,
                "Re-Prepare Round?",
                f"Pairings for Round {round_index + 1} already exist. Re-generate them?\n"
                "This is usually not needed unless player active status changed significantly.",
                QtWidgets.QMessageBox.StandardButton.Yes
                | QtWidgets.QMessageBox.StandardButton.No,
                QtWidgets.QMessageBox.StandardButton.No,
            )
            if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                # Clear existing pairings for this round to regenerate
                self.tournament.rounds_pairings_ids = (
                    self.tournament.rounds_pairings_ids[:round_index]
                )
                self.tournament.rounds_byes_ids = self.tournament.rounds_byes_ids[
                    :round_index
                ]
                self.history_message.emit(
                    f"--- Re-preparing pairings for Round {round_index + 1} ---"
                )
            else:
                # Just display existing pairings
                display_round_num = round_index + 1
                pairings_ids = self.tournament.rounds_pairings_ids[round_index]
                bye_id = self.tournament.rounds_byes_ids[round_index]
                pairings = []
                for w_id, b_id in pairings_ids:
                    w = self.tournament.players.get(w_id)
                    b = self.tournament.players.get(b_id)
                    if w and b:
                        pairings.append((w, b))

                bye_player = self.tournament.players.get(bye_id) if bye_id else None
                self.header.set_title(f"Round {display_round_num} Pairings & Results")
                self.display_pairings_for_input(
                    pairings, [bye_player] if bye_player else []
                )
                self.update_ui_state()
                return True

        display_round_number = round_index + 1

        # Check if this is a manual pairing tournament
        if self.tournament.pairing_system == "manual":
            self._handle_manual_pairing_round(display_round_number, round_index)
            return True

        self.status_message.emit(
            f"Generating pairings for Round {display_round_number}..."
        )
        QtWidgets.QApplication.processEvents()

        try:
            pairings, bye_player = self.tournament.create_pairings(
                display_round_number,
                allow_repeat_pairing_callback=self.prompt_repeat_pairing,
            )

            if (
                not pairings
                and len(self.tournament._get_active_players()) > 1
                and not bye_player
            ):
                if len(self.tournament._get_active_players()) % 2 == 0:
                    QtWidgets.QMessageBox.critical(
                        self,
                        "Pairing Error",
                        f"Pairing generation failed for Round {display_round_number}. No pairings returned. Check logs and player statuses.",
                    )
                    self.status_message.emit(
                        f"Error generating pairings for Round {display_round_number}."
                    )
                    self.update_ui_state()
                    return False

            self.header.set_title(f"Round {display_round_number} Pairings & Results")
            self.display_pairings_for_input(
                pairings, [bye_player] if bye_player else []
            )
            self.history_message.emit(
                f"--- Round {display_round_number} Pairings Generated ---"
            )
            for pair in pairings:
                if len(pair) == 3:
                    white, black, color = pair
                    self.history_message.emit(
                        f"  {white.name} ({color}) vs {black.name} ({'B' if color == 'W' else 'W'})"
                    )
                else:
                    white, black = pair
                    self.history_message.emit(f"  {white.name} (W) vs {black.name} (B)")
            if bye_player:
                self.history_message.emit(f"  Bye: {bye_player.name}")
            self.history_message.emit("-" * 20)
            self.dirty.emit()
            self.status_message.emit(
                f"Round {display_round_number} pairings ready. Enter results."
            )
        except Exception as e:
            logging.exception(
                f"Error generating pairings for Round {display_round_number}:"
            )
            QtWidgets.QMessageBox.critical(
                self,
                "Pairing Error",
                f"Pairing generation failed for Round {display_round_number}:\n{e}",
            )
            self.status_message.emit(
                f"Error generating pairings for Round {display_round_number}."
            )
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
        self.pairings_table.display_pairings(
            pairings, bye_players, self.current_round_index
        )

    def clear_pairings_display(self):
        """Clears the pairings table and bye player label."""
        self.pairings_table.clear()
        if self.tournament:
            self.header.set_title(f"Round {self.current_round_index + 1} - Not Started")
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

        white_id = result_selector.property("white_id")
        black_id = result_selector.property("black_id")

        menu = QtWidgets.QMenu(self)

        # Offer option to edit all pairings for all tournaments
        edit_all_action = menu.addAction("Edit Pairings...")
        menu.addSeparator()

        adjust_action = menu.addAction("Manually Adjust Pairing...")

        # Only allow adjustment for the current round before results are recorded
        can_adjust = self.current_round_index < len(self.tournament.rounds_pairings_ids)
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
            if self.current_round_index < len(self.tournament.rounds_pairings_ids):
                pairings_ids = self.tournament.rounds_pairings_ids[
                    self.current_round_index
                ]
                bye_id = self.tournament.rounds_byes_ids[self.current_round_index]
                existing_pairings = []
                for w_id, b_id in pairings_ids:
                    w = self.tournament.players.get(w_id)
                    b = self.tournament.players.get(b_id)
                    if w and b:
                        existing_pairings.append((w, b))
                existing_bye = self.tournament.players.get(bye_id) if bye_id else None
            active_players = [
                p for p in self.tournament.players.values() if p.is_active
            ]
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

        # Results are for the round currently displayed, which is self.current_round_index
        round_index_to_record = self.current_round_index

        if round_index_to_record >= len(self.tournament.rounds_pairings_ids):
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
            if self.tournament.record_results(round_index_to_record, results_data):
                self.last_recorded_results_data = list(
                    results_data
                )  # Store deep copy for undo

                display_round_number = round_index_to_record + 1
                self.history_message.emit(
                    f"--- Round {display_round_number} Results Recorded ---"
                )
                self.log_results_details(results_data, round_index_to_record)

                # Advance current_round_index *after* successful recording and logging
                self.current_round_index += 1
                # Notify main window of round advancement
                self.round_completed.emit(self.current_round_index)

                self.standings_update_requested.emit()

                if self.current_round_index >= self.tournament.num_rounds:
                    self.status_message.emit(
                        f"Tournament finished after {self.tournament.num_rounds} rounds."
                    )
                    self.history_message.emit(
                        f"--- Tournament Finished ({self.tournament.num_rounds} Rounds) ---"
                    )
                    # Clear pairings table as no more rounds to input
                    self.pairings_table.clear()
                    self.header.set_title("Tournament Finished")
                else:
                    self.status_message.emit(
                        f"Round {display_round_number} results recorded. Prepare Round {self.current_round_index + 1}."
                    )
                    # Clear pairings table for next round prep
                    self.pairings_table.clear()
                    self.header.set_title(
                        f"Round {self.current_round_index + 1} (Pending Preparation)"
                    )

                self.dirty.emit()
            else:  # record_results returned False
                QtWidgets.QMessageBox.warning(
                    self,
                    "Recording Warning",
                    "Some results may not have been recorded properly by the backend. Check logs and player status.",
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
        from PyQt6.QtCore import QDateTime
        from PyQt6.QtGui import QTextDocument

        from gambitpairing.constants import TIEBREAK_NAMES
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

        from gambitpairing.constants import TIEBREAK_NAMES

        page_break = (
            '<div style="page-break-before: always;"></div>'
            if separate_pages
            else '<hr style="margin: 2em 0; border: none; border-top: 2px solid #222;">'
        )

        # Build pairings section
        pairings_html = ""
        if self.pairings_table.rowCount() > 0:
            pairings_html = f"""
            <h2>Pairings{' - ' + tournament_name if tournament_name else ''}</h2>
            <div class="subtitle">{round_title}</div>
            <table class="pairings">
                <tr>
                    <th style="width:7%;">Bd</th>
                    <th style="width:46%;">White</th>
                    <th style="width:46%;">Black</th>
                </tr>
            """
            for row in range(self.pairings_table.rowCount()):
                white_item = self.pairings_table.item(row, 1)  # Column 1 is White
                black_item = self.pairings_table.item(row, 2)  # Column 2 is Black
                white_name = white_item.text() if white_item else ""
                black_name = black_item.text() if black_item else ""
                pairings_html += f"<tr><td>{row + 1}</td><td>{white_name}</td><td>{black_name}</td></tr>"

            if (
                self.pairings_table.bye_container.isVisible()
                and self.pairings_table.lbl_bye.text()
                and self.pairings_table.lbl_bye.text() != "Bye: None"
            ):
                pairings_html += f'<tr class="bye-row"><td colspan="3">{self.pairings_table.lbl_bye.text()}</td></tr>'

            pairings_html += "</table>"

        # Build standings section
        standings_html = ""
        main_window = self.window()
        if hasattr(main_window, "standings_tab") and hasattr(
            main_window.standings_tab, "get_standings_html"
        ):
            standings_html_content = main_window.standings_tab.get_standings_html()
            if standings_html_content:
                standings_html = f"""
                {page_break}
                <h2>Standings{' - ' + tournament_name if tournament_name else ''}</h2>
                <div class="subtitle">After Round {self.current_round_index}</div>
                {standings_html_content}
                """

        # Combine into full HTML document
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; color: #000; background: #fff; margin: 0; padding: 20px; }}
                h2 {{ text-align: center; margin: 0 0 0.5em 0; font-size: 1.35em; font-weight: bold; letter-spacing: 0.03em; }}
                .subtitle {{ text-align: center; font-size: 1.05em; margin-bottom: 1.2em; color: #444; }}
                table.pairings, table.standings {{ border-collapse: collapse; width: 100%; margin: 0 auto 1.5em auto; }}
                table.pairings th, table.pairings td,
                table.standings th, table.standings td {{ border: 1px solid #222; padding: 6px 10px; text-align: center; font-size: 11pt; }}
                table.pairings th, table.standings th {{ font-weight: bold; background: #f0f0f0; }}
                table.pairings td:nth-child(2), table.pairings td:nth-child(3) {{ text-align: left; }}
                table.standings td:nth-child(2) {{ text-align: left; }}
                .bye-row td {{ font-style: italic; font-weight: bold; text-align: center; border-top: 2px solid #222; }}
                .legend {{ margin-top: 1em; font-size: 10pt; color: #444; }}
                .footer {{ text-align: center; font-size: 9pt; margin-top: 2em; color: #888; }}
            </style>
        </head>
        <body>
            {pairings_html}
            {standings_html}
            <div class="footer">
                Printed by Gambit Pairing &mdash; {QDateTime.currentDateTime().toString('yyyy-MM-dd hh:mm')}
            </div>
        </body>
        </html>
        """

        return html

    def get_results_from_table(
        self,
    ) -> Tuple[Optional[List[Tuple[str, str, float]]], bool]:
        return self.pairings_table.get_results()

    def log_results_details(self, results_data, round_index_recorded):
        bye_id = self.tournament.rounds_byes_ids[round_index_recorded]
        # Log paired game results
        for w_id, b_id, score_w in results_data:
            w = self.tournament.players.get(w_id)  # Assume player exists
            b = self.tournament.players.get(b_id)
            score_b_display = (
                f"{WIN_SCORE - score_w:.1f}"  # Calculate display for black's score
            )
            self.history_message.emit(
                f"  {w.name if w else w_id} ({score_w:.1f}) - {b.name if b else b_id} ({score_b_display})"
            )

        # Log bye if one was assigned for the undone round
        if round_index_recorded < len(self.tournament.rounds_byes_ids):
            bye_id = self.tournament.rounds_byes_ids[round_index_recorded]
            if bye_id:
                bye_player = self.tournament.players.get(bye_id)
                if bye_player:
                    status = (
                        " (Inactive - No Score)" if not bye_player.is_active else ""
                    )
                    # Actual score for bye is handled by record_results based on active status
                    bye_score_awarded = BYE_SCORE if bye_player.is_active else 0.0
                    self.history_message.emit(
                        f"  Bye point ({bye_score_awarded:.1f}) awarded to: {bye_player.name}{status}"
                    )
                else:
                    self.history_message.emit(
                        f"  Bye player ID {bye_id} not found in player list (error)."
                    )
        self.history_message.emit("-" * 20)

    def undo_last_results(self) -> None:
        if (
            not self.tournament
            or not self.last_recorded_results_data
            or self.current_round_index == 0
        ):
            # current_round_index is index of NEXT round to play. If 0, no rounds completed.
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
            f"Undo results from Round {round_to_undo_display_num} and revert to its pairing stage?",
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No,
        )
        if reply != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        try:
            # The round whose results are being undone (0-indexed)
            round_index_being_undone = self.current_round_index - 1

            # Revert player stats for each game in last_recorded_results_data
            for white_id, black_id, _ in self.last_recorded_results_data:
                p_white = self.tournament.players.get(white_id)
                p_black = self.tournament.players.get(black_id)
                if p_white:
                    self._revert_player_round_data(p_white)
                if p_black:
                    self._revert_player_round_data(p_black)

            # Revert bye player stats if a bye was given in the undone round
            if round_index_being_undone < len(self.tournament.rounds_byes_ids):
                bye_player_id_undone_round = self.tournament.rounds_byes_ids[
                    round_index_being_undone
                ]
                if bye_player_id_undone_round:
                    p_bye = self.tournament.players.get(bye_player_id_undone_round)
                    if p_bye:
                        self._revert_player_round_data(p_bye)

            # Crucial: Do NOT pop from tournament's rounds_pairings_ids or rounds_byes_ids here.
            # These store the historical pairings. Undoing results means we are going back to the
            # state *before* these results were entered for that specific round's pairings.
            # The pairings themselves remain.

            # If manual pairings were made for the round being undone, they are part of its history.
            # They are not automatically "undone" unless the user manually re-pairs.
            if round_index_being_undone in self.tournament.manual_pairings:
                logging.warning(
                    f"Manual pairings for round {round_to_undo_display_num} were part of its setup and are not automatically reverted by undoing results."
                )

            self.last_recorded_results_data = (
                []
            )  # Clear the stored results for "can_undo" check
            self.current_round_index -= 1  # Decrement GUI's round counter

            # --- Update UI ---
            # Re-display pairings for the round being "re-opened" for input
            self.header.set_title(
                f"Round {self.current_round_index + 1} Pairings & Results (Re-entry)"
            )

            pairings_ids_to_redisplay = self.tournament.rounds_pairings_ids[
                self.current_round_index
            ]
            bye_id_to_redisplay = self.tournament.rounds_byes_ids[
                self.current_round_index
            ]

            pairings_to_redisplay = []
            for w_id, b_id in pairings_ids_to_redisplay:
                w = self.tournament.players.get(w_id)
                b = self.tournament.players.get(b_id)
                if w and b:
                    pairings_to_redisplay.append((w, b))
                else:
                    logging.warning(
                        f"Load: Missing player for pairing ({w_id} vs {b_id}) in loaded round {self.current_round_index + 1}"
                    )

            bye_player_to_redisplay = (
                self.tournament.players.get(bye_id_to_redisplay)
                if bye_id_to_redisplay
                else None
            )

            self.display_pairings_for_input(
                pairings_to_redisplay,
                [bye_player_to_redisplay] if bye_player_to_redisplay else [],
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

    def _revert_player_round_data(self, player: Player):
        """Helper to remove the last round's data from a player object's history lists."""
        if not player.results:
            return  # No results to revert

        last_result = player.results.pop()
        # Score is recalculated from scratch or by subtracting. Subtracting is simpler here.
        if last_result is not None:
            player.score = round(
                player.score - last_result, 1
            )  # round to handle float issues

        if player.running_scores:
            player.running_scores.pop()

        last_opponent_id = player.opponent_ids.pop() if player.opponent_ids else None
        last_color = player.color_history.pop() if player.color_history else None

        if last_color == "Black":
            player.num_black_games = max(0, player.num_black_games - 1)

        if last_opponent_id is None:  # Means the undone round was a bye for this player
            # Check if they *still* have other byes in their history.
            # If not, has_received_bye becomes False.
            player.has_received_bye = (
                (None in player.opponent_ids) if player.opponent_ids else False
            )
            logging.debug(
                f"Player {player.name} bye undone. Has received bye: {player.has_received_bye}"
            )

        # Invalidate opponent cache, it will be rebuilt on next access
        player._opponents_played_cache = []

    def update_ui_state(self):
        """
        Update all UI elements based on current tournament state.

        This method uses TournamentState to compute state and update:
        - Primary action button text and enabled state
        - Status instruction message and styling
        - Visibility and enabled states for all controls
        - Round progress indicator

        Button styling is handled via QSS classes:
        - IconButton: Edit/Print pairings (icon-only)

        Status instruction styling uses QSS with [state] property:
        - ready: Tournament ready to start
        - recording: Results entry in progress
        - prepare: Ready for next round
        - finished: Tournament complete
        """
        tournament_exists = self.tournament is not None

        # Show/hide placeholder based on tournament existence
        if not tournament_exists:
            self.no_tournament_placeholder.show()
            self.header.hide()
            self.round_card.hide()
            return

        # Tournament exists - show main content
        self.no_tournament_placeholder.hide()
        self.header.show()

        # Compute tournament state using TournamentState helper
        state = TournamentState.compute(self.tournament, self.current_round_index)

        # Debug logging
        logger.debug(
            f"update_ui_state: phase={state.phase.name}, "
            f"pairings_generated={state.pairings_generated}, results_recorded={state.results_recorded}, "
            f"total_rounds={state.total_rounds}"
        )

        # Determine which view to show: Pre-Tournament or Round Card
        if state.phase == TournamentPhase.NOT_STARTED:
            self.pre_tournament_widget.show()
            self.round_card.hide()
        else:
            self.pre_tournament_widget.hide()
            self.round_card.show()

        # ===== UPDATE ROUND CONTROLS =====
        control_state = "finished"
        if state.phase == TournamentPhase.NOT_STARTED:
            control_state = "start"
        elif state.phase == TournamentPhase.AWAITING_RESULTS:
            control_state = "record"
        elif state.phase == TournamentPhase.AWAITING_NEXT_ROUND:
            control_state = "prepare"

        self.round_controls.update_state(control_state)
        self.round_controls.set_undo_enabled(state.can_undo)
        # Undo button visibility is handled by the widget layout, but we can enforce it if needed
        # The widget currently always shows it but disables it.
        # If we want to hide it when tournament not started:
        self.round_controls.btn_undo.setVisible(state.tournament_started)

        # ===== UPDATE STATUS/INSTRUCTION LABEL =====
        num_pairings = self.pairings_table.rowCount()
        status_message = state.get_status_message(num_pairings)

        if status_message:
            self.lbl_status_instruction.setText(status_message)
            self.lbl_status_instruction.setProperty("state", state.status_state)
            self.lbl_status_instruction.show()
        else:
            self.lbl_status_instruction.setText("")
            self.lbl_status_instruction.setProperty("state", "default")
            self.lbl_status_instruction.hide()

        # Force style refresh after changing property
        self.lbl_status_instruction.style().unpolish(self.lbl_status_instruction)
        self.lbl_status_instruction.style().polish(self.lbl_status_instruction)

        # ===== UPDATE EDIT PAIRINGS BUTTON =====
        has_pairings = (
            self.current_round_index < len(self.tournament.rounds_pairings_ids)
            and len(self.tournament.rounds_pairings_ids[self.current_round_index]) > 0
        )
        if has_pairings:
            self.btn_edit_pairings.show()
            self.btn_edit_pairings.setEnabled(state.can_record)
        else:
            self.btn_edit_pairings.hide()

        # ===== UPDATE PRINT BUTTON =====
        self.btn_print_pairings.setEnabled(self.pairings_table.rowCount() > 0)

        # Enable the whole tab
        self.setEnabled(tournament_exists)

    def _open_manual_pairing_dialog(self, display_round_number: int, round_idx: int):
        """Helper to open manual pairing dialog and handle results."""
        # Get existing pairings
        existing_pairings = None
        existing_bye = None

        if round_idx < len(self.tournament.rounds_pairings_ids):
            pairings_ids = self.tournament.rounds_pairings_ids[round_idx]
            bye_id = self.tournament.rounds_byes_ids[round_idx]

            existing_pairings = []
            for w_id, b_id in pairings_ids:
                w = self.tournament.players.get(w_id)
                b = self.tournament.players.get(b_id)
                if w and b:
                    existing_pairings.append((w, b))

            existing_bye = self.tournament.players.get(bye_id) if bye_id else None

        # Open the manual pairing dialog
        active_players = [p for p in self.tournament.players.values() if p.is_active]

        dialog = ManualPairingDialog(
            active_players,
            existing_pairings,
            existing_bye,
            display_round_number,
            self,
            self.tournament,
        )

        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            pairings, bye_players = dialog.get_pairings_and_bye()

            # For now, handle legacy compatibility by using the first bye player
            # TODO: Update tournament logic to handle multiple bye players
            bye_player = bye_players[0] if bye_players else None

            # Set the manual pairings in the tournament
            if self.tournament.set_manual_pairings(round_idx, pairings, bye_player):
                self.display_pairings_for_input(pairings, bye_players)

                # Log the updated pairings
                pairing_type = (
                    "Manual" if self.tournament.pairing_system == "manual" else "Edited"
                )
                self.history_message.emit(
                    f"--- Round {display_round_number} {pairing_type} Pairings Updated ---"
                )
                for i, (white, black) in enumerate(pairings, 1):
                    self.history_message.emit(
                        f"  Board {i}: {white.name} (W) vs {black.name} (B)"
                    )
                if bye_players:
                    if len(bye_players) == 1:
                        self.history_message.emit(f"  Bye: {bye_players[0].name}")
                    else:
                        bye_names = ", ".join([p.name for p in bye_players])
                        self.history_message.emit(
                            f"  Byes ({len(bye_players)}): {bye_names}"
                        )
                self.history_message.emit("-" * 20)

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

    def _edit_all_pairings(self):
        """Open the manual pairing dialog to edit all pairings for the current round."""
        if not self.tournament:
            return

        display_round_number = self.current_round_index + 1
        self._open_manual_pairing_dialog(display_round_number, self.current_round_index)

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
