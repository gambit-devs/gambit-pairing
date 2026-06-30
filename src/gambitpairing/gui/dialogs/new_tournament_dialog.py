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

from gambitpairing.constants import DEFAULT_TIEBREAK_SORT_ORDER, TIEBREAK_NAMES
from gambitpairing.gui.ui_loader import load_ui_into, required_child
from gambitpairing.utils import resize_list_to_show_all_items


class NewTournamentDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_tiebreak_order = list(DEFAULT_TIEBREAK_SORT_ORDER)
        self.player_count = 5

        load_ui_into(self, "new_tournament_dialog.ui")

        self.name_edit = required_child(self, QtWidgets.QLineEdit, "name_edit")
        self.rounds_label = required_child(self, QtWidgets.QLabel, "rounds_label")
        self.rounds_spin = required_child(self, QtWidgets.QSpinBox, "rounds_spin")
        self.tiebreak_list = required_child(
            self, QtWidgets.QListWidget, "tiebreak_list"
        )
        self.pairing_combo = required_child(
            self, QtWidgets.QComboBox, "pairing_combo"
        )
        self.pairing_combo.addItem("Dutch System (FIDE/USCF-style)", "dutch_swiss")
        self.pairing_combo.addItem("Round Robin (All-Play-All)", "round_robin")
        self.pairing_combo.addItem("Manual Pairing", "manual")

        self.btn_tiebreak_up = required_child(
            self, QtWidgets.QPushButton, "btn_tiebreak_up"
        )
        self.btn_tiebreak_down = required_child(
            self, QtWidgets.QPushButton, "btn_tiebreak_down"
        )
        self.btn_pairing_info = required_child(
            self, QtWidgets.QPushButton, "btn_pairing_info"
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
        info = {
            "dutch_swiss": {
                "title": "Dutch System",
                "desc": "The most widely used Swiss system: players are grouped by score, then paired top-half vs bottom-half within each group, avoiding repeats and balancing colors. Used in FIDE and USCF events. <b>Note:</b> This system is still being developed in Gambit Pairing.",
                "fide": True,
                "uscf": True,
                "details": "<ul><li><b>Pairing Logic:</b> Players are sorted by score, then paired top vs bottom within each score group, avoiding previous opponents and balancing colors.</li><li><b>Best For:</b> Most open tournaments, FIDE/USCF events.</li><li><b>Notes:</b> This is the standard Swiss system for rated events. <b>Note:</b> This system is still being developed in Gambit Pairing.</li></ul>",
            },
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
                "details": "<ul><li><b>Pairing Logic:</b> No automatic pairing. TD manually creates all matches each round.</li><li><b>Best For:</b> Special events, demonstration games, custom formats.</li><li><b>Features:</b> Full pairing editor with drag-and-drop, player pool, edit mode for swapping players.</li><li><b>Notes:</b> Maximum flexibility but requires manual work for every round.</li></ul>",
            },
        }
        dialog = QtWidgets.QDialog(self)
        load_ui_into(dialog, "pairing_info_dialog.ui")
        toc = required_child(dialog, QtWidgets.QListWidget, "toc")
        title_label = required_child(dialog, QtWidgets.QLabel, "title_label")
        desc_label = required_child(dialog, QtWidgets.QLabel, "desc_label")
        html_details = required_child(dialog, QtWidgets.QTextBrowser, "html_details")

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
        # Select the current pairing system by default
        current_key = self.pairing_combo.currentData()
        default_idx = keys.index(current_key) if current_key in keys else 0
        toc.setCurrentRow(default_idx)
        update_details(default_idx)
        dialog.exec()

    def get_data(self) -> Optional[Tuple[str, int, List[str], str]]:
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
        )

    def on_pairing_system_changed(self):
        key = self.pairing_combo.currentData()

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
