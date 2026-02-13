from typing import List, Tuple

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
from gambitpairing.utils import resize_list_to_show_all_items


class SettingsDialog(QtWidgets.QDialog):
    def __init__(
        self,
        num_rounds: int,
        tiebreak_order: List[str],
        tournament_mode: str = DEFAULT_MODE,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Tournament Settings")
        self.setMinimumWidth(350)
        self.current_tiebreak_order = list(tiebreak_order)
        self.tournament_mode = tournament_mode
        layout = QtWidgets.QVBoxLayout(self)
        rounds_group = QtWidgets.QGroupBox("General")
        rounds_layout = QtWidgets.QFormLayout(rounds_group)
        self.spin_num_rounds = QtWidgets.QSpinBox()
        self.spin_num_rounds.setRange(1, 50)
        self.spin_num_rounds.setValue(num_rounds)
        self.spin_num_rounds.setToolTip("Set the total number of rounds.")
        rounds_layout.addRow("Number of Rounds:", self.spin_num_rounds)
        layout.addWidget(rounds_group)

        # Chess Federation group
        mode_group = QtWidgets.QGroupBox("Chess Federation")
        mode_layout = QtWidgets.QHBoxLayout(mode_group)
        self.mode_combo = QtWidgets.QComboBox()
        self.mode_combo.addItem("USCF", MODE_USCF)
        self.mode_combo.addItem("FIDE", MODE_FIDE)
        # Set current mode
        current_index = 0 if tournament_mode == MODE_USCF else 1
        self.mode_combo.setCurrentIndex(current_index)
        self.mode_combo.setToolTip(
            "Select USCF or FIDE federation. This determines the default tiebreaker rules."
        )
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        mode_layout.addWidget(self.mode_combo, stretch=1)
        layout.addWidget(mode_group)

        tiebreak_group = QtWidgets.QGroupBox("Tiebreak Order")
        tiebreak_layout = QtWidgets.QHBoxLayout(tiebreak_group)
        self.tiebreak_list = QtWidgets.QListWidget()
        self.tiebreak_list.setToolTip(
            "Order in which tiebreaks are applied (higher is better). Drag to reorder."
        )
        self.tiebreak_list.setDragDropMode(
            QtWidgets.QAbstractItemView.DragDropMode.InternalMove
        )
        self.populate_tiebreak_list()
        resize_list_to_show_all_items(self.tiebreak_list)
        tiebreak_layout.addWidget(self.tiebreak_list)
        move_button_layout = QtWidgets.QVBoxLayout()
        btn_up = QtWidgets.QPushButton("Up")
        btn_down = QtWidgets.QPushButton("Down")
        btn_up.clicked.connect(self.move_tiebreak_up)
        btn_down.clicked.connect(self.move_tiebreak_down)
        move_button_layout.addStretch()
        move_button_layout.addWidget(btn_up)
        move_button_layout.addWidget(btn_down)
        move_button_layout.addStretch()
        tiebreak_layout.addLayout(move_button_layout)
        layout.addWidget(tiebreak_group)
        self.buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum
        )
        self.buttons.setMinimumHeight(40)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def on_mode_changed(self) -> None:
        """Handle chess federation change, updating default tiebreakers."""
        new_mode = self.mode_combo.currentData()
        if new_mode != self.tournament_mode:
            # Ask user if they want to reset tiebreakers to mode defaults
            response = QtWidgets.QMessageBox.question(
                self,
                "Reset Tiebreakers?",
                f"Would you like to reset tiebreakers to {new_mode} defaults?",
                QtWidgets.QMessageBox.StandardButton.Yes
                | QtWidgets.QMessageBox.StandardButton.No,
            )
            if response == QtWidgets.QMessageBox.StandardButton.Yes:
                self.tournament_mode = new_mode
                if self.tournament_mode == MODE_FIDE:
                    self.current_tiebreak_order = list(DEFAULT_FIDE_TIEBREAK_ORDER)
                else:
                    self.current_tiebreak_order = list(DEFAULT_USCF_TIEBREAK_ORDER)
                self.populate_tiebreak_list()
                resize_list_to_show_all_items(self.tiebreak_list)
            else:
                # Revert the combo box
                current_index = 0 if self.tournament_mode == MODE_USCF else 1
                self.mode_combo.setCurrentIndex(current_index)

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

    def get_settings(self) -> Tuple[int, List[str], str]:
        return (
            self.spin_num_rounds.value(),
            self.current_tiebreak_order,
            self.mode_combo.currentData(),
        )
