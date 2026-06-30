"""Integrated Player Management Dialog with tabs for manual editing, FIDE import, and tournament players."""

from typing import Any, Callable, Dict, List, Optional, Tuple

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import QObject, Qt, QThread, pyqtSignal

from gambitpairing.gui.gui_utils import get_colored_icon, update_widget_style
from gambitpairing.gui.dialogs.player_management_data import (
    PlayerFormFields,
    build_player_data_from_fields,
    has_fide_fields,
    project_tournament_player_row,
    search_result_count_text,
)
from gambitpairing.gui.notification import show_notification
from gambitpairing.gui.ui_loader import load_ui_into, required_child
from gambitpairing.models.player import Player
from gambitpairing.utils.api import (
    get_cfc_player_info,
    get_fide_player_info,
    search_fide_players,
)

# FIDE columns with better minimum widths
FIDE_COLUMNS: List[Tuple[str, int]] = [
    ("", 5),  # checkbox - smaller to reduce wasted space
    ("Name", 300),
    ("FIDE ID", 100),
    ("Fed", 80),
    ("Title", 80),
    ("Std", 80),
    ("Rapid", 100),  # Increased for better fit
    ("Blitz", 80),
    ("B-Year", 80),
    ("Gender", 110),  # Increased for better fit
]

# Define CFC columns - adjust these based on actual CFC database structure
CFC_COLUMNS: List[Tuple[str, int]] = [
    ("", 5),  # Checkbox column
    ("CFC ID", 80),  # CFC membership ID
    ("Name", 200),  # Player name
    ("Rating", 80),  # CFC rating
    ("Province", 80),  # Province/Territory
    ("City", 120),  # City
    ("Expiry", 80),  # Membership expiry
    ("Status", 80),  # Active/Inactive status
]

# Tournament players columns
TOURNAMENT_COLUMNS: List[Tuple[str, int]] = [
    ("Name", 200),
    ("Rating", 80),
    ("Age", 60),
    ("Gender", 80),
]


class _FideWorker(QObject):
    finished = pyqtSignal(object, object)  # (result, error)

    def __init__(self, fn: Callable, *args, **kwargs):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs
        self._interrupted = False

    def interrupt(self):
        """Mark this worker as interrupted."""
        self._interrupted = True

    @QtCore.pyqtSlot()
    def run(self):
        try:
            # Check if we've been interrupted before starting
            if self._interrupted:
                return

            result = self._fn(*self._args, **self._kwargs)

            # Check if we've been interrupted before emitting
            if not self._interrupted:
                self.finished.emit(result, None)
        except Exception as e:
            # Only emit error if we weren't interrupted
            if not self._interrupted:
                self.finished.emit(None, e)


