"""Dialog modules for the GUI."""

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

from .about_dialog import AboutDialog
from .manual_pairing_dialog import ManualPairingDialog
from .new_tournament_dialog import NewTournamentDialog
from .player_management_dialog import PlayerManagementDialog
from .print_options_dialog import PrintOptionsDialog
from .tournament_settings_dialoug import SettingsDialog
from .update_dialog import UpdateDownloadDialog
from .update_prompt_dialog import UpdatePromptDialog

__all__ = [
    "NewTournamentDialog",
    "PlayerManagementDialog",
    "SettingsDialog",
    "ManualPairingDialog",
    "UpdateDownloadDialog",
    "UpdatePromptDialog",
    "AboutDialog",
    "PrintOptionsDialog",
]
