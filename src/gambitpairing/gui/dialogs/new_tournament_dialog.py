"""Dialog for creating new tournament."""

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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from typing import List, Optional, Tuple

from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt

from gambitpairing.constants import (
    DEFAULT_FIDE_TIEBREAK_ORDER,
    DEFAULT_MODE,
    DEFAULT_USCF_TIEBREAK_ORDER,
    MODE_FIDE,
    MODE_USCF,
    TIEBREAK_NAMES,
)
from gambitpairing.gui.gui_utils import get_native_icon
from gambitpairing.gui.ui_loader import load_ui_into, required_child
from gambitpairing.utils.utility_functions import resize_list_to_show_all_items


class NewTournamentDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tournament_mode = DEFAULT_MODE
        self.current_tiebreak_order = list(DEFAULT_USCF_TIEBREAK_ORDER)
        self.player_count = 5

        load_ui_into(self, "new_tournament_dialog.ui")

        self.name_edit = required_child(self, QtWidgets.QLineEdit, "name_edit")
        self.rounds_label = required_child(self, QtWidgets.QLabel, "rounds_label")
        self.rounds_spin = required_child(self, QtWidgets.QSpinBox, "rounds_spin")
        self.mode_combo = required_child(self, QtWidgets.QComboBox, "mode_combo")
        self.mode_combo.addItem("USCF", MODE_USCF)
        self.mode_combo.addItem("FIDE", MODE_FIDE)
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        self.tiebreak_list = required_child(
            self, QtWidgets.QListWidget, "tiebreak_list"
        )
        self.pairing_combo = required_child(self, QtWidgets.QComboBox, "pairing_combo")
        self.pairing_combo.addItem("Dutch System", "dutch_swiss")
        self.pairing_combo.addItem("Round Robin (All-Play-All)", "round_robin")
        self.pairing_combo.addItem("Manual Pairing", "manual")
        self.experimental_dutch_check = required_child(
            self, QtWidgets.QCheckBox, "experimental_dutch_check"
        )

        self.btn_tiebreak_up = required_child(
            self, QtWidgets.QPushButton, "btn_tiebreak_up"
        )
        self.btn_tiebreak_down = required_child(
            self, QtWidgets.QPushButton, "btn_tiebreak_down"
        )
        self.btn_tiebreak_up.setIcon(
            get_native_icon("go-up", QtWidgets.QStyle.StandardPixmap.SP_ArrowUp)
        )
        self.btn_tiebreak_down.setIcon(
            get_native_icon("go-down", QtWidgets.QStyle.StandardPixmap.SP_ArrowDown)
        )
        self.btn_tiebreak_up.setToolTip("Move selected tiebreak up")
        self.btn_tiebreak_down.setToolTip("Move selected tiebreak down")
        self.btn_pairing_info = required_child(
            self, QtWidgets.QPushButton, "btn_pairing_info"
        )
        self.btn_pairing_info.setIcon(
            get_native_icon(
                "help-about", QtWidgets.QStyle.StandardPixmap.SP_MessageBoxInformation
            )
        )
        self.buttons = required_child(self, QtWidgets.QDialogButtonBox, "buttons")

        self.populate_tiebreak_list()
        resize_list_to_show_all_items(self.tiebreak_list)

        self.btn_tiebreak_up.clicked.connect(self.move_tiebreak_up)
        self.btn_tiebreak_down.clicked.connect(self.move_tiebreak_down)
        self.btn_pairing_info.clicked.connect(self.show_pairing_info)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.pairing_combo.currentIndexChanged.connect(self.on_pairing_system_changed)
        self.rounds_spin.valueChanged.connect(self.on_rounds_changed)

        self.on_pairing_system_changed()

    def populate_tiebreak_list(self) -> None:
        self.tiebreak_list.clear()
        for tb_key in self.current_tiebreak_order:
            display_name = TIEBREAK_NAMES.get(tb_key, tb_key)
            item = QtWidgets.QListWidgetItem(display_name)
            item.setData(Qt.ItemDataRole.UserRole, tb_key)
            self.tiebreak_list.addItem(item)

    def move_tiebreak_up(self) -> None:
        current_row = self.tiebreak_list.currentRow()
        if current_row > 0:
            item = self.tiebreak_list.takeItem(current_row)
            self.tiebreak_list.insertItem(current_row - 1, item)
            self.tiebreak_list.setCurrentRow(current_row - 1)

    def move_tiebreak_down(self) -> None:
        current_row = self.tiebreak_list.currentRow()
        if current_row < self.tiebreak_list.count() - 1:
            item = self.tiebreak_list.takeItem(current_row)
            self.tiebreak_list.insertItem(current_row + 1, item)
            self.tiebreak_list.setCurrentRow(current_row + 1)

    def update_order_from_list(self) -> None:
        self.current_tiebreak_order = [
            self.tiebreak_list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.tiebreak_list.count())
        ]

    def accept(self) -> None:
        self.update_order_from_list()
        super().accept()

    def show_pairing_info(self) -> None:
        """show pairing system information"""
        use_experimental_dutch = (
            self.pairing_combo.currentData() == "dutch_swiss"
            and self.experimental_dutch_check.isChecked()
        )
        if use_experimental_dutch:
            dutch_info = {
                "title": "Dutch System (Gambit - Experimental)",
                "desc": "Uses Gambit Pairing's native Dutch Swiss implementation. It is available for testing and comparison while it continues to improve.",
                "fide": True,
                "uscf": True,
                "details": "<ul><li><b>Pairing Logic:</b> Uses Gambit's native Dutch Swiss implementation for score groups, rematch avoidance, colour allocation, and bye selection.</li><li><b>Status:</b> Experimental; the standard Dutch System uses BBP Pairings by default.</li><li><b>Best For:</b> Testing, comparison, and development.</li></ul>",
            }
        else:
            dutch_info = {
                "title": "Dutch System (BBP/FIDE)",
                "desc": "The standard FIDE Dutch Swiss system, powered by the upstream BBP Pairings engine with Gambit's native implementation as a fallback.",
                "fide": True,
                "uscf": True,
                "details": "<ul><li><b>Pairing Logic:</b> Uses the upstream BBP Pairings Dutch engine for FIDE-compliant score groups, rematch avoidance, colour allocation, and bye selection.</li><li><b>Fallback:</b> Gambit's experimental Dutch engine is used automatically if BBP is unavailable or cannot represent a tournament state.</li><li><b>Best For:</b> Most open tournaments and FIDE events.</li></ul>",
            }
        info = {
            "dutch_swiss": dutch_info,
            "round_robin": {
                "title": "Round Robin",
                "desc": "Every player plays every other player. Used for small events and FIDE title norm tournaments.",
                "fide": True,
                "uscf": True,
                "details": "<ul><li><b>Pairing Logic:</b> All-play-all, each player faces every other once.</li><li><b>Best For:</b> Small groups, title norm events, club championships.</li><li><b>Notes:</b> Number of rounds = number of players - 1.</li></ul>",
            },
            "manual": {
                "title": "Manual Pairing",
                "desc": "Complete manual control over all pairings. Tournament director creates all pairings by hand for each round.",
                "fide": False,
                "uscf": False,
                "details": "<ul><li><b>Pairing Logic:</b> No automatic pairing. TD manually creates all matches each round.</li><li><b>Best For:</b> Special events, demonstration games, custom formats.</li><li><b>Features:</b> Full pairing editor with click-to-place controls, a player pool, drag-to-remove assignments, and color swapping.</li><li><b>Notes:</b> Maximum flexibility but requires manual work for every round.</li></ul>",
            },
        }
        dialog = QtWidgets.QDialog(self)
        load_ui_into(dialog, "pairing_info_dialog.ui")
        toc = required_child(dialog, QtWidgets.QListWidget, "toc")
        title_label = required_child(dialog, QtWidgets.QLabel, "title_label")
        desc_label = required_child(dialog, QtWidgets.QLabel, "desc_label")
        html_details = required_child(dialog, QtWidgets.QTextBrowser, "html_details")
        button_box = required_child(dialog, QtWidgets.QDialogButtonBox, "button_box")

        keys = list(info.keys())
        for k in keys:
            item = QtWidgets.QListWidgetItem(info[k]["title"])
            item.setData(Qt.ItemDataRole.UserRole, k)
            toc.addItem(item)

        def update_details(idx):
            key = toc.item(idx).data(Qt.ItemDataRole.UserRole)
            d = info.get(key, {})
            title_label.setText(d.get("title", ""))
            desc_label.setText(d.get("desc", ""))
            html_details.setHtml(d.get("details", ""))

        toc.currentRowChanged.connect(update_details)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        # Select the current pairing system by default
        current_key = self.pairing_combo.currentData()
        default_idx = keys.index(current_key) if current_key in keys else 0
        toc.setCurrentRow(default_idx)
        update_details(default_idx)
        dialog.exec()

    def on_mode_changed(self) -> None:
        """Use the selected federation's defaults for new tournaments."""
        new_mode = self.mode_combo.currentData()
        if new_mode == self.tournament_mode:
            return
        self.tournament_mode = new_mode
        self.current_tiebreak_order = list(
            DEFAULT_FIDE_TIEBREAK_ORDER
            if new_mode == MODE_FIDE
            else DEFAULT_USCF_TIEBREAK_ORDER
        )
        self.populate_tiebreak_list()
        resize_list_to_show_all_items(self.tiebreak_list)

    def get_data(self) -> Optional[Tuple[str, int, List[str], str, bool]]:
        name = self.name_edit.text().strip()
        if not name:
            QtWidgets.QMessageBox.warning(
                self, "Input Error", "Tournament name cannot be empty."
            )
            return None
        pairing_system = self.pairing_combo.currentData()
        return (
            name,
            self.rounds_spin.value(),
            self.current_tiebreak_order,
            pairing_system,
            pairing_system == "dutch_swiss"
            and self.experimental_dutch_check.isChecked(),
        )

    def on_pairing_system_changed(self):
        key = self.pairing_combo.currentData()
        is_dutch = key == "dutch_swiss"
        self.experimental_dutch_check.setVisible(is_dutch)
        self.experimental_dutch_check.setEnabled(is_dutch)

        if key == "round_robin":
            # For round robin, rounds = players - 1, hide the input
            self.rounds_spin.setVisible(False)
            self.rounds_label.setVisible(False)
            self.rounds_spin.setToolTip(
                "Number of rounds is fixed for Round Robin: players - 1."
            )
            self.rounds_spin.setValue(max(1, self.player_count - 1))
        else:
            self.rounds_spin.setVisible(True)
            self.rounds_label.setVisible(True)
            self.rounds_spin.setToolTip("")

    def set_player_count(self, count: int) -> None:
        self.player_count = count
        if self.pairing_combo.currentData() == "round_robin":
            self.rounds_spin.setValue(max(1, count - 1))

    def on_rounds_changed(self, value) -> None:
        # Optionally, update player count if not round robin
        if self.pairing_combo.currentData() != "round_robin":
            self.player_count = value + 1  # For UI consistency


#  LocalWords:  swiss QGroupBox QDialogButtonBox fide desc colors
