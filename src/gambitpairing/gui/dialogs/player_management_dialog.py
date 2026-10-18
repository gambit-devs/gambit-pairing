"""Integrated Player Management Dialog with tabs for manual editing, FIDE/CFC search, and tournament players."""

from typing import Any, Callable, Dict, Optional, Sequence

from PyQt6 import QtCore, QtWidgets
from PyQt6.QtCore import QObject, Qt, QThread, pyqtSignal

from gambitpairing.gui.dialogs.player_lists_dialog import PlayerListsDialog
from gambitpairing.gui.dialogs.player_management_data import (
    PlayerFormFields,
    build_player_data_from_fields,
    has_fide_fields,
    optional_int_from_text,
    project_tournament_player_row,
)
from gambitpairing.gui.gui_utils import get_native_icon
from gambitpairing.gui.player_list_workflow import (
    PlayerListUpdater,
    player_list_updater,
)
from gambitpairing.gui.ui_loader import load_ui_into, required_child
from gambitpairing.models.player import Player
from gambitpairing.player_lists.catalog import SOURCE_CFC, SOURCE_FIDE
from gambitpairing.player_lists.search import (
    SEARCH_MODES,
    LiveLookups,
    MergedSearchRow,
    SearchMode,
    SearchRequest,
    SourceResult,
    SourceState,
    SourceStatus,
    format_search_status,
    merge_search_hits,
    search_source,
    selected_sources,
)
from gambitpairing.player_lists.updates import CheckOutcome, CheckStatus

RESULT_COLUMNS: tuple[str, ...] = (
    "Name",
    "Source",
    "FIDE ID",
    "CFC ID",
    "FIDE rating",
    "CFC rating",
)
SEARCH_PLACEHOLDERS: dict[SearchMode, str] = {
    SearchMode.NAME: "Enter player name...",
    SearchMode.FIDE_ID: "Enter FIDE ID, e.g. 1503014...",
    SearchMode.CFC_ID: "Enter CFC ID, e.g. 100123...",
}

TOURNAMENT_COLUMNS: tuple[str, ...] = ("Name", "Rating", "Age", "Gender")

DETAILS_TAB_INDEX = 0