class PlayerManagementDialog(QtWidgets.QDialog):
    """Integrated dialog for player management with tabs for editing, FIDE import, and tournament view."""

    def __init__(
        self, parent=None, player_data: Optional[Dict[str, Any]] = None, tournament=None
    ):
        super().__init__(parent)
        self.player_data = player_data or {}
        self.tournament = tournament
        self._thread = None
        self._worker = None
        self._selected_player_data = None
        self._player_data_changed = False  # Track if data has been changed/imported
        self._cleaning_up = False  # Track if we're in cleanup mode
        self._editing_player_id = None  # Track which player is being edited (if any)

        self.setWindowTitle("Player Management")
        self.setModal(True)
        self.resize(900, 600)

        load_ui_into(self, "player_management_dialog.ui")
        self.setProperty("class", "PlayerManagementDialog")
        self._bind_ui_controls()
        self._configure_details_tab()
        self._configure_fide_tab()
        self._configure_cfc_tab()
        self._configure_tournament_tab()

        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        # Install event filter for Enter key handling
        self.installEventFilter(self)

        if self.player_data:
            self._populate_details_form()

    def _bind_ui_controls(self) -> None:
        """Bind required Designer controls to the dialog's public API fields."""
        self.tab_widget = required_child(self, QtWidgets.QTabWidget, "tab_widget")
        self.buttons = required_child(self, QtWidgets.QDialogButtonBox, "buttons")

        self.details_tab = required_child(self, QtWidgets.QWidget, "details_tab")
        self.fide_tab = required_child(self, QtWidgets.QWidget, "fide_tab")
        self.cfc_tab = required_child(self, QtWidgets.QWidget, "cfc_tab")
        self.tournament_tab = required_child(self, QtWidgets.QWidget, "tournament_tab")

        self.name_edit = required_child(self, QtWidgets.QLineEdit, "name_edit")
        self.rating_spin = required_child(self, QtWidgets.QSpinBox, "rating_spin")
        self.gender_combo = required_child(self, QtWidgets.QComboBox, "gender_combo")
        self.dob_edit = required_child(self, QtWidgets.QDateEdit, "dob_edit")
        self.phone_edit = required_child(self, QtWidgets.QLineEdit, "phone_edit")
        self.email_edit = required_child(self, QtWidgets.QLineEdit, "email_edit")
        self.club_edit = required_child(self, QtWidgets.QLineEdit, "club_edit")
        self.federation_edit = required_child(
            self, QtWidgets.QLineEdit, "federation_edit"
        )
        self.fide_group = required_child(self, QtWidgets.QGroupBox, "fide_group")
        self.fide_id_edit = required_child(self, QtWidgets.QLineEdit, "fide_id_edit")
        self.fide_title_edit = required_child(
            self, QtWidgets.QLineEdit, "fide_title_edit"
        )
        self.fide_std_edit = required_child(self, QtWidgets.QLineEdit, "fide_std_edit")
        self.fide_rapid_edit = required_child(
            self, QtWidgets.QLineEdit, "fide_rapid_edit"
        )
        self.fide_blitz_edit = required_child(
            self, QtWidgets.QLineEdit, "fide_blitz_edit"
        )

        self.search_edit = required_child(self, QtWidgets.QLineEdit, "search_edit")
        self.btn_search = required_child(self, QtWidgets.QPushButton, "btn_search")
        self.btn_clear = required_child(self, QtWidgets.QPushButton, "btn_clear")
        self.fide_table = required_child(self, QtWidgets.QTableWidget, "fide_table")
        self.results_info_label = required_child(
            self, QtWidgets.QLabel, "results_info_label"
        )
        self.fide_progress = required_child(
            self, QtWidgets.QProgressBar, "fide_progress"
        )
        self.btn_use_selected = required_child(
            self, QtWidgets.QPushButton, "btn_use_selected"
        )

        self.cfc_search_edit = required_child(
            self, QtWidgets.QLineEdit, "cfc_search_edit"
        )
        self.btn_cfc_search = required_child(
            self, QtWidgets.QPushButton, "btn_cfc_search"
        )
        self.btn_cfc_clear = required_child(
            self, QtWidgets.QPushButton, "btn_cfc_clear"
        )
        self.cfc_table = required_child(self, QtWidgets.QTableWidget, "cfc_table")
        self.cfc_results_info_label = required_child(
            self, QtWidgets.QLabel, "cfc_results_info_label"
        )
        self.cfc_progress = required_child(
            self, QtWidgets.QProgressBar, "cfc_progress"
        )
        self.btn_use_selected_cfc = required_child(
            self, QtWidgets.QPushButton, "btn_use_selected_cfc"
        )

        self.tournament_stack = required_child(
            self, QtWidgets.QStackedWidget, "tournament_stack"
        )
        self.tournament_empty_page = required_child(
            self, QtWidgets.QWidget, "tournament_empty_page"
        )
        self.tournament_table_page = required_child(
            self, QtWidgets.QWidget, "tournament_table_page"
        )
        self.btn_empty_go_fide = required_child(
            self, QtWidgets.QPushButton, "btn_empty_go_fide"
        )
        self.btn_empty_go_details = required_child(
            self, QtWidgets.QPushButton, "btn_empty_go_details"
        )
        self.tournament_table = required_child(
            self, QtWidgets.QTableWidget, "tournament_table"
        )
        self.btn_edit_tournament_player = required_child(
            self, QtWidgets.QPushButton, "btn_edit_tournament_player"
        )

    def _configure_details_tab(self) -> None:
        self.name_edit.textChanged.connect(
            lambda: setattr(self, "_player_data_changed", True)
        )
        self._configure_copy_button("btn_copy_name", self.name_edit.text, "Name")
        self._configure_copy_button(
            "btn_copy_rating", lambda: str(self.rating_spin.value()), "Rating"
        )
        self._configure_copy_button("btn_copy_phone", self.phone_edit.text, "Phone")
        self._configure_copy_button("btn_copy_email", self.email_edit.text, "Email")
        self._configure_copy_button("btn_copy_club", self.club_edit.text, "Club")
        self._configure_copy_button(
            "btn_copy_federation", self.federation_edit.text, "Federation"
        )
        self._configure_copy_button("btn_copy_fide_id", self.fide_id_edit.text, "FIDE ID")
        self._configure_copy_button("btn_copy_fide_title", self.fide_title_edit.text, "Title")
        self._configure_copy_button(
            "btn_copy_fide_std", self.fide_std_edit.text, "Standard Rating"
        )
        self._configure_copy_button(
            "btn_copy_fide_rapid", self.fide_rapid_edit.text, "Rapid Rating"
        )
        self._configure_copy_button(
            "btn_copy_fide_blitz", self.fide_blitz_edit.text, "Blitz Rating"
        )

    def _configure_copy_button(
        self, name: str, text_getter: Callable[[], str], field_name: str
    ) -> None:
        button = required_child(self, QtWidgets.QPushButton, name)
        button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        button.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        button.setFixedSize(32, 32)
        icon = QtGui.QIcon.fromTheme("edit-copy")
        if not icon or icon.isNull():
            icon = get_colored_icon("copy.svg", "#444", 16)
        button.setIcon(icon)
        button.setIconSize(QtCore.QSize(18, 18))
        button.clicked.connect(
            lambda: self._copy_to_clipboard(text_getter(), field_name)
        )

    def _configure_fide_tab(self) -> None:
        self.search_edit.installEventFilter(self)
        self.btn_search.clicked.connect(self._on_search)
        self.btn_clear.clicked.connect(self._clear_fide_results)
        self._configure_results_table(self.fide_table, FIDE_COLUMNS)
        self.fide_table.itemSelectionChanged.connect(self._on_fide_selection_changed)
        self.fide_table.itemDoubleClicked.connect(self._use_selected_fide_player)
        self.fide_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.fide_table.customContextMenuRequested.connect(self._show_fide_context_menu)
        self.btn_use_selected.clicked.connect(self._use_selected_fide_player)

    def _configure_cfc_tab(self) -> None:
        self.cfc_search_edit.installEventFilter(self)
        self.btn_cfc_search.clicked.connect(self._on_cfc_search)
        self.btn_cfc_clear.clicked.connect(self._clear_cfc_results)
        self._configure_results_table(self.cfc_table, CFC_COLUMNS)
        self.cfc_table.itemSelectionChanged.connect(self._on_cfc_selection_changed)
        self.cfc_table.itemDoubleClicked.connect(self._use_selected_cfc_player)
        self.cfc_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.cfc_table.customContextMenuRequested.connect(self._show_cfc_context_menu)
        self.btn_use_selected_cfc.clicked.connect(self._use_selected_cfc_player)

    def _configure_results_table(
        self, table: QtWidgets.QTableWidget, columns: List[Tuple[str, int]]
    ) -> None:
        table.setColumnCount(len(columns))
        table.verticalHeader().setVisible(False)
        header = table.horizontalHeader()
        for index, (title, width) in enumerate(columns):
            table.setHorizontalHeaderItem(index, QtWidgets.QTableWidgetItem(title))
            table.setColumnWidth(index, width)
            header.setMinimumSectionSize(width)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)

    def _set_search_status(
        self, label: QtWidgets.QLabel, text: str, state: str = "idle"
    ) -> None:
        label.setText(text)
        label.setProperty("state", state)
        update_widget_style(label)

    def _configure_tournament_tab(self) -> None:
        if not self.tournament:
            self.tab_widget.removeTab(self.tab_widget.indexOf(self.tournament_tab))
            return

        self.tab_widget.setTabText(
            self.tab_widget.indexOf(self.tournament_tab),
            f"Tournament Players ({len(self.tournament.players)})",
        )
        self.btn_empty_go_fide.clicked.connect(lambda: self.tab_widget.setCurrentIndex(1))
        self.btn_empty_go_details.clicked.connect(
            lambda: self.tab_widget.setCurrentIndex(0)
        )

        if len(self.tournament.players) == 0:
            self.tournament_stack.setCurrentWidget(self.tournament_empty_page)
            return

        self.tournament_stack.setCurrentWidget(self.tournament_table_page)
        self._configure_results_table(self.tournament_table, TOURNAMENT_COLUMNS)
        header = self.tournament_table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        for index in range(1, len(TOURNAMENT_COLUMNS)):
            header.setSectionResizeMode(index, QtWidgets.QHeaderView.ResizeMode.Fixed)
        self.tournament_table.itemSelectionChanged.connect(
            self._on_tournament_selection_changed
        )
        self.tournament_table.itemDoubleClicked.connect(
            self._edit_selected_tournament_player
        )
        self.btn_edit_tournament_player.clicked.connect(
            self._edit_selected_tournament_player
        )
        self._populate_tournament_table()


    def _copy_to_clipboard(self, text: str, field_name: str = "") -> None:
        """Copy text to clipboard with feedback using notification."""
        if not text.strip():
            show_notification(
                self,
                (
                    f"Nothing to copy - {field_name} is empty"
                    if field_name
                    else "Nothing to copy"
                ),
                1500,
                "warning",  # Use warning type for empty fields
            )
            return

        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(text.strip())

        # Show success notification
        display_text = text.strip()
        if len(display_text) > 20:
            display_text = display_text[:20] + "..."

        show_notification(
            self,
            (
                f"Copied {field_name}: {display_text}"
                if field_name
                else f"Copied: {display_text}"
            ),
            2000,
            "success",  # Use success type for successful copies
        )

    # Supporting methods for CFC functionality
    def _on_cfc_search(self):
        """Handle CFC search button click."""
        search_term = self.cfc_search_edit.text().strip()
        if not search_term:
            QtWidgets.QMessageBox.information(
                self,
                "Search Required",
                "Please enter a player name or CFC ID to search.",
            )
            return

        self._search_cfc_players(search_term)

    def _search_cfc_players(self, search_term):
        """Search for CFC players."""
        self.cfc_progress.setVisible(True)
        self.cfc_progress.setRange(0, 0)  # Indeterminate progress
        self.btn_cfc_search.setEnabled(False)
        self._set_search_status(
            self.cfc_results_info_label, "Searching CFC database...", "busy"
        )

        try:
            results = get_cfc_player_info(search_term)

            self._populate_cfc_results(results, search_term)

        except Exception as e:
            QtWidgets.QMessageBox.warning(
                self, "Search Error", f"Failed to search CFC database:\n{str(e)}"
            )
            self._set_search_status(self.cfc_results_info_label, "Search failed", "error")

        finally:
            self.cfc_progress.setVisible(False)
            self.btn_cfc_search.setEnabled(True)
            self.btn_cfc_clear.setEnabled(True)

    def _populate_cfc_results(self, results, search_term):
        """Populate the CFC results table."""
        self.cfc_table.setRowCount(len(results))

        for row, player in enumerate(results):
            # Checkbox
            checkbox = QtWidgets.QCheckBox()
            self.cfc_table.setCellWidget(row, 0, checkbox)

            # Player data
            items = [
                player.get("cfc_id", ""),
                player.get("name", ""),
                str(player.get("rating", "")),
                player.get("province", ""),
                player.get("city", ""),
                player.get("expiry_date", ""),
                player.get("status", ""),
            ]

            for col, text in enumerate(items, 1):
                item = QtWidgets.QTableWidgetItem(str(text))
                item.setData(Qt.ItemDataRole.UserRole, player)  # Store full player data
                self.cfc_table.setItem(row, col, item)

        # Update results info
        if results:
            self._set_search_status(
                self.cfc_results_info_label,
                f"Found {len(results)} player(s) for '{search_term}'",
                "success",
            )
        else:
            self._set_search_status(
                self.cfc_results_info_label,
                f"No players found for '{search_term}'. Try a different search term.",
                "warning",
            )

    def _clear_cfc_results(self):
        """Clear CFC search results."""
        self.cfc_table.setRowCount(0)
        self.cfc_search_edit.clear()
        self._set_search_status(
            self.cfc_results_info_label,
            "Search for players above to see results here",
            "idle",
        )
        self.btn_cfc_clear.setEnabled(False)
        self.btn_use_selected_cfc.setEnabled(False)

    def _on_cfc_selection_changed(self):
        """Handle CFC table selection change."""
        has_selection = bool(self.cfc_table.selectedItems())
        self.btn_use_selected_cfc.setEnabled(has_selection)

    def _use_selected_cfc_player(self):
        """Import the selected CFC player."""
        current_row = self.cfc_table.currentRow()
        if current_row < 0:
            QtWidgets.QMessageBox.information(
                self, "No Selection", "Please select a player to import."
            )
            return

        # Get player data from the selected row
        item = self.cfc_table.item(current_row, 1)  # CFC ID column
        if item:
            player_data = item.data(Qt.ItemDataRole.UserRole)
            self._import_cfc_player_data(player_data)

    def _import_cfc_player_data(self, player_data):
        """Import CFC player data to the Player Details tab."""
        if not player_data:
            return

        try:
            # Convert CFC API data to standardized player dict using adapter
            from gambitpairing.utils.api_adapters import cfc_api_to_player_dict

            standardized_data = cfc_api_to_player_dict(player_data)

            # Switch to Player Details tab
            self.tab_widget.setCurrentIndex(0)

            # Populate form fields with standardized data
            self.name_edit.setText(standardized_data.get("name", ""))
            self.rating_spin.setValue(standardized_data.get("rating", 1000))

            # Set gender
            gender = standardized_data.get("gender")
            if gender:
                gender_text = (
                    "Male" if gender == "M" else "Female" if gender == "F" else ""
                )
                if gender_text:
                    idx = self.gender_combo.findText(gender_text)
                    if idx >= 0:
                        self.gender_combo.setCurrentIndex(idx)

            # Set date of birth if available
            dob = standardized_data.get("date_of_birth")
            if dob:
                birth_date = QtCore.QDate(dob.year, dob.month, dob.day)
                if birth_date.isValid():
                    self.dob_edit.setDate(birth_date)

            # Set province/federation
            self.federation_edit.setText(standardized_data.get("federation", ""))

            # Clear fields not available from CFC
            self.phone_edit.setText("")
            self.email_edit.setText("")
            self.club_edit.setText("")

            # Set CFC ID if the field exists
            cfc_id = standardized_data.get("cfc_id")
            if hasattr(self, "cfc_id_edit") and cfc_id:
                self.cfc_id_edit.setText(str(cfc_id))

            # Store the standardized player data for later use
            self._selected_player_data = standardized_data
            self._player_data_changed = True  # Mark that we have new data to save

            # Show success message using notification
            show_notification(
                self,
                f"Successfully imported: {standardized_data.get('name', 'Unknown')}",
                2500,
                "success",
            )

        except Exception as e:
            QtWidgets.QMessageBox.warning(
                self, "Import Error", f"Failed to import player data:\n{str(e)}"
            )

    def _show_cfc_context_menu(self, position):
        """Show context menu for CFC results table."""
        item = self.cfc_table.itemAt(position)
        if not item:
            return

        menu = QtWidgets.QMenu(self)

        # Copy actions
        copy_name_action = menu.addAction("Copy Name")
        copy_cfc_id_action = menu.addAction("Copy CFC ID")
        copy_rating_action = menu.addAction("Copy Rating")
        menu.addSeparator()
        copy_all_action = menu.addAction("Copy All Data")

        action = menu.exec(self.cfc_table.mapToGlobal(position))

        if action:
            row = item.row()
            clipboard = QtWidgets.QApplication.clipboard()

            if action == copy_name_action:
                clipboard.setText(self.cfc_table.item(row, 2).text())  # Name column
            elif action == copy_cfc_id_action:
                clipboard.setText(self.cfc_table.item(row, 1).text())  # CFC ID column
            elif action == copy_rating_action:
                clipboard.setText(self.cfc_table.item(row, 3).text())  # Rating column
            elif action == copy_all_action:
                # Copy all visible data for the row
                data_parts = []
                for col in range(
                    1, self.cfc_table.columnCount()
                ):  # Skip checkbox column
                    header = self.cfc_table.horizontalHeaderItem(col).text()
                    value = self.cfc_table.item(row, col).text()
                    data_parts.append(f"{header}: {value}")
                clipboard.setText(" | ".join(data_parts))

    def _query_cfc_database(self, search_term, is_id_search):
        """
        Query the CFC database API.

        This is a placeholder method that should be implemented with actual CFC API calls.
        The CFC may have a different API structure than FIDE.

        Parameters
        ----------
            search_term: The search term (name or CFC ID)
            is_id_search: True if searching by CFC ID, False if by name

        Returns
        -------
            List of player dictionaries with CFC data
        """
        # Placeholder - replace with actual CFC API implementation
        # You'll need to research the CFC's available APIs or web scraping methods
        # for now, this is not implemented
        raise NotImplementedError

    def _populate_details_form(self):
        """Populate the details form with player data."""

        def _set(widget, value):
            if hasattr(widget, "setText") and value is not None:
                widget.setText(str(value))

        self.name_edit.setText(self.player_data.get("name", ""))

        rating = self.player_data.get("rating", 1000)
        if rating:
            self.rating_spin.setValue(int(rating))

        # Handle gender (sync sex -> gender)
        gender = self.player_data.get("gender") or self.player_data.get("sex")
        if gender:
            if gender == "M":
                self.gender_combo.setCurrentText("Male")
            elif gender == "F":
                self.gender_combo.setCurrentText("Female")
            else:
                idx = self.gender_combo.findText(gender)
                if idx >= 0:
                    self.gender_combo.setCurrentIndex(idx)
                else:
                    self.gender_combo.setCurrentIndex(idx if idx >= 0 else 0)

        # Date of birth
        dob_str = self.player_data.get("date_of_birth")
        if dob_str:
            try:
                dob_qdate = QtCore.QDate.fromString(dob_str, "yyyy-MM-dd")
                if dob_qdate.isValid():
                    self.dob_edit.setDate(dob_qdate)
            except (ValueError, TypeError):
                pass

        self.phone_edit.setText(self.player_data.get("phone", "") or "")
        self.email_edit.setText(self.player_data.get("email", "") or "")
        self.club_edit.setText(self.player_data.get("club", "") or "")
        self.federation_edit.setText(self.player_data.get("federation", "") or "")

        # FIDE information (now editable)
        if any(
            self.player_data.get(key)
            for key in [
                "fide_id",
                "fide_title",
                "fide_standard",
                "fide_rapid",
                "fide_blitz",
            ]
        ):
            _set(self.fide_id_edit, self.player_data.get("fide_id"))
            _set(self.fide_title_edit, self.player_data.get("fide_title"))
            _set(self.fide_std_edit, self.player_data.get("fide_standard"))
            _set(self.fide_rapid_edit, self.player_data.get("fide_rapid"))
            _set(self.fide_blitz_edit, self.player_data.get("fide_blitz"))
            self.fide_group.setVisible(True)

    def _populate_tournament_table(self):
        """Populate the tournament players table."""
        if not self.tournament:
            return

        self.tournament_table.setRowCount(0)
        for player in self.tournament.players.values():
            self._append_tournament_row(player)

        self.tournament_table.resizeRowsToContents()

    def _append_tournament_row(self, player: Player):
        """Add a player row to the tournament table."""
        row = self.tournament_table.rowCount()
        self.tournament_table.insertRow(row)
        projection = project_tournament_player_row(player)

        # Name
        name_item = QtWidgets.QTableWidgetItem(projection.name)
        name_item.setData(Qt.ItemDataRole.UserRole, projection.player_id)
        self.tournament_table.setItem(row, 0, name_item)

        # Rating
        self.tournament_table.setItem(
            row, 1, QtWidgets.QTableWidgetItem(projection.rating)
        )

        # Age (handle None case safely)
        self.tournament_table.setItem(
            row, 2, QtWidgets.QTableWidgetItem(projection.age)
        )

        # Gender
        gender_item = QtWidgets.QTableWidgetItem(projection.gender)
        self.tournament_table.setItem(row, 3, gender_item)

    def eventFilter(self, obj, event):
        """Handle Enter key in search field."""
        if event.type() == QtCore.QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
                if obj == self.search_edit:
                    self._on_search()
                    return True
        return super().eventFilter(obj, event)

    def _set_fide_busy(self, busy: bool, status_text: str = "") -> None:
        """Set the UI state for FIDE operations with status update."""
        controls = [
            self.search_edit,
            self.btn_search,
            self.btn_use_selected,
        ]

        for control in controls:
            control.setEnabled(not busy)

        self.fide_progress.setVisible(busy)
        if busy:
            self.fide_progress.setRange(0, 0)  # Indeterminate
            if status_text:
                self._set_search_status(self.results_info_label, status_text, "busy")
        else:
            self.fide_progress.setVisible(False)

    def _on_search(self) -> None:
        """Unified search for players by name or FIDE ID with auto-detection."""
        # Prevent overlapping searches
        if self._thread and self._thread.isRunning():
            return

        text = self.search_edit.text().strip()
        if not text:
            QtWidgets.QMessageBox.information(
                self,
                "Search Required",
                "Please enter a player name or FIDE ID to search.",
            )
            return

        # Auto-detect search type: if it's all digits, treat as FIDE ID
        if text.isdigit():
            # FIDE ID search
            try:
                fid = int(text)
                if fid <= 0:
                    raise ValueError("FIDE ID must be positive")
            except ValueError:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Invalid FIDE ID",
                    "Please enter a valid FIDE ID (positive number only).\n"
                    "Example: 1503014 for Magnus Carlsen",
                )
                return

            def _fetch_one() -> List[Dict[str, Any]]:
                info = get_fide_player_info(str(fid))
                return [info] if info else []

            # Set cancellation flag for uniformity
            self._current_search_cancel_flag = {"cancelled": False}
            self._run_async(_fetch_one, status_text=f"Looking up FIDE ID {fid}...")
        else:
            # Name search
            if len(text) < 2:
                QtWidgets.QMessageBox.information(
                    self,
                    "Search Too Short",
                    "Please enter at least 2 characters for name search.",
                )
                return

            # Prepare cooperative cancellation flag
            self._current_search_cancel_flag = {"cancelled": False}

            def is_cancelled():
                return self._current_search_cancel_flag["cancelled"]

            self._run_async(
                lambda: search_fide_players(name=text, is_cancelled=is_cancelled),
                status_text=f"Searching FIDE database for '{text}'...",
            )

    def _clear_fide_results(self) -> None:
        """Clear the FIDE search results table."""
        self.fide_table.setRowCount(0)
        self.btn_use_selected.setEnabled(False)
        self.btn_clear.setEnabled(False)
        self.fide_group.setVisible(False)

        # Reset info label
        self._set_search_status(
            self.results_info_label,
            "Search for players above to see results here",
            "idle",
        )

        # Clear search field
        self.search_edit.clear()

    def _run_async(self, fn: Callable, status_text: str = "Processing...") -> None:
        """Run function in background thread with proper cleanup of previous jobs."""
        # Always abort any existing job before starting a new one
        self._abort_current_job()

        # Set busy state with status
        self._set_fide_busy(True, status_text)

        # Create new worker and thread
        self._worker = _FideWorker(fn)
        self._thread = QThread()
        self._worker.moveToThread(self._thread)

        # Connect signals with unique connection to prevent multiple connections
        self._worker.finished.connect(self._on_fide_finished)
        self._thread.started.connect(self._worker.run)
        self._thread.setParent(self)  # ensure dialog owns lifetime

        # Start the thread
        self._thread.start()

    def _on_fide_finished(self, result, error) -> None:
        """Handle completion of FIDE operation."""
        # Check if we've already cleaned up (aborted) - ignore late signals
        if not self._thread or not self._worker or self._cleaning_up:
            return

        if error:
            self._set_search_status(
                self.results_info_label, f"Search failed: {error}", "error"
            )
            QtWidgets.QMessageBox.warning(self, "FIDE Search Error", f"Error: {error}")
        elif result:
            self._display_fide_results(result)
        else:
            self._set_search_status(
                self.results_info_label,
                "No players found. Try a different search term.",
                "warning",
            )
            QtWidgets.QMessageBox.information(self, "No Results", "No players found.")

        self._set_fide_busy(False)
        # Gracefully finalize thread post-finish
        self._finalize_thread()

    def _finalize_thread(self):
        thread = self._thread
        worker = self._worker
        if not thread:
            return
        if worker:
            try:
                worker.finished.disconnect(self._on_fide_finished)
            except (RuntimeError, TypeError):
                pass
        if thread.isRunning():
            thread.quit()
            if not thread.wait(1500):
                thread.terminate()
                thread.wait(200)
        if worker:
            worker.deleteLater()
        self._thread = None
        self._worker = None

    def _display_fide_results(self, players: List[Dict[str, Any]]) -> None:
        self.fide_table.setRowCount(0)
        for p in players:
            self._append_fide_row(p)
        self.fide_table.resizeRowsToContents()

        # Update info label and enable clear button
        player_count = len(players)
        self._set_search_status(
            self.results_info_label, search_result_count_text(player_count), "success"
        )
        self.btn_clear.setEnabled(player_count > 0)

    def _append_fide_row(self, p: Dict[str, Any]) -> None:
        row = self.fide_table.rowCount()
        self.fide_table.insertRow(row)

        # Checkbox
        chk = QtWidgets.QTableWidgetItem()
        chk.setFlags(
            Qt.ItemFlag.ItemIsUserCheckable
            | Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
        )
        chk.setCheckState(Qt.CheckState.Unchecked)
        self.fide_table.setItem(row, 0, chk)

        # Name
        name_item = QtWidgets.QTableWidgetItem(str(p.get("name") or ""))
        name_item.setData(Qt.ItemDataRole.UserRole, p)  # Store full player data
        self.fide_table.setItem(row, 1, name_item)

        # Other columns
        self.fide_table.setItem(
            row, 2, QtWidgets.QTableWidgetItem(str(p.get("fide_id") or ""))
        )
        self.fide_table.setItem(
            row, 3, QtWidgets.QTableWidgetItem(str(p.get("federation") or ""))
        )
        self.fide_table.setItem(
            row, 4, QtWidgets.QTableWidgetItem(str(p.get("title") or ""))
        )

        def fmt_rating(val):
            return "" if val in (None, 0) else str(val)

        self.fide_table.setItem(
            row, 5, QtWidgets.QTableWidgetItem(fmt_rating(p.get("standard_rating")))
        )
        self.fide_table.setItem(
            row, 6, QtWidgets.QTableWidgetItem(fmt_rating(p.get("rapid_rating")))
        )
        self.fide_table.setItem(
            row, 7, QtWidgets.QTableWidgetItem(fmt_rating(p.get("blitz_rating")))
        )
        self.fide_table.setItem(
            row, 8, QtWidgets.QTableWidgetItem(str(p.get("birth_year") or ""))
        )

        # Convert gender for display
        gender = p.get("gender")
        if not gender and str(p.get("title") or "").upper().startswith("W"):
            gender = "F"
        gender_display = ""
        if gender == "M":
            gender_display = "Male"
        elif gender == "F":
            gender_display = "Female"
        self.fide_table.setItem(row, 9, QtWidgets.QTableWidgetItem(gender_display))

        self.fide_table.setRowHeight(row, 22)

    def _show_fide_context_menu(self, position):
        """Show context menu for FIDE search results."""
        item = self.fide_table.itemAt(position)
        if not item:
            return

        menu = QtWidgets.QMenu()

        # Import action
        import_action = menu.addAction("Import Player")
        import_action.setEnabled(True)
        import_action.triggered.connect(self._use_selected_fide_player)

        # Copy actions for various fields
        menu.addSeparator()

        row = item.row()
        name_item = self.fide_table.item(row, 1)
        if name_item and name_item.text().strip():
            copy_name_action = menu.addAction(f"Copy Name: {name_item.text()}")
            copy_name_action.triggered.connect(
                lambda: self._copy_to_clipboard(name_item.text(), "Name")
            )

        fide_id_item = self.fide_table.item(row, 2)
        if fide_id_item and fide_id_item.text().strip():
            copy_id_action = menu.addAction(f"Copy FIDE ID: {fide_id_item.text()}")
            copy_id_action.triggered.connect(
                lambda: self._copy_to_clipboard(fide_id_item.text(), "FIDE ID")
            )

        # Show menu
        if menu.actions():
            menu.exec(self.fide_table.mapToGlobal(position))

    def _on_fide_selection_changed(self):
        """Handle FIDE table selection change."""
        selected_rows = self.fide_table.selectionModel().selectedRows()
        self.btn_use_selected.setEnabled(len(selected_rows) > 0)

    def _on_tournament_selection_changed(self):
        """Handle tournament table selection change."""
        selected_rows = self.tournament_table.selectionModel().selectedRows()
        self.btn_edit_tournament_player.setEnabled(len(selected_rows) > 0)

    def _use_selected_fide_player(self):
        """Use the selected FIDE player data in the details form."""
        selected_rows = self.fide_table.selectionModel().selectedRows()
        if not selected_rows:
            return

        # Get the first selected player
        row = selected_rows[0].row()
        name_item = self.fide_table.item(row, 1)
        if not name_item:
            return

        player_data = name_item.data(Qt.ItemDataRole.UserRole)
        if not player_data:
            return

        # Convert FIDE API data to standardized player dict using adapter
        from gambitpairing.utils.api_adapters import fide_api_to_player_dict

        standardized_data = fide_api_to_player_dict(player_data)

        # Update details form with standardized data
        self.name_edit.setText(standardized_data.get("name", ""))
        self.rating_spin.setValue(standardized_data.get("rating", 1000))

        # Set gender
        gender = standardized_data.get("gender")
        if gender:
            gender_text = "Male" if gender == "M" else "Female" if gender == "F" else ""
            if gender_text:
                idx = self.gender_combo.findText(gender_text)
                if idx >= 0:
                    self.gender_combo.setCurrentIndex(idx)

        self.federation_edit.setText(standardized_data.get("federation", ""))

        # Set date of birth if available
        dob = standardized_data.get("date_of_birth")
        if dob:
            birth_date = QtCore.QDate(dob.year, dob.month, dob.day)
            if birth_date.isValid():
                self.dob_edit.setDate(birth_date)

        # Clear other fields that might not be available from FIDE
        self.phone_edit.setText("")
        self.email_edit.setText("")
        self.club_edit.setText("")

        # Show FIDE info (now editable)
        self.fide_id_edit.setText(str(standardized_data.get("fide_id", "") or ""))
        self.fide_title_edit.setText(str(standardized_data.get("fide_title", "") or ""))
        self.fide_std_edit.setText(
            str(standardized_data.get("fide_standard", "") or "")
        )
        self.fide_rapid_edit.setText(str(standardized_data.get("fide_rapid", "") or ""))
        self.fide_blitz_edit.setText(str(standardized_data.get("fide_blitz", "") or ""))

        self.fide_group.setVisible(True)

        # Store the standardized player data for later use
        self._selected_player_data = standardized_data
        self._player_data_changed = True  # Mark that we have new data to save

        # Switch to details tab
        self.tab_widget.setCurrentIndex(0)

        # Show brief success feedback using notification
        show_notification(
            self,
            f"Successfully imported: {standardized_data.get('name', 'Unknown')}",
            2500,
            "success",
        )

    def _edit_selected_tournament_player(self):
        """Edit the selected tournament player."""
        selected_rows = self.tournament_table.selectionModel().selectedRows()
        if not selected_rows:
            return

        row = selected_rows[0].row()
        name_item = self.tournament_table.item(row, 0)
        if not name_item:
            return

        player_id = name_item.data(Qt.ItemDataRole.UserRole)
        player = self.tournament.players.get(player_id)
        if not player:
            return

        # Store the player ID so we know we're editing this player
        self._editing_player_id = player_id

        # Load player data into details form
        self.player_data = {
            "name": player.name,
            "rating": player.rating,
            "gender": player.gender,
            "date_of_birth": player.date_of_birth,
            "phone": player.phone or "",
            "email": player.email or "",
            "club": player.club or "",
            "federation": player.federation or "",
            "fide_id": getattr(player, "fide_id", None),
            "fide_title": getattr(player, "fide_title", None),
            "fide_standard": getattr(player, "fide_standard", None),
            "fide_rapid": getattr(player, "fide_rapid", None),
            "fide_blitz": getattr(player, "fide_blitz", None),
            "birth_year": getattr(player, "birth_year", None),
        }

        self._populate_details_form()

        # Switch to details tab
        self.tab_widget.setCurrentIndex(0)

    def accept(self):
        """Override accept to validate input."""
        # Always validate if we're on Player Details tab OR if we have imported data that needs to be saved
        current_tab = self.tab_widget.currentIndex()
        has_player_data = (
            self._player_data_changed
            or self._selected_player_data
            or bool(self.name_edit.text().strip())
        )

        if (
            current_tab == 0 or has_player_data
        ):  # Player Details tab or has player data to save
            if not self.name_edit.text().strip():
                # If on other tabs but have imported data, switch to details tab first
                if current_tab != 0:
                    self.tab_widget.setCurrentIndex(0)
                QtWidgets.QMessageBox.warning(
                    self, "Validation Error", "Player name cannot be empty."
                )
                self.name_edit.setFocus()
                return

            # Validate rating is reasonable
            rating = self.rating_spin.value()
            if rating < 0 or rating > 3500:
                if current_tab != 0:
                    self.tab_widget.setCurrentIndex(0)
                QtWidgets.QMessageBox.warning(
                    self, "Validation Error", "Rating must be between 0 and 3500."
                )
                self.rating_spin.setFocus()
                return

            # Validate date of birth
            if (
                self.dob_edit.date().isValid()
                and self.dob_edit.date() > QtCore.QDate.currentDate()
            ):
                if current_tab != 0:
                    self.tab_widget.setCurrentIndex(0)
                QtWidgets.QMessageBox.warning(
                    self, "Validation Error", "Date of birth cannot be in the future."
                )
                self.dob_edit.setFocus()
                return

            # Validate age makes sense (not too old or too young)
            dob_date = self.dob_edit.date()
            if dob_date != QtCore.QDate(2000, 1, 1):  # Not default date
                today = QtCore.QDate.currentDate()
                age = today.year() - dob_date.year()
                if age > 150 or age < 0:
                    if current_tab != 0:
                        self.tab_widget.setCurrentIndex(0)
                    QtWidgets.QMessageBox.warning(
                        self,
                        "Validation Error",
                        f"Calculated age ({age}) seems unrealistic. Please check the date of birth.",
                    )
                    self.dob_edit.setFocus()
                    return

            # Validate email format if provided
            email = self.email_edit.text().strip()
            if email and "@" not in email:
                if current_tab != 0:
                    self.tab_widget.setCurrentIndex(0)
                QtWidgets.QMessageBox.warning(
                    self,
                    "Validation Error",
                    "Please enter a valid email address or leave empty.",
                )
                self.email_edit.setFocus()
                return

            # Validate FIDE ID if provided
            fide_id_text = self.fide_id_edit.text().strip()
            if fide_id_text:
                try:
                    fide_id = int(fide_id_text)
                    if fide_id <= 0:
                        raise ValueError("FIDE ID must be positive")
                except ValueError:
                    if current_tab != 0:
                        self.tab_widget.setCurrentIndex(0)
                    QtWidgets.QMessageBox.warning(
                        self, "Validation Error", "FIDE ID must be a positive number."
                    )
                    self.fide_id_edit.setFocus()
                    return

        elif current_tab != 0 and not has_player_data:
            # If we're on other tabs and no data has been imported/entered, ask user to go to details tab
            result = QtWidgets.QMessageBox.question(
                self,
                "Save Player",
                "To save a player, please fill out the details on the Player Details tab.\n\n"
                "Would you like to go to the Player Details tab now?",
                QtWidgets.QMessageBox.StandardButton.Yes
                | QtWidgets.QMessageBox.StandardButton.Cancel,
            )
            if result == QtWidgets.QMessageBox.StandardButton.Yes:
                self.tab_widget.setCurrentIndex(0)
                self.name_edit.setFocus()
            return
        super().accept()

    def closeEvent(self, event) -> None:
        """Ensure proper cleanup when dialog is closed."""
        self._abort_current_job()
        super().closeEvent(event)

    def reject(self) -> None:
        """Ensure proper cleanup when dialog is cancelled."""
        self._abort_current_job()
        super().reject()

    def get_player_data(self) -> Dict[str, Any]:
        """Get the player data from the form."""
        dob_qdate = self.dob_edit.date()

        fields = PlayerFormFields(
            name=self.name_edit.text(),
            rating=self.rating_spin.value(),
            gender_text=self.gender_combo.currentText(),
            date_of_birth=(
                dob_qdate.toString("yyyy-MM-dd")
                if dob_qdate != QtCore.QDate(2000, 1, 1)
                else ""
            ),
            phone=self.phone_edit.text(),
            email=self.email_edit.text(),
            club=self.club_edit.text(),
            federation=self.federation_edit.text(),
            fide_id=self.fide_id_edit.text(),
            fide_title=self.fide_title_edit.text(),
            fide_standard=self.fide_std_edit.text(),
            fide_rapid=self.fide_rapid_edit.text(),
            fide_blitz=self.fide_blitz_edit.text(),
        )
        selected_birth_year = (
            self._selected_player_data.get("birth_year")
            if self._selected_player_data
            else None
        )
        return build_player_data_from_fields(
            fields,
            include_fide_fields=bool(self._selected_player_data)
            or has_fide_fields(fields),
            selected_birth_year=selected_birth_year,
        )

    def get_editing_player_id(self) -> Optional[str]:
        """Get the ID of the player being edited, if any.

        Returns:
            Player ID if editing an existing player, None if adding a new player
        """
        return self._editing_player_id

    def _abort_current_job(self) -> None:
        """Cooperatively cancel and cleanup the current background job."""
        if not self._thread or self._cleaning_up:
            return

        self._cleaning_up = True
        try:
            # Signal cancellation to search logic if active
            if hasattr(self, "_current_search_cancel_flag"):
                self._current_search_cancel_flag["cancelled"] = True

            # Interrupt worker (prevents emitting results afterwards)
            if self._worker:
                self._worker.interrupt()

            # Give the thread a chance to finish gracefully
            if self._thread.isRunning():
                if not self._thread.wait(500):  # wait 0.5s first
                    if not self._thread.wait(1500):  # total ~2s
                        self._thread.terminate()
                        self._thread.wait(200)

            # Disconnect signal if still connected
            if self._worker:
                try:
                    self._worker.finished.disconnect()
                except (RuntimeError, TypeError):
                    pass
                self._worker.deleteLater()

            # Clear busy UI
            self._set_fide_busy(False)
        finally:
            self._thread = None
            self._worker = None
            self._cleaning_up = False
            if hasattr(self, "_current_search_cancel_flag"):
                del self._current_search_cancel_flag
