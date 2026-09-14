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
from gambitpairing.gui.gui_utils import get_native_icon
from gambitpairing.gui.ui_loader import load_ui_into, required_child
from gambitpairing.utils.utility_functions import resize_list_to_show_all_items


class SettingsDialog(QtWidgets.QDialog):
    def __init__(
        self,
        num_rounds: int,
        tiebreak_order: List[str],
        tournament_mode: str = DEFAULT_MODE,
        parent=None,
    ):
        super().__init__(parent)
        self.current_tiebreak_order = list(tiebreak_order)
        self.tournament_mode = tournament_mode

        load_ui_into(self, "tournament_settings_dialog.ui")

        self.rounds_group = required_child(self, QtWidgets.QGroupBox, "rounds_group")
        self.rounds_label = required_child(self, QtWidgets.QLabel, "rounds_label")
        self.spin_num_rounds = required_child(
            self, QtWidgets.QSpinBox, "spin_num_rounds"
        )
        self.spin_num_rounds.setValue(num_rounds)

        self.mode_combo = required_child(self, QtWidgets.QComboBox, "mode_combo")
        self.mode_combo.addItem("USCF", MODE_USCF)
        self.mode_combo.addItem("FIDE", MODE_FIDE)
        self.mode_combo.setCurrentIndex(0 if tournament_mode == MODE_USCF else 1)
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)

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
        self.btn_tiebreak_up.setIcon(
            get_native_icon("go-up", QtWidgets.QStyle.StandardPixmap.SP_ArrowUp)
        )
        self.btn_tiebreak_down.setIcon(
            get_native_icon("go-down", QtWidgets.QStyle.StandardPixmap.SP_ArrowDown)
        )
        self.btn_tiebreak_up.setToolTip("Move selected tiebreak up")
        self.btn_tiebreak_down.setToolTip("Move selected tiebreak down")
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

    def on_mode_changed(self) -> None:
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
