"""Dialog for choosing which FIDE and CFC player lists are kept locally."""

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

from typing import Optional

from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt

from gambitpairing.gui.gui_utils import get_native_icon
from gambitpairing.gui.player_list_workflow import (
    PlayerListUpdater,
    player_list_updater,
)
from gambitpairing.gui.ui_loader import load_ui_into, required_child
from gambitpairing.player_lists.catalog import (
    CFC_ATTRIBUTION,
    FIDE_ATTRIBUTION,
    PLAYER_LISTS,
    PlayerListSpec,
)
from gambitpairing.player_lists.store import ListState
from gambitpairing.player_lists.updates import CheckOutcome

LIST_COLUMNS: tuple[str, ...] = ("List", "Source", "State")
LIST_COLUMN = 0
SOURCE_COLUMN = 1
STATE_COLUMN = 2

FIDE_DOWNLOADS_URL = "https://ratings.fide.com/download_lists.phtml"
CFC_RATINGS_URL = "https://www.chess.ca/en/ratings/"


class PlayerListsDialog(QtWidgets.QDialog):
    """Choose the kept lists, see their state and update them on demand."""

    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget] = None,
        updater: Optional[PlayerListUpdater] = None,
    ) -> None:
        super().__init__(parent)
        self.updater = updater or player_list_updater()
        self.store = self.updater.store
        load_ui_into(self, "player_lists_dialog.ui")
        self._bind_ui_controls()
        self._populate_lists()

        self.lists_table.itemSelectionChanged.connect(self._on_selection_changed)
        self.btn_update_now.clicked.connect(self._update_selected_now)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.updater.status.connect(self._on_updater_status)
        self.updater.list_updated.connect(self._on_list_updated)
        self.updater.busy_changed.connect(self._set_busy)
        self._set_busy(self.updater.is_busy)

    def _bind_ui_controls(self) -> None:
        self.intro_label = required_child(self, QtWidgets.QLabel, "intro_label")
        self.lists_table = required_child(self, QtWidgets.QTableWidget, "lists_table")
        self.details_label = required_child(self, QtWidgets.QLabel, "details_label")
        self.progress_label = required_child(self, QtWidgets.QLabel, "progress_label")
        self.progress_bar = required_child(self, QtWidgets.QProgressBar, "progress_bar")
        self.btn_update_now = required_child(
            self, QtWidgets.QPushButton, "btn_update_now"
        )
        self.attribution_label = required_child(
            self, QtWidgets.QLabel, "attribution_label"
        )
        self.buttons = required_child(self, QtWidgets.QDialogButtonBox, "buttons")

        self.btn_update_now.setIcon(
            get_native_icon(
                "view-refresh", QtWidgets.QStyle.StandardPixmap.SP_BrowserReload
            )
        )
        self.attribution_label.setText(
            f'{FIDE_ATTRIBUTION} <a href="{FIDE_DOWNLOADS_URL}">FIDE download '
            f"lists</a><br>{CFC_ATTRIBUTION} "
            f'<a href="{CFC_RATINGS_URL}">CFC ratings</a>'
        )

        self.lists_table.setColumnCount(len(LIST_COLUMNS))
        self.lists_table.verticalHeader().setVisible(False)
        header = self.lists_table.horizontalHeader()
        for index, title in enumerate(LIST_COLUMNS):
            self.lists_table.setHorizontalHeaderItem(
                index, QtWidgets.QTableWidgetItem(title)
            )
            header.setSectionResizeMode(
                index,
                (
                    QtWidgets.QHeaderView.ResizeMode.Stretch
                    if index == STATE_COLUMN
                    else QtWidgets.QHeaderView.ResizeMode.ResizeToContents
                ),
            )

    def _populate_lists(self) -> None:
        selected = set(self.store.selected_keys())
        self.lists_table.setRowCount(len(PLAYER_LISTS))
        for row, spec in enumerate(PLAYER_LISTS):
            name_item = QtWidgets.QTableWidgetItem(spec.name)
            name_item.setData(Qt.ItemDataRole.UserRole, spec.key)
            name_item.setFlags(name_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            name_item.setCheckState(
                Qt.CheckState.Checked
                if spec.key in selected
                else Qt.CheckState.Unchecked
            )
            name_item.setToolTip(spec.description)
            self.lists_table.setItem(row, LIST_COLUMN, name_item)
            source_item = QtWidgets.QTableWidgetItem(spec.source)
            self.lists_table.setItem(row, SOURCE_COLUMN, source_item)
            self.lists_table.setItem(row, STATE_COLUMN, QtWidgets.QTableWidgetItem())
            self._refresh_row(row)

    def _row_for_key(self, key: str) -> int:
        for row in range(self.lists_table.rowCount()):
            item = self.lists_table.item(row, LIST_COLUMN)
            if item and item.data(Qt.ItemDataRole.UserRole) == key:
                return row
        return -1

    def _spec_for_row(self, row: int) -> Optional[PlayerListSpec]:
        if 0 <= row < len(PLAYER_LISTS):
            return PLAYER_LISTS[row]
        return None

    def _refresh_row(self, row: int, status_text: str = "") -> None:
        spec = self._spec_for_row(row)
        item = self.lists_table.item(row, STATE_COLUMN)
        if spec is None or item is None:
            return
        text = status_text or self.store.describe_state(spec)
        if not status_text and self.updater.is_active(spec.key):
            text = "Waiting to check…"
        item.setText(text)
        item.setToolTip(self.store.describe_skipped(spec) or text)

    def selected_keys(self) -> list[str]:
        """Return the keys of the checked lists."""
        keys = []
        for row in range(self.lists_table.rowCount()):
            item = self.lists_table.item(row, LIST_COLUMN)
            if item and item.checkState() == Qt.CheckState.Checked:
                keys.append(item.data(Qt.ItemDataRole.UserRole))
        return keys

    def _current_spec(self) -> Optional[PlayerListSpec]:
        return self._spec_for_row(self.lists_table.currentRow())

    def _on_selection_changed(self) -> None:
        spec = self._current_spec()
        self.btn_update_now.setEnabled(
            spec is not None and not self.updater.is_active(spec.key)
        )
        if spec is None:
            return
        details = spec.description
        skipped = self.store.describe_skipped(spec)
        if skipped:
            details = f"{details}\n{skipped}."
        self.details_label.setText(details)

    def _update_selected_now(self) -> None:
        spec = self._current_spec()
        if spec is None:
            return
        self.updater.update_now([spec.key])
        self._refresh_row(self.lists_table.currentRow())
        self.btn_update_now.setEnabled(False)

    def _on_updater_status(self, key: str, text: str) -> None:
        row = self._row_for_key(key)
        if row >= 0:
            self._refresh_row(row, text)
        self.progress_label.setText(text)

    def _on_list_updated(self, outcome: CheckOutcome) -> None:
        row = self._row_for_key(outcome.key)
        if row >= 0:
            self._refresh_row(row)
        spec = self._spec_for_row(row)
        if spec is not None:
            failed = self.store.state(spec) is ListState.ERROR
            separator = ": error: " if failed else ": "
            self.progress_label.setText(f"{spec.name}{separator}{outcome.message}")
        self._on_selection_changed()

    def _set_busy(self, busy: bool) -> None:
        self.progress_bar.setVisible(busy)
        if busy:
            self.progress_bar.setRange(0, 0)
        self._on_selection_changed()

    def accept(self) -> None:
        """Save the selection; local copies of unchecked lists are deleted."""
        keys = self.selected_keys()
        removed = [
            spec.name
            for spec in PLAYER_LISTS
            if spec.key not in keys and self.store.has_data_file(spec)
        ]
        if removed:
            answer = QtWidgets.QMessageBox.question(
                self,
                "Delete Player Lists",
                "Delete the local copy of " + ", ".join(removed) + "?",
                QtWidgets.QMessageBox.StandardButton.Yes
                | QtWidgets.QMessageBox.StandardButton.Cancel,
            )
            if answer != QtWidgets.QMessageBox.StandardButton.Yes:
                return
        self.store.save_selection(keys)
        super().accept()

    def done(self, result: int) -> None:
        for signal, slot in (
            (self.updater.status, self._on_updater_status),
            (self.updater.list_updated, self._on_list_updated),
            (self.updater.busy_changed, self._set_busy),
        ):
            try:
                signal.disconnect(slot)
            except (RuntimeError, TypeError):
                pass
        super().done(result)
