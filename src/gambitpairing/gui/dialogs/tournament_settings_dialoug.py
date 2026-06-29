from typing import List, Tuple

from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt

from gambitpairing.constants import TIEBREAK_NAMES
from gambitpairing.gui.ui_loader import load_ui_into, required_child
from gambitpairing.utils import resize_list_to_show_all_items


class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, num_rounds: int, tiebreak_order: List[str], parent=None):
        super().__init__(parent)
        self.current_tiebreak_order = list(tiebreak_order)

        load_ui_into(self, "tournament_settings_dialog.ui")

        self.rounds_group = required_child(
            self, QtWidgets.QGroupBox, "rounds_group"
        )
        self.rounds_label = required_child(self, QtWidgets.QLabel, "rounds_label")
        self.spin_num_rounds = required_child(
            self, QtWidgets.QSpinBox, "spin_num_rounds"
        )
        self.spin_num_rounds.setValue(num_rounds)

        self.tiebreak_list = required_child(
            self, QtWidgets.QListWidget, "tiebreak_list"
        )
        self.populate_tiebreak_list()
        resize_list_to_show_all_items(self.tiebreak_list)

        self.btn_tiebreak_up = required_child(
            self, QtWidgets.QPushButton, "btn_tiebreak_up"
        )
        self.btn_tiebreak_down = required_child(
            self, QtWidgets.QPushButton, "btn_tiebreak_down"
        )
        self.btn_tiebreak_up.clicked.connect(self.move_tiebreak_up)
        self.btn_tiebreak_down.clicked.connect(self.move_tiebreak_down)

        self.buttons = required_child(self, QtWidgets.QDialogButtonBox, "buttons")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

    def configure_round_count_controls(
        self, pairing_system: str | None, tournament_started: bool
    ) -> None:
        """Apply pairing-system rules to the editable round count controls."""
        is_round_robin = pairing_system == "round_robin"
        self.rounds_label.setVisible(not is_round_robin)
        self.spin_num_rounds.setVisible(not is_round_robin)

        if is_round_robin:
            self.spin_num_rounds.setToolTip(
                "Number of rounds is fixed for Round Robin: players - 1."
            )
            return

        self.spin_num_rounds.setEnabled(not tournament_started)
        self.spin_num_rounds.setToolTip("")

    def populate_tiebreak_list(self):
        self.tiebreak_list.clear()
        for tb_key in self.current_tiebreak_order:
            display_name = TIEBREAK_NAMES.get(tb_key, tb_key)
            item = QtWidgets.QListWidgetItem(display_name)
            item.setData(Qt.ItemDataRole.UserRole, tb_key)
            self.tiebreak_list.addItem(item)

    def move_tiebreak_up(self):
        current_row = self.tiebreak_list.currentRow()
        if current_row > 0:
            item = self.tiebreak_list.takeItem(current_row)
            self.tiebreak_list.insertItem(current_row - 1, item)
            self.tiebreak_list.setCurrentRow(current_row - 1)
            self.update_order_from_list()

    def move_tiebreak_down(self):
        current_row = self.tiebreak_list.currentRow()
        if current_row < self.tiebreak_list.count() - 1:
            item = self.tiebreak_list.takeItem(current_row)
            self.tiebreak_list.insertItem(current_row + 1, item)
            self.tiebreak_list.setCurrentRow(current_row + 1)
            self.update_order_from_list()

    def update_order_from_list(self):
        self.current_tiebreak_order = [
            self.tiebreak_list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.tiebreak_list.count())
        ]

    def accept(self):
        self.update_order_from_list()
        super().accept()

    def get_settings(self) -> Tuple[int, List[str]]:
        return self.spin_num_rounds.value(), self.current_tiebreak_order
