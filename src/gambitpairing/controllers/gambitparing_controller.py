"""Main controller for gambit-pairing."""

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

from typing import Optional, List, Tuple

from gambitpairing.models.tournament import Tournament


# BIG 'ol WIP
class GampitPairingController:
    """Central application controller.

    Attributes
    ----------
    TODO
    """

    def __init__(self) -> None:
        # TODO: Figure out the main window
        self.main_window = GambitPairingMainWindow()
        self.window.set_app_instance(app)
        self.window.show()
        logger.info("Setup main window")
        self.tournament: Optional[Tournament] = None
        self.current_round_index: int = 0
        self.last_recorded_results_data: List[Tuple[str, str, float]] = []
        self.filepath: Optional[Path] = None
        self.dirty: bool = False

    def save_tournament(self) -> None:
        """Save the active tournament."""
        logger.info("trying to save tournament.")
        path = self._prompt_save_path()
        if not path:
            logger.info("_prompt_save_path() returned Nothing.")
            raise FileLoadException("_prompt_save_path() returned Nothing.")
        try:
            self.persistence.save(self.app, path)
            self._refresh_ui()
        except SaveError as e:
            self._show_error("Save Error", str(e))
            raise e

    def reset_tournament_state(self):
        """Reset the entire application to a clean state."""
        self.tournament = None
        self.current_round_index = 0
        self.last_recorded_results_data = []
        self.current_tournament_filepath = None
        self.mark_clean()

        self._set_tournament_on_tabs()  # clear tournament tabs

        # Clear tab UI
        self.players_tab.reset_display()
        self.rounds_tab.reset_display()
        self.standings_tab.reset_display()
        self.crosstable_tab.reset_display()
        self.history_tab.reset_display()

        self._update_ui_state()

    def mark_clean(self) -> None:
        """Mask app state as clean."""
        self.dirty = False

    def mark_dirty(self):
        """Mark app state as 'dirty'."""
        self._dirty = True
        self._update_ui_state()
