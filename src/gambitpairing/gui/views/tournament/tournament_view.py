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
from gambitpairing.gui.ui_loader import load_ui_into, required_child
from gambitpairing.utils import PairingsPrinter
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
from gambitpairing.gui.views.tournament.tournament_view_workflow import (
    active_players_for_manual_pairing,
    build_recorded_round_view_update,
    build_tournament_view_state,
    evaluate_minimum_player_check,
    evaluate_undo_availability,
    format_generated_pairing_history_lines,
    format_manual_pairing_history_lines,
    format_recorded_result_history_lines,
    players_to_revert_for_undo,
    revert_player_round_data,
    resolve_existing_round_pairings,
    undo_confirmation_message,
)
from gambitpairing.models import (
    Player,
)
from gambitpairing.utils import setup_logger

logger = setup_logger(__name__)


class TournamentView(QtWidgets.QWidget):
    def _check_minimum_players(self, for_preparation=False):
        """
        Shared minimum player/active player checks for both tournament start and round preparation.
        Returns True if checks pass, False if user cancels or not enough players.
        """
        check = evaluate_minimum_player_check(
            self.tournament, for_preparation=for_preparation
        )
        if check.kind == "blocking":
            QtWidgets.QMessageBox.warning(self, check.title, check.message)
            return False
        if check.requires_confirmation:
            reply = QtWidgets.QMessageBox.warning(
                self,
                check.title,
                check.message,
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

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tournament = None
        self.current_round_index = 0
        self.last_recorded_results_data: List[tuple] = []

        # Create controller and printer helpers
        self.controller = TournamentController()
        self.printer = PairingsPrinter(self)

        load_ui_into(self, "tournament_view.ui")
        self.main_layout = required_child(
            self, QtWidgets.QVBoxLayout, "main_layout"
        )
        header_layout = required_child(self, QtWidgets.QVBoxLayout, "header_layout")
        pre_tournament_layout = required_child(
            self, QtWidgets.QVBoxLayout, "pre_tournament_layout"
        )
        placeholder_layout = required_child(
            self, QtWidgets.QVBoxLayout, "placeholder_layout"
        )

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
        header_layout.addWidget(self.header)

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

    def _setup_round_card(self):
        """Create the round card container with pairings table and action footer."""
        self.round_card = required_child(self, QtWidgets.QFrame, "round_card")
        self.round_card.setProperty("class", "RoundCard")
        pairings_layout = required_child(
            self, QtWidgets.QVBoxLayout, "pairings_layout"
        )
        round_controls_layout = required_child(
            self, QtWidgets.QVBoxLayout, "round_controls_layout"
        )

        # ===== STATUS BAR =====
        self.lbl_status_instruction = required_child(
            self, QtWidgets.QLabel, "lbl_status_instruction"
        )
        self.lbl_status_instruction.setProperty("class", "StatusInstruction")
        self.lbl_status_instruction.setProperty("state", "default")

        # ===== PAIRINGS TABLE =====
        self.pairings_table = PairingsTable()
        self.pairings_table.context_menu_requested.connect(
            self.show_pairing_context_menu
        )
        pairings_layout.addWidget(self.pairings_table, 1)

        # ===== ACTION FOOTER =====
        self.round_controls = RoundControlsWidget()
        self.round_controls.start_requested.connect(self.start_tournament)
        self.round_controls.prepare_requested.connect(self.prepare_next_round)
        self.round_controls.record_requested.connect(self.record_and_advance)
        self.round_controls.undo_requested.connect(self.undo_last_results)
        round_controls_layout.addWidget(self.round_controls)

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
                existing = resolve_existing_round_pairings(
                    self.tournament, round_index
                )
                self.header.set_title(f"Round {display_round_num} Pairings & Results")
                self.display_pairings_for_input(existing.pairings, existing.bye_players)
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
            for line in format_generated_pairing_history_lines(
                display_round_number, pairings, bye_player
            ):
                self.history_message.emit(line)
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

    def reset_display(self):
        """Reset the UI to default state.

        Clears the pairings table and bye player label.
        """
        self.pairings_table.reset_display()
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
                existing = resolve_existing_round_pairings(
                    self.tournament, self.current_round_index
                )
                existing_pairings = existing.pairings
                existing_bye = existing.bye_player
            active_players = active_players_for_manual_pairing(self.tournament)
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

                for line in format_recorded_result_history_lines(
                    self.tournament, results_data, round_index_to_record
                ):
                    self.history_message.emit(line)

                # Advance current_round_index *after* successful recording and logging
                view_update = build_recorded_round_view_update(
                    self.tournament.num_rounds, round_index_to_record
                )
                self.current_round_index = view_update.next_round_index
                # Notify main window of round advancement
                self.round_completed.emit(self.current_round_index)

                self.standings_update_requested.emit()
                self.status_message.emit(view_update.status_message)
                for line in view_update.history_lines:
                    self.history_message.emit(line)

                self.pairings_table.reset_display()
                self.header.set_title(view_update.header_title)

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
    ) -> Tuple[Optional[List[tuple]], bool]:
        return self.pairings_table.get_results()

    def log_results_details(self, results_data, round_index_recorded):
        for line in format_recorded_result_history_lines(
            self.tournament, results_data, round_index_recorded
        )[1:]:
            self.history_message.emit(line)

    def undo_last_results(self) -> None:
        undo_availability = evaluate_undo_availability(
            self.tournament, self.last_recorded_results_data, self.current_round_index
        )
        if not undo_availability.can_undo:
            # current_round_index is index of NEXT round to play. If 0, no rounds completed.
            QtWidgets.QMessageBox.warning(
                self,
                undo_availability.title,
                undo_availability.message,
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
            # The round whose results are being undone (0-indexed)
            round_index_being_undone = self.current_round_index - 1

            for player in players_to_revert_for_undo(
                self.tournament,
                self.last_recorded_results_data,
                round_index_being_undone,
            ):
                self._revert_player_round_data(player)

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

    def _revert_player_round_data(self, player: Player):
        """Helper to remove the last round's data from a player object's history lists."""
        revert_player_round_data(player)

    def update_ui_state(self):
        """
        Update all UI elements based on current tournament state.

        This method uses tournament view workflow helpers to compute and update:
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
        view_state = build_tournament_view_state(
            self.tournament,
            self.current_round_index,
            self.pairings_table.rowCount(),
        )

        # Show/hide placeholder based on tournament existence
        if not view_state.tournament_exists:
            self.tournament_placeholder.show()
            self.header.hide()
            self.round_card.hide()
            return

        # Tournament exists - show main content
        self.tournament_placeholder.hide()
        self.header.show()

        # Determine which view to show: Pre-Tournament or Round Card
        if view_state.show_pre_tournament_start:
            self.pre_tournament_start_widget.show()
            self.round_card.hide()
        else:
            self.pre_tournament_start_widget.hide()
            self.round_card.show()

        # ===== UPDATE ROUND CONTROLS =====
        self.round_controls.update_state(view_state.round_control_state)
        self.round_controls.set_undo_enabled(view_state.undo_enabled)
        self.round_controls.set_undo_visible(view_state.undo_visible)

        # ===== UPDATE STATUS/INSTRUCTION LABEL =====
        if view_state.status_visible:
            self.lbl_status_instruction.setText(view_state.status_message)
            self.lbl_status_instruction.setProperty("state", view_state.status_state)
            self.lbl_status_instruction.show()
        else:
            self.lbl_status_instruction.setText("")
            self.lbl_status_instruction.setProperty("state", "default")
            self.lbl_status_instruction.hide()

        # Force style refresh after changing property
        self.lbl_status_instruction.style().unpolish(self.lbl_status_instruction)
        self.lbl_status_instruction.style().polish(self.lbl_status_instruction)

        # ===== UPDATE EDIT PAIRINGS BUTTON =====
        if view_state.edit_pairings_visible:
            self.btn_edit_pairings.show()
            self.btn_edit_pairings.setEnabled(view_state.edit_pairings_enabled)
        else:
            self.btn_edit_pairings.hide()

        # ===== UPDATE PRINT BUTTON =====
        self.btn_print_pairings.setEnabled(view_state.print_pairings_enabled)

        # Enable the whole tab
        self.setEnabled(view_state.tournament_exists)

    def _open_manual_pairing_dialog(self, display_round_number: int, round_idx: int):
        """Helper to open manual pairing dialog and handle results."""
        # Get existing pairings
        existing_pairings = None
        existing_bye = None

        if round_idx < len(self.tournament.rounds_pairings_ids):
            existing = resolve_existing_round_pairings(self.tournament, round_idx)
            existing_pairings = existing.pairings
            existing_bye = existing.bye_player

        # Open the manual pairing dialog
        active_players = active_players_for_manual_pairing(self.tournament)

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
