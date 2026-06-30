"""Main GUI window for Gambit Pairing."""

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

import logging
from typing import List, Optional

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QCloseEvent
from PyQt6.QtWidgets import QMessageBox

from gambitpairing import APP_NAME, APP_VERSION, utils
from gambitpairing.controllers.tournament import (
    TournamentGuiState,
    TournamentPersistenceService,
)
from gambitpairing.models.tournament import Tournament
from gambitpairing.update import Updater
from gambitpairing.utils import setup_logger

from .dialogs import (
    AboutDialog,
    NewTournamentDialog,
    SettingsDialog,
    UnsavedChangesDialog,
)
from .import_player import ImportPlayer
from .main_window_file_flow import (
    build_load_error_prompt,
    build_load_failure_notification,
    build_load_success_history,
    build_load_success_notification,
    build_load_success_status,
    build_overwrite_confirmation_prompt,
    build_save_error_prompt,
    build_save_history,
    build_save_status,
    should_request_save_path,
)
from .main_window_save_flow import (
    build_unsaved_changes_prompt,
    should_continue_after_save_prompt,
    should_prompt_for_unsaved_changes,
)
from .main_window_state import build_main_window_ui_state
from .main_window_tournament_flow import (
    build_new_tournament_history,
    build_new_tournament_notification,
    project_new_tournament_data,
)
from .notification import show_notification
from .ui_loader import load_ui_into
from .update_workflow import UpdateWorkflowController
from .views.crosstable.crosstable_view import CrosstableView
from .views.history.history_view import HistoryView
from .views.players.players_view import PlayersView
from .views.standings.standings_view import StandingsView
from .views.tournament.tournament_view import TournamentView
from .widgets.tournament_placeholder import TournamentPlaceholder

logger = setup_logger(__name__)