class _SearchWorker(QObject):
    finished = pyqtSignal(object, object, object)  # (worker, result, error)

    def __init__(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs
        self._interrupted = False

    def interrupt(self) -> None:
        """Mark this worker as interrupted."""
        self._interrupted = True

    @QtCore.pyqtSlot()
    def run(self) -> None:
        try:
            # Check if we've been interrupted before starting
            if self._interrupted:
                return

            result = self._fn(*self._args, **self._kwargs)

            # Check if we've been interrupted before emitting
            if not self._interrupted:
                self.finished.emit(self, result, None)
        except Exception as e:
            # Only emit error if we weren't interrupted
            if not self._interrupted:
                self.finished.emit(self, None, e)


class PlayerManagementDialog(QtWidgets.QDialog):
    """Integrated dialog for player management with tabs for editing, FIDE/CFC search, and tournament view."""

    def __init__(
        self,
        parent=None,
        player_data: Optional[Dict[str, Any]] = None,
        tournament=None,
        updater: Optional[PlayerListUpdater] = None,
        live_lookups: Optional[LiveLookups] = None,
    ):
        super().__init__(parent)
        self.player_data = player_data or {}
        self.tournament = tournament
        self.updater = updater or player_list_updater()
        self.live_lookups = live_lookups or LiveLookups()
        # source -> (thread, worker) for the searches still running
        self._search_jobs: Dict[str, tuple[QThread, _SearchWorker]] = {}
        self._source_results: Dict[str, SourceResult] = {}
        self._source_statuses: Dict[str, SourceStatus] = {}
        self._result_rows: list[MergedSearchRow] = []
        self._search_request: Optional[SearchRequest] = None
        self._search_tab_activated = False
        self._selected_player_data = None
        self._player_data_changed = False  # Track if data has been changed/imported
        self._cleaning_up = False  # Track if we're in cleanup mode
        self._editing_player_id = None  # Track which player is being edited (if any)

        self.setWindowTitle("Player Management")
        self.setModal(True)
        self.resize(900, 600)

        load_ui_into(self, "player_management_dialog.ui")
        self._bind_ui_controls()
        self._configure_details_tab()
        self._configure_search_tab()
        self._configure_tournament_tab()

        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        # Install event filter for Enter key handling
        self.installEventFilter(self)

        if self.player_data:
            self._populate_details_form()

        # Trigger: opening the dialog checks lists whose daily check is due.
        self.updater.run_scheduled_checks()

    def _bind_ui_controls(self) -> None:
        """Bind required Designer controls to the dialog's public API fields."""
        self.tab_widget = required_child(self, QtWidgets.QTabWidget, "tab_widget")
        self.buttons = required_child(self, QtWidgets.QDialogButtonBox, "buttons")

        self.details_tab = required_child(self, QtWidgets.QWidget, "details_tab")
        self.search_tab = required_child(self, QtWidgets.QWidget, "search_tab")
        self.tournament_tab = required_child(self, QtWidgets.QWidget, "tournament_tab")

        self.name_edit = required_child(self, QtWidgets.QLineEdit, "name_edit")
        self.rating_spin = required_child(self, QtWidgets.QSpinBox, "rating_spin")
        self.gender_combo = required_child(self, QtWidgets.QComboBox, "gender_combo")
        self.dob_edit = required_child(self, QtWidgets.QDateEdit, "dob_edit")
        self.cfc_id_edit = required_child(self, QtWidgets.QLineEdit, "cfc_id_edit")
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

        self.search_by_combo = required_child(
            self, QtWidgets.QComboBox, "search_by_combo"
        )
        self.search_edit = required_child(self, QtWidgets.QLineEdit, "search_edit")
        self.btn_search = required_child(self, QtWidgets.QPushButton, "btn_search")
        self.btn_clear = required_child(self, QtWidgets.QPushButton, "btn_clear")
        self.source_fide_check = required_child(
            self, QtWidgets.QCheckBox, "source_fide_check"
        )
        self.source_cfc_check = required_child(
            self, QtWidgets.QCheckBox, "source_cfc_check"
        )
        self.btn_player_lists = required_child(
            self, QtWidgets.QPushButton, "btn_player_lists"
        )
        self.results_table = required_child(
            self, QtWidgets.QTableWidget, "results_table"
        )
        self.search_status_label = required_child(
            self, QtWidgets.QLabel, "search_status_label"
        )
        self.list_status_label = required_child(
            self, QtWidgets.QLabel, "list_status_label"
        )
        self.search_progress = required_child(
            self, QtWidgets.QProgressBar, "search_progress"
        )
        self.btn_use_selected = required_child(
            self, QtWidgets.QPushButton, "btn_use_selected"
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
        self.btn_empty_go_search = required_child(
            self, QtWidgets.QPushButton, "btn_empty_go_search"
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

        self.btn_search.setIcon(
            get_native_icon(
                "system-search",
                QtWidgets.QStyle.StandardPixmap.SP_FileDialogContentsView,
            )
        )
        self.btn_clear.setIcon(
            get_native_icon(
                "edit-clear", QtWidgets.QStyle.StandardPixmap.SP_DialogResetButton
            )
        )
        self.btn_use_selected.setIcon(
            get_native_icon(
                "dialog-ok-apply", QtWidgets.QStyle.StandardPixmap.SP_DialogApplyButton
            )
        )
        self.btn_player_lists.setIcon(
            get_native_icon(
                "folder-download", QtWidgets.QStyle.StandardPixmap.SP_DriveNetIcon
            )
        )
        self.btn_empty_go_search.setIcon(
            get_native_icon("go-next", QtWidgets.QStyle.StandardPixmap.SP_ArrowRight)
        )
        self.btn_empty_go_details.setIcon(
            get_native_icon(
                "list-add", QtWidgets.QStyle.StandardPixmap.SP_FileDialogNewFolder
            )
        )
        self.btn_edit_tournament_player.setIcon(
            get_native_icon(
                "document-edit",
                QtWidgets.QStyle.StandardPixmap.SP_FileDialogDetailedView,
            )
        )

    def _configure_details_tab(self) -> None:
        self.name_edit.textChanged.connect(
            lambda: setattr(self, "_player_data_changed", True)
        )
        self._configure_copy_button("btn_copy_name", self.name_edit.text, "Name")
        self._configure_copy_button(
            "btn_copy_rating", lambda: str(self.rating_spin.value()), "Rating"
        )
        self._configure_copy_button("btn_copy_cfc_id", self.cfc_id_edit.text, "CFC ID")
        self._configure_copy_button("btn_copy_phone", self.phone_edit.text, "Phone")
        self._configure_copy_button("btn_copy_email", self.email_edit.text, "Email")
        self._configure_copy_button("btn_copy_club", self.club_edit.text, "Club")
        self._configure_copy_button(
            "btn_copy_federation", self.federation_edit.text, "Federation"
        )
        self._configure_copy_button(
            "btn_copy_fide_id", self.fide_id_edit.text, "FIDE ID"
        )
        self._configure_copy_button(
            "btn_copy_fide_title", self.fide_title_edit.text, "Title"
        )
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
        button = required_child(self, QtWidgets.QToolButton, name)
        button.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        button.setAutoRaise(True)
        button.setAccessibleName(f"Copy {field_name}")
        button.setIcon(
            get_native_icon(
                "edit-copy", QtWidgets.QStyle.StandardPixmap.SP_FileDialogContentsView
            )
        )
        button.clicked.connect(
            lambda: self._copy_to_clipboard(text_getter(), field_name)
        )

    def _configure_search_tab(self) -> None:
        self.search_edit.installEventFilter(self)
        self.btn_search.clicked.connect(self._on_search)
        self.btn_clear.clicked.connect(self._clear_search_results)
        self.search_by_combo.currentIndexChanged.connect(self._on_search_mode_changed)
        self.source_fide_check.toggled.connect(self._on_sources_changed)
        self.source_cfc_check.toggled.connect(self._on_sources_changed)
        self.btn_player_lists.clicked.connect(self.show_player_lists_dialog)
        self._configure_results_table(self.results_table, RESULT_COLUMNS)
        source_header = self.results_table.horizontalHeaderItem(
            RESULT_COLUMNS.index("Source")
        )
        source_header.setToolTip(
            "Players found in both databases share one row, matched on FIDE number"
        )
        self.results_table.itemSelectionChanged.connect(
            self._on_result_selection_changed
        )
        self.results_table.itemDoubleClicked.connect(self._use_selected_result)
        self.results_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.results_table.customContextMenuRequested.connect(
            self._show_results_context_menu
        )
        self.btn_use_selected.clicked.connect(self._use_selected_result)
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

        self.updater.status.connect(self._on_list_status)
        self.updater.list_updated.connect(self._on_list_updated)
        self.updater.busy_changed.connect(self._on_lists_busy_changed)
        self._on_search_mode_changed()
        self._on_sources_changed()

    def _configure_results_table(
        self, table: QtWidgets.QTableWidget, columns: Sequence[str]
    ) -> None:
        table.setColumnCount(len(columns))
        table.verticalHeader().setVisible(False)
        table.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
        )
        header = table.horizontalHeader()
        name_index = next(
            (index for index, title in enumerate(columns) if title == "Name"),
            None,
        )
        for index, title in enumerate(columns):
            table.setHorizontalHeaderItem(index, QtWidgets.QTableWidgetItem(title))
            header.setSectionResizeMode(
                index,
                (
                    QtWidgets.QHeaderView.ResizeMode.Stretch
                    if index == name_index
                    else QtWidgets.QHeaderView.ResizeMode.ResizeToContents
                ),
            )

    def _configure_tournament_tab(self) -> None:
        if not self.tournament:
            self.tab_widget.removeTab(self.tab_widget.indexOf(self.tournament_tab))
            return

        self.tab_widget.setTabText(
            self.tab_widget.indexOf(self.tournament_tab),
            f"Tournament Players ({len(self.tournament.players)})",
        )
        self.btn_empty_go_search.clicked.connect(
            lambda: self.tab_widget.setCurrentWidget(self.search_tab)
        )
        self.btn_empty_go_details.clicked.connect(
            lambda: self.tab_widget.setCurrentIndex(DETAILS_TAB_INDEX)
        )

        if len(self.tournament.players) == 0:
            self.tournament_stack.setCurrentWidget(self.tournament_empty_page)
            return

        self.tournament_stack.setCurrentWidget(self.tournament_table_page)
        self._configure_results_table(self.tournament_table, TOURNAMENT_COLUMNS)
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
        """Copy non-empty text to the clipboard."""
        if not text.strip():
            return

        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(text.strip())

    # --- player lists ----------------------------------------------------------

    def _on_tab_changed(self, index: int) -> None:
        """Trigger: the first activation of the search tab checks due lists."""
        if self.tab_widget.widget(index) is self.search_tab:
            if not self._search_tab_activated:
                self._search_tab_activated = True
                self.updater.run_scheduled_checks()

    def show_player_lists_dialog(self) -> None:
        """Open the Player Lists dialog."""
        PlayerListsDialog(self, updater=self.updater).exec()

    def _on_list_status(self, _key: str, text: str) -> None:
        self.list_status_label.setText(text)
        self.list_status_label.setVisible(True)

    def _on_list_updated(self, outcome: CheckOutcome) -> None:
        if outcome.status is CheckStatus.FAILED:
            self.list_status_label.setText(
                f"Player list update failed: {outcome.message}. "
                "Search uses the copy already kept, or the FIDE and CFC websites."
            )
            self.list_status_label.setVisible(True)

    def _on_lists_busy_changed(self, busy: bool) -> None:
        if not busy and not self.list_status_label.text().startswith(
            "Player list update failed"
        ):
            self.list_status_label.setVisible(False)

    # --- search ----------------------------------------------------------------

    def _search_mode(self) -> SearchMode:
        index = self.search_by_combo.currentIndex()
        return (
            SEARCH_MODES[index] if 0 <= index < len(SEARCH_MODES) else SearchMode.NAME
        )

    def _on_search_mode_changed(self, _index: int = 0) -> None:
        self.search_edit.setPlaceholderText(SEARCH_PLACEHOLDERS[self._search_mode()])

    def _on_sources_changed(self, _checked: bool = False) -> None:
        sources = selected_sources(
            self.source_fide_check.isChecked(), self.source_cfc_check.isChecked()
        )
        self.btn_search.setEnabled(bool(sources) and not self._search_jobs)
        self.btn_search.setToolTip(
            "Search the checked sources (Ctrl+Enter)"
            if sources
            else "Check FIDE, CFC or both to search"
        )

    def _on_search(self) -> None:
        """Search every checked source for the term, as the Search by choice says."""
        if self._search_jobs:
            return

        request = SearchRequest.from_inputs(
            self._search_mode(),
            self.search_edit.text(),
            self.source_fide_check.isChecked(),
            self.source_cfc_check.isChecked(),
        )
        error = request.validation_error()
        if error:
            QtWidgets.QMessageBox.information(self, "Search", error)
            return

        self.results_table.setRowCount(0)
        self._result_rows = []
        self._search_request = request
        self._source_results = {}
        self._source_statuses = {
            source: SourceStatus(source, SourceState.SEARCHING)
            for source in request.sources
        }
        self._update_search_status()
        self._set_search_busy(True)

        for source in request.sources:
            self._start_source_search(
                source,
                lambda source=source: search_source(
                    source,
                    request,
                    self.updater.store,
                    self.live_lookups,
                ),
            )

    def _start_source_search(self, source: str, fn: Callable[[], Any]) -> None:
        worker = _SearchWorker(fn)
        thread = QThread(self)
        worker.moveToThread(thread)
        worker.finished.connect(self._dispatch_search_finished)
        thread.started.connect(worker.run)
        self._search_jobs[source] = (thread, worker)
        thread.start()

    @QtCore.pyqtSlot(object, object, object)
    def _dispatch_search_finished(
        self, worker: _SearchWorker, result: Any, error: Optional[Exception]
    ) -> None:
        """Handle one source's result in the dialog's thread."""
        if self._cleaning_up:
            return
        source = next(
            (
                key
                for key, (_thread, job_worker) in self._search_jobs.items()
                if job_worker is worker
            ),
            None,
        )
        if source is None:
            return
        self._finish_source_job(source)

        if error is not None:
            self._source_statuses[source] = SourceStatus(
                source, SourceState.FAILED, message=str(error) or "search failed"
            )
        else:
            self._source_results[source] = result
            self._source_statuses[source] = result.status()
            self._display_search_results()

        self._update_search_status()
        if not self._search_jobs:
            self._set_search_busy(False)

    def _finish_source_job(self, source: str) -> None:
        thread, worker = self._search_jobs.pop(source)
        try:
            worker.finished.disconnect(self._dispatch_search_finished)
        except (RuntimeError, TypeError):
            pass
        thread.quit()
        if not thread.wait(1500):
            thread.terminate()
            thread.wait(200)
        worker.deleteLater()
        thread.deleteLater()

    def _update_search_status(self) -> None:
        self.search_status_label.setText(
            format_search_status(list(self._source_statuses.values()))
        )

    def _set_search_busy(self, busy: bool) -> None:
        self.search_progress.setVisible(busy)
        if busy:
            self.search_progress.setRange(0, 0)  # Indeterminate
        for control in (self.search_edit, self.search_by_combo):
            control.setEnabled(not busy)
        self._on_sources_changed()
        self.btn_clear.setEnabled(not busy and bool(self._source_statuses))

    def _display_search_results(self) -> None:
        """Merge the results received so far and show them."""
        selected = self._selected_result_row()
        hits = {source: result.hits for source, result in self._source_results.items()}
        request = self._search_request
        self._result_rows = merge_search_hits(
            hits.get(SOURCE_FIDE, ()),
            hits.get(SOURCE_CFC, ()),
            term=request.term if request and request.mode is SearchMode.NAME else "",
        )

        self.results_table.setRowCount(0)
        for row in self._result_rows:
            self._append_result_row(row)
        self.results_table.resizeRowsToContents()

        if selected is not None:
            for index, row in enumerate(self._result_rows):
                if (row.fide_id, row.cfc_id) == (selected.fide_id, selected.cfc_id):
                    self.results_table.selectRow(index)
                    break
        self._on_result_selection_changed()

    def _append_result_row(self, result: MergedSearchRow) -> None:
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        values = (
            result.name,
            result.source_label,
            str(result.fide_id or ""),
            str(result.cfc_id or ""),
            result.fide_rating_text,
            result.cfc_rating_text,
        )
        for column, text in enumerate(values):
            item = QtWidgets.QTableWidgetItem(text)
            self.results_table.setItem(row, column, item)

    def _clear_search_results(self) -> None:
        """Clear the search results table."""
        self._abort_search_jobs()
        self.results_table.setRowCount(0)
        self._result_rows = []
        self._source_results = {}
        self._source_statuses = {}
        self.btn_use_selected.setEnabled(False)
        self.btn_clear.setEnabled(False)
        self.search_status_label.setText("Search for players above to see results here")
        self.search_edit.clear()

    def _selected_result_row(self) -> Optional[MergedSearchRow]:
        selection = self.results_table.selectionModel()
        rows = selection.selectedRows() if selection else []
        if not rows:
            return None
        index = rows[0].row()
        return self._result_rows[index] if index < len(self._result_rows) else None

    def _on_result_selection_changed(self) -> None:
        self.btn_use_selected.setEnabled(self._selected_result_row() is not None)

    def _show_results_context_menu(self, position) -> None:
        """Show context menu for the search results."""
        item = self.results_table.itemAt(position)
        if not item:
            return
        result = self._result_rows[item.row()]

        menu = QtWidgets.QMenu(self)
        use_action = menu.addAction("Use Player")
        use_action.triggered.connect(self._use_selected_result)
        menu.addSeparator()
        for label, value in (
            ("Name", result.name),
            ("FIDE ID", str(result.fide_id or "")),
            ("CFC ID", str(result.cfc_id or "")),
        ):
            if value:
                action = menu.addAction(f"Copy {label}: {value}")
                action.triggered.connect(
                    lambda _checked=False, value=value, label=label: (
                        self._copy_to_clipboard(value, label)
                    )
                )
        menu.exec(self.results_table.mapToGlobal(position))

    def _use_selected_result(self, *_args: Any) -> None:
        """Fill the details form from the selected result."""
        result = self._selected_result_row()
        if result is None:
            return
        try:
            self._apply_player_data(result.player_data(), from_fide=bool(result.fide))
        except Exception as e:
            QtWidgets.QMessageBox.warning(
                self, "Import Error", f"Failed to import player data:\n{str(e)}"
            )

    def _apply_player_data(self, data: Dict[str, Any], from_fide: bool) -> None:
        """Fill the details form from a standardized player dict.

        FIDE rows fill every FIDE field, as the FIDE import always did. IDs are
        only written when the result has one, so a player's existing FIDE or
        CFC ID is never replaced with a blank.
        """
        self.name_edit.setText(data.get("name", ""))
        self.rating_spin.setValue(int(data.get("rating") or 0))

        gender = data.get("gender")
        gender_text = "Male" if gender == "M" else "Female" if gender == "F" else ""
        if gender_text:
            idx = self.gender_combo.findText(gender_text)
            if idx >= 0:
                self.gender_combo.setCurrentIndex(idx)

        dob = data.get("date_of_birth")
        if dob:
            birth_date = QtCore.QDate(dob.year, dob.month, dob.day)
            if birth_date.isValid():
                self.dob_edit.setDate(birth_date)

        self.federation_edit.setText(data.get("federation") or "")

        # Clear fields neither federation provides
        self.phone_edit.setText("")
        self.email_edit.setText("")
        self.club_edit.setText("")

        if data.get("fide_id"):
            self.fide_id_edit.setText(str(data["fide_id"]))
            self.fide_group.setVisible(True)
        if from_fide:
            for edit, key in (
                (self.fide_title_edit, "fide_title"),
                (self.fide_std_edit, "fide_standard"),
                (self.fide_rapid_edit, "fide_rapid"),
                (self.fide_blitz_edit, "fide_blitz"),
            ):
                edit.setText(str(data.get(key) or ""))
        if data.get("cfc_id"):
            self.cfc_id_edit.setText(str(data["cfc_id"]))

        # Store the standardized player data for later use
        self._selected_player_data = data
        self._player_data_changed = True  # Mark that we have new data to save

        self.tab_widget.setCurrentIndex(DETAILS_TAB_INDEX)

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
        cfc_id = self.player_data.get("cfc_id")
        if cfc_id:
            self.cfc_id_edit.setText(str(cfc_id))

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

    def _on_tournament_selection_changed(self):
        """Handle tournament table selection change."""
        selected_rows = self.tournament_table.selectionModel().selectedRows()
        self.btn_edit_tournament_player.setEnabled(len(selected_rows) > 0)

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
            "cfc_id": getattr(player, "cfc_id", None),
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

            # Validate CFC ID if provided
            cfc_id_text = self.cfc_id_edit.text().strip()
            if cfc_id_text and optional_int_from_text(cfc_id_text) in (None, 0):
                if current_tab != 0:
                    self.tab_widget.setCurrentIndex(0)
                QtWidgets.QMessageBox.warning(
                    self, "Validation Error", "CFC ID must be a positive number."
                )
                self.cfc_id_edit.setFocus()
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
        self._abort_search_jobs()
        super().closeEvent(event)

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
            cfc_id=optional_int_from_text(self.cfc_id_edit.text()),
        )

    def get_editing_player_id(self) -> Optional[str]:
        """Get the ID of the player being edited, if any.

        Returns:
            Player ID if editing an existing player, None if adding a new player
        """
        return self._editing_player_id

    def _abort_search_jobs(self) -> None:
        """Cooperatively cancel and clean up the running searches."""
        if not self._search_jobs or self._cleaning_up:
            return

        self._cleaning_up = True
        try:
            for source in list(self._search_jobs):
                thread, worker = self._search_jobs[source]
                # Interrupt worker (prevents emitting results afterwards)
                worker.interrupt()
                try:
                    worker.finished.disconnect()
                except (RuntimeError, TypeError):
                    pass
                # Give the thread a chance to finish gracefully
                thread.quit()
                if not thread.wait(2000):
                    thread.terminate()
                    thread.wait(200)
                worker.deleteLater()
                del self._search_jobs[source]
            self._set_search_busy(False)
        finally:
            self._cleaning_up = False

    def done(self, result: int) -> None:
        """Stop searches and stop listening to the app-wide list updater."""
        self._abort_search_jobs()
        for signal, slot in (
            (self.updater.status, self._on_list_status),
            (self.updater.list_updated, self._on_list_updated),
            (self.updater.busy_changed, self._on_lists_busy_changed),
        ):
            try:
                signal.disconnect(slot)
            except (RuntimeError, TypeError):
                pass
        super().done(result)