class GambitPairingMainWindow(QtWidgets.QMainWindow):
    """Main application window for Gambit Pairing."""

    def __init__(self) -> None:
        super().__init__()
        self.tournament: Optional[Tournament] = None
        # current_round_index tracks rounds with recorded results.
        # 0 = no results yet. 1 = R1 results are in.
        self.current_round_index: int = 0
        self.last_recorded_results_data: List[tuple] = []
        self._current_filepath: Optional[str] = None
        self._dirty: bool = False
        self.updater: Optional[Updater] = Updater(APP_VERSION)
        self.persistence_service = TournamentPersistenceService()
        # import player is a class containing import player logic
        self.import_mgr = ImportPlayer(self)

        self._setup_ui()
        self.update_workflow = UpdateWorkflowController(
            parent=self,
            updater=self.updater,
            app_name=APP_NAME,
            app_version=APP_VERSION,
            status_callback=self.statusBar().showMessage,
            close_callback=self.close,
        )
        self._update_ui_state()

        # Check for pending update first, then check for new online updates.
        if not self.check_for_pending_update():
            if self.updater:
                QtCore.QTimer.singleShot(1500, self.check_for_updates_auto)

        logger.info("GambitPairingMainWindow __init__ done.")

    def set_app_instance(self, app):
        """Store a reference to the QApplication instance for stylesheet control."""
        self._app_instance = app

    def mark_dirty(self, dirty=True):
        """Mark as dirty."""
        if self._dirty != dirty:
            self._dirty = dirty
            self._update_ui_state()

    def mark_clean(self):
        """Mark as clean."""
        self.mark_dirty(False)

    def reset_tournament_state(self):
        """Reset the entire application to a clean state."""
        self.tournament = None
        self.current_round_index = 0
        self.last_recorded_results_data = []
        self._current_filepath = None
        self.mark_clean()

        self._set_tournament_on_tabs()  # clear tournament tabs

        # Clear tab UI
        self.players_tab.reset_display()
        self.rounds_tab.reset_display()
        self.standings_tab.reset_display()
        self.crosstable_tab.reset_display()
        self.history_tab.reset_display()

        self._update_ui_state()

    def prompt_new_tournament(self):
        """Prompt the user to create a new tournament after check_save()."""
        if not self.check_save():
            return

        dialog = NewTournamentDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            if data:
                projection = project_new_tournament_data(data)
                self.reset_tournament_state()
                self.tournament = Tournament(
                    name=projection.name,
                    players=[],
                    num_rounds=projection.num_rounds,
                    tiebreak_order=projection.tiebreak_order,
                    pairing_system=projection.pairing_system,
                )
                self.pairing_system = projection.pairing_system
                self.update_history_log(build_new_tournament_history(projection))
                self.mark_dirty()
                self._set_tournament_on_tabs()
                self.standings_tab.update_standings_table_headers()
                self._update_ui_state()
                try:
                    show_notification(
                        self,
                        build_new_tournament_notification(projection),
                        duration=3500,
                        notification_type="success",
                    )

                except Exception as e:
                    message = (
                        "exception: '%s' excepted in an `except Exception`. This is bad practice."
                        % str(e)
                    )
                    raise RuntimeError(message)

    def show_settings_dialog(self) -> bool:
        if not self.tournament:
            return False

        dialog = SettingsDialog(
            self.tournament.num_rounds, self.tournament.tiebreak_order, self
        )
        tournament_started = len(self.tournament.rounds_pairings_ids) > 0
        dialog.configure_round_count_controls(
            getattr(self.tournament, "pairing_system", None),
            tournament_started,
        )

        if dialog.exec():
            new_rounds, new_tiebreaks = dialog.get_settings()
            if (
                self.tournament.num_rounds != new_rounds
                and not tournament_started
                and getattr(self.tournament, "pairing_system", None) != "round_robin"
            ):
                self.tournament.num_rounds = new_rounds
                self.update_history_log(f"Number of rounds set to {new_rounds}.")
                self.mark_dirty()

            if self.tournament.tiebreak_order != new_tiebreaks:
                self.tournament.tiebreak_order = new_tiebreaks
                self.update_history_log("Tiebreak order updated.")
                self.mark_dirty()
                self.standings_tab.update_standings_table_headers()
                self.standings_tab.update_standings_table()

            self._update_ui_state()
            return True
        return False

    def update_history_log(self, message: str):
        """Append a timestamped message to the history log tab."""
        self.history_tab.update_history_log(message)

    def _collect_gui_state(self) -> TournamentGuiState:
        return TournamentGuiState(
            current_round_index=self.current_round_index,
            last_recorded_results_data=list(self.last_recorded_results_data),
        )

    def _apply_gui_state(self, gui_state: TournamentGuiState) -> None:
        self.current_round_index = gui_state.current_round_index
        self.last_recorded_results_data = list(gui_state.last_recorded_results_data)

    def save_tournament(self, save_as=False):
        if not self.tournament:
            return False
        if should_request_save_path(self._current_filepath, save_as):
            filename, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, "Save Tournament", "", "JSON Files (*.json)"
            )
            if not filename:
                return False
            self._current_filepath = filename

        filepath = self._current_filepath
        assert filepath is not None
        try:
            # check to see if file exists, and confirm prior to overwrite
            if QtCore.QFileInfo(filepath).exists():

                logger.warning("save_tournament is trying to right over a file.")
                # confirm before over write
                prompt = build_overwrite_confirmation_prompt()
                if not self.get_confirmation(
                    action=prompt.title, message=prompt.message
                ):
                    return False
                # else continue

            self.persistence_service.save(
                filepath, self.tournament, self._collect_gui_state()
            )
            self.mark_clean()
            self.statusBar().showMessage(build_save_status(filepath))
            self.update_history_log(build_save_history(filepath))
            return True

        except Exception as e:
            message = (
                "exception: '%s' excepted in an `except Exception`. This is bad practice."
                % str(e)
            )
            logging.exception("Error saving tournament:")
            prompt = build_save_error_prompt(e)
            QtWidgets.QMessageBox.critical(
                self, prompt.title, prompt.message
            )
            raise RuntimeError(message)

    def restart_application(self):
        """Restart the application cleanly."""
        utils.restart_application()

    def load_tournament(self):
        if not self.check_save():
            return
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Load Tournament", "", "JSON Files (*.json)"
        )
        if not filename:
            logger.warning("Not loading tournament because no filename provided.")
            return

        try:
            document = self.persistence_service.load(filename)

            self.reset_tournament_state()
            self.tournament = document.tournament
            self._apply_gui_state(document.gui_state)
            self._current_filepath = filename

            self._set_tournament_on_tabs()

            self._refresh_tournament_views()

            self.mark_clean()
            self.update_history_log(build_load_success_history(filename))
            self.statusBar().showMessage(
                build_load_success_status(self.tournament.name)
            )
            try:
                show_notification(
                    self,
                    build_load_success_notification(self.tournament.name),
                    duration=3000,
                    notification_type="info",
                )
            except Exception:
                logger.debug("Could not show load notification.", exc_info=True)
        except Exception as e:
            logging.exception("Error loading tournament:")
            self.reset_tournament_state()
            try:
                show_notification(
                    self,
                    build_load_failure_notification(e),
                    duration=6000,
                    notification_type="error",
                )
            except Exception:
                prompt = build_load_error_prompt(e)
                QtWidgets.QMessageBox.critical(
                    self, prompt.title, prompt.message
                )
        finally:
            self._update_ui_state()

    def _refresh_tournament_views(self) -> None:
        """Refresh all tab displays from the current tournament."""
        self.players_tab.refresh_player_list()
        self.standings_tab.update_standings_table_headers()
        self.standings_tab.update_standings_table()
        self.crosstable_tab.update_crosstable()

        if self.tournament and 0 <= self.current_round_index < len(
            self.tournament.rounds_pairings_ids
        ):
            pairings, bye_player = self.tournament.get_pairings_for_round(
                self.current_round_index
            )
            self.rounds_tab.display_pairings_for_input(
                pairings, [bye_player] if bye_player else []
            )
        else:
            self.rounds_tab.reset_display()

    def check_save(self) -> bool:
        """Check if progress is saved before proceeding, if not prompt user."""
        if not should_prompt_for_unsaved_changes(self._dirty):
            logger.info("check_save_before_proceeding: fount state to be clean.")
            return True
        logger.info("check_save_before_proceeding: fount state to be dirty.")
        prompt = build_unsaved_changes_prompt()
        dialog = UnsavedChangesDialog(prompt, self)
        dialog.exec()

        if dialog.selected_action == "save":
            return should_continue_after_save_prompt("save", self.save_tournament())
        if dialog.selected_action == "discard":
            return should_continue_after_save_prompt("discard", save_succeeded=False)
        return should_continue_after_save_prompt("cancel", save_succeeded=False)

    def show_about_dialog(self):
        """Show the About dialog."""
        dialog = AboutDialog(self)
        dialog.exec()

    def get_confirmation(
        self, action: str = "", message: str = "Are you sure you want to proceed?"
    ) -> bool:
        """Ask the user to confirm a potentially destructive action."""
        reply = QMessageBox.question(
            self,
            action,
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes

    def check_for_pending_update(self) -> bool:
        """Check for a previously downloaded update and ask to install it."""
        return self.update_workflow.check_for_pending_update()

    def check_for_updates_manual(self) -> None:
        """Manually check for updates and notify the user of the result."""
        self.update_workflow.check_for_updates_manual()

    def check_for_updates_auto(self) -> None:
        """Automatically check for updates in the background."""
        self.update_workflow.check_for_updates_auto()

    def prompt_update(self) -> bool:
        """Show a dialog prompting the user to download the new version."""
        return self.update_workflow.prompt_update()

    def start_update_download(self) -> None:
        """Initiate the update download and shows the progress dialog."""
        self.update_workflow.start_update_download()

    def on_update_done(self, success: bool, message: str) -> None:
        """Handle both success and error for update."""
        self.update_workflow.on_update_done(success, message)

    def _restart_with_update(self, extracted_path: str) -> None:
        self.update_workflow.restart_with_update(extracted_path)

    def closeEvent(self, event: QCloseEvent):
        """Handle a close Event, checking if needed."""
        if self.update_workflow.is_updating:
            event.accept()
            return

        if self.check_save():
            logging.info(f"{APP_NAME} closing.")
            event.accept()
        else:
            event.ignore()

    def _on_round_completed(self, round_index: int):
        """Slot called when a round is recorded and the tournament is advanced."""
        self.current_round_index = round_index
        # Sync last_recorded_results_data from rounds_tab to main window
        if hasattr(self.rounds_tab, "last_recorded_results_data"):
            self.last_recorded_results_data = list(
                self.rounds_tab.last_recorded_results_data
            )
        self.mark_dirty()
        self._update_ui_state()

    def _navigate_to_rounds_tab(self):
        """Switch to the Rounds tab."""
        self.tabs.setCurrentWidget(self.rounds_tab)

    def _start_tournament_with_navigation(self):
        """Navigate to Rounds tab and start the tournament."""
        self._navigate_to_rounds_tab()
        self.rounds_tab.start_tournament()

    def _prepare_round_with_navigation(self):
        """Navigate to Rounds tab and prepare the next round."""
        self._navigate_to_rounds_tab()
        self.rounds_tab.prepare_next_round()

    def _record_results_with_navigation(self):
        """Navigate to Rounds tab and record results."""
        self._navigate_to_rounds_tab()
        self.rounds_tab.record_and_advance()

    def _undo_results_with_navigation(self):
        """Navigate to Rounds tab and undo last results."""
        self._navigate_to_rounds_tab()
        self.rounds_tab.undo_last_results()

    def _set_tournament_on_tabs(self):
        """Pass the current tournament object to all tabs so they can access its data."""
        for tab in [
            self.players_tab,
            self.rounds_tab,
            self.standings_tab,
            self.crosstable_tab,
            self.history_tab,
        ]:
            if hasattr(tab, "set_tournament"):
                tab.set_tournament(self.tournament)
        # Also set current_round_index and last_recorded_results_data on rounds_tab
        if hasattr(self.rounds_tab, "set_current_round_index"):
            self.rounds_tab.set_current_round_index(self.current_round_index)
        if hasattr(self.rounds_tab, "last_recorded_results_data"):
            self.rounds_tab.last_recorded_results_data = list(
                self.last_recorded_results_data
            )
        # Ensure UI state is updated after tournament propagation
        self._update_ui_state()

    def _setup_ui(self):
        load_ui_into(self, "main_window.ui")
        self.setWindowTitle(APP_NAME)
        self._setup_main_panel()
        self._setup_menu()
        self._setup_toolbar()
        self.statusBar().showMessage("Ready - Create New or Load Tournament.")
        logging.info(f"{APP_NAME} v{APP_VERSION} started.")

    def _setup_main_panel(self):
        """Create the tab widget and populates it with the modular tab classes."""
        # stacked_widget comes from main_window.ui.
        if not hasattr(self, "stacked_widget"):
            self.stacked_widget = QtWidgets.QStackedWidget()
            self.setCentralWidget(self.stacked_widget)

        # Placeholder for no tournament
        self.tournament_placeholder = TournamentPlaceholder(self)
        self.tournament_placeholder.create_tournament_requested.connect(
            self.prompt_new_tournament
        )
        self.tournament_placeholder.import_tournament_requested.connect(
            self.load_tournament
        )
        self.stacked_widget.addWidget(self.tournament_placeholder)

        self.tabs = QtWidgets.QTabWidget()
        self.stacked_widget.addWidget(self.tabs)

        self.players_tab = PlayersView(self)
        self.rounds_tab = TournamentView(self)
        self.standings_tab = StandingsView(self)
        self.crosstable_tab = CrosstableView(self)
        self.history_tab = HistoryView(self)

        self.players_tab.status_message.connect(self.statusBar().showMessage)
        self.rounds_tab.status_message.connect(self.statusBar().showMessage)
        self.players_tab.history_message.connect(self.history_tab.update_history_log)
        self.rounds_tab.history_message.connect(self.history_tab.update_history_log)
        self.players_tab.dirty.connect(self.mark_dirty)
        self.rounds_tab.dirty.connect(self.mark_dirty)
        self.rounds_tab.dirty.connect(self._update_ui_state)
        self.rounds_tab.round_completed.connect(self._on_round_completed)
        self.rounds_tab.standings_update_requested.connect(
            self.standings_tab.update_standings_table
        )
        self.rounds_tab.standings_update_requested.connect(
            self.players_tab.refresh_player_list
        )

        self.tabs.addTab(self.players_tab, "Players")
        self.tabs.addTab(self.rounds_tab, "Rounds")
        self.tabs.addTab(self.standings_tab, "Standings")
        self.tabs.addTab(self.crosstable_tab, "Crosstable")
        self.tabs.addTab(self.history_tab, "History Log")

    def _create_action(
        self, text: str, slot: callable, shortcut: str = "", tooltip: str = ""
    ) -> QAction:
        """Create and configure a QAction."""
        action = QAction(text, self)
        action.triggered.connect(slot)
        if shortcut:
            action.setShortcut(QtGui.QKeySequence(shortcut))
        if tooltip:
            action.setToolTip(tooltip)
            action.setStatusTip(tooltip)
        action.setIconVisibleInMenu(False)
        return action

    def _setup_menu(self):
        """Set up the main menu bar, connecting actions to methods in the main window or tabs."""
        menu_bar = self.menuBar()

        # File Menu
        file_menu = menu_bar.addMenu("&File")
        self.new_action = self._create_action(
            "&New Tournament...", self.prompt_new_tournament, "Ctrl+N"
        )
        self.load_action = self._create_action(
            "&Load Tournament...", self.load_tournament, "Ctrl+O"
        )
        self.save_action = self._create_action(
            "&Save Tournament", self.save_tournament, "Ctrl+S"
        )
        self.save_as_action = self._create_action(
            "Save Tournament &As...",
            lambda: self.save_tournament(save_as=True),
            "Ctrl+Shift+S",
        )
        self.export_standings_action = self._create_action(
            "&Export Standings...", self.standings_tab.export_standings
        )
        self.settings_action = self._create_action(
            "S&ettings...", self.show_settings_dialog
        )
        self.exit_action = self._create_action("E&xit", self.close, "Ctrl+Q")

        file_menu.addActions(
            [self.new_action, self.load_action, self.save_action, self.save_as_action]
        )
        file_menu.addSeparator()
        file_menu.addActions(
            [
                self.export_standings_action,
            ]
        )
        file_menu.addSeparator()
        file_menu.addAction(self.settings_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        # Tournament Menu
        tournament_menu = menu_bar.addMenu("&Tournament")
        self.start_action = self._create_action(
            "&Start Tournament", self._start_tournament_with_navigation
        )
        self.prepare_round_action = self._create_action(
            "&Prepare Next Round", self._prepare_round_with_navigation
        )
        self.record_results_action = self._create_action(
            "&Record Results && Advance", self._record_results_with_navigation
        )
        self.undo_results_action = self._create_action(
            "&Undo Last Results", self._undo_results_with_navigation
        )
        tournament_menu.addActions(
            [
                self.start_action,
                self.prepare_round_action,
                self.record_results_action,
                self.undo_results_action,
            ]
        )

        # Player Menu
        player_menu = menu_bar.addMenu("&Players")
        self.add_player_action = self._create_action(
            "&Add Player...", self.players_tab.add_player_detailed
        )
        player_menu.addAction(self.add_player_action)
        self.import_players_action = self._create_action(
            "&Import Players from CSV...", self.players_tab.import_players_csv
        )
        self.export_players_action = self._create_action(
            "&Export Players to CSV...", self.players_tab.export_players_to_file
        )
        player_menu.addSeparator()
        player_menu.addActions(
            [
                self.import_players_action,
                self.export_players_action,
            ]
        )

        # Help Menu
        help_menu = menu_bar.addMenu("&Help")
        help_menu.addAction("About...", self.show_about_dialog)
        self.update_action = self._create_action(
            "Check for &Updates...", self.check_for_updates_manual
        )
        help_menu.addAction(self.update_action)

    def _setup_toolbar(self) -> None:
        """Set up the main application toolbar.

        The toolbar contains file operations and tournament control actions.
        Tournament control actions show/hide based on tournament state for a cleaner UX.
        Icons are loaded from the system theme for a native look and feel.
        """
        toolbar = self.addToolBar("Main Toolbar")
        toolbar.setObjectName("MainToolbar")
        toolbar.setProperty("class", "MainToolbar")
        # Prevent detaching / floating
        toolbar.setMovable(False)

        toolbar.setMovable(False)

        if hasattr(toolbar, "setFloatable"):
            toolbar.setFloatable(False)

        toolbar.setAllowedAreas(
            Qt.ToolBarArea.TopToolBarArea | Qt.ToolBarArea.BottomToolBarArea
        )
        toolbar.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
        toolbar.setIconSize(QtCore.QSize(18, 18))

        QtGui.QIcon.setThemeName("Adwaita")

        # Set icons for file actions
        self.new_action.setIcon(QtGui.QIcon.fromTheme("document-new"))
        self.load_action.setIcon(QtGui.QIcon.fromTheme("document-open"))
        self.save_action.setIcon(QtGui.QIcon.fromTheme("document-save"))
        self.start_action.setIcon(QtGui.QIcon.fromTheme("media-playback-start"))
        self.record_results_action.setIcon(QtGui.QIcon.fromTheme("media-record"))
        self.prepare_round_action.setIcon(QtGui.QIcon.fromTheme("go-next"))

        # Add file-related toolbar actions
        toolbar.addActions([self.new_action, self.load_action, self.save_action])
        self.file_separator = toolbar.addSeparator()
        toolbar.addAction(self.start_action)
        toolbar.addAction(self.record_results_action)
        toolbar.addAction(self.prepare_round_action)

        # Separator before tournament info when tournament is started
        self.tournament_separator = toolbar.addSeparator()

        self.toolbar_tournament_label = QtWidgets.QLabel("No Tournament Loaded")
        self.toolbar_tournament_label.setProperty("class", "ToolbarTournamentLabel")
        self.toolbar_tournament_label.setContentsMargins(8, 0, 8, 0)
        toolbar.addWidget(self.toolbar_tournament_label)

    def _update_ui_state(self):
        """Update the state of UI elements based on the tournament's current state.

        Tournament control actions (Start, Prepare, Record, Undo) are now
        primarily managed in the Tournament tab. This method focuses on:
        - Menu action enable/disable states
        - File operations state
        - Player operations state
        - Window title and status bar updates
        """
        state = build_main_window_ui_state(
            tournament=self.tournament,
            current_round_index=self.current_round_index,
            last_recorded_results_data=self.last_recorded_results_data,
            dirty=self._dirty,
            current_filepath=self._current_filepath,
            app_name=APP_NAME,
        )

        # Switch between placeholder and tabs using stacked widget
        if state.tournament_exists:
            self.stacked_widget.setCurrentWidget(self.tabs)
        else:
            self.stacked_widget.setCurrentWidget(self.tournament_placeholder)

        # Update menu actions (still accessible via menus)
        self.start_action.setEnabled(state.can_start)
        self.prepare_round_action.setEnabled(state.can_prepare)
        self.record_results_action.setEnabled(state.can_record)
        self.undo_results_action.setEnabled(state.can_undo)

        # Update toolbar visibility
        self.start_action.setVisible(state.can_start)
        self.record_results_action.setVisible(state.can_record)
        self.prepare_round_action.setVisible(state.can_prepare)
        self.file_separator.setVisible(
            True
        )  # Always show separator between file actions and info
        self.tournament_separator.setVisible(state.tournament_exists)

        # File operations
        self.save_action.setEnabled(state.can_save)
        self.save_as_action.setEnabled(state.can_save)
        self.export_standings_action.setEnabled(state.can_export_standings)

        # Player operations
        self.import_players_action.setEnabled(state.can_import_players)
        self.export_players_action.setEnabled(state.can_export_players)
        self.add_player_action.setEnabled(state.can_add_player)
        self.settings_action.setEnabled(state.can_open_settings)

        # Delegate UI state updates to the tabs themselves
        self.players_tab.update_ui_state()
        self.rounds_tab.update_ui_state()
        self.standings_tab.update_ui_state()
        self.crosstable_tab.update_ui_state()
        self.history_tab.update_ui_state()

        self.setWindowTitle(state.window_title)
        self.statusBar().showMessage(state.status_message)
        self.toolbar_tournament_label.setText(state.toolbar_tournament_label)


#  LocalWords:  bbb px msgbox MainToolbar
