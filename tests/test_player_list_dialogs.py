"""Offscreen tests for the merged search tab, the Player Lists dialog and triggers."""

import os
from datetime import timedelta
from pathlib import Path
import time
from typing import cast
import zipfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import httpx
from PyQt6 import QtWidgets
from PyQt6.QtCore import QItemSelectionModel, Qt
import pytest

from gambitpairing.gui.dialogs.player_lists_dialog import PlayerListsDialog
from gambitpairing.gui.dialogs.player_management_dialog import PlayerManagementDialog
from gambitpairing.gui.player_list_workflow import PlayerListUpdater
from gambitpairing.player_lists.catalog import PLAYER_LISTS, get_player_list
from gambitpairing.controllers.tournament.session import TournamentSession as Tournament
from gambitpairing.player_lists.registration import add_registrations
from gambitpairing.player_lists.search import LiveLookups, SearchMode
from gambitpairing.player_lists.store import (
    ListMetadata,
    ListState,
    PlayerListStore,
    utc_now,
)

FIXTURES = Path(__file__).parent / "fixtures" / "player_lists"
FIDE = get_player_list("fide_combined")
CFC = get_player_list("cfc_members")


_APP: QtWidgets.QApplication | None = None


def _app() -> QtWidgets.QApplication:
    global _APP
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    _APP = cast(QtWidgets.QApplication, app)
    return _APP


def _wait_until(condition, timeout=10.0):
    app = _app()
    deadline = time.monotonic() + timeout
    while not condition():
        if time.monotonic() > deadline:
            raise AssertionError("timed out waiting for background work")
        app.processEvents()
        time.sleep(0.01)
    app.processEvents()


def _fide_zip_bytes(tmp_path: Path) -> bytes:
    path = tmp_path / "fide.zip"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "players_list_xml_foa.xml",
            (FIXTURES / "fide_players_list_sample.xml").read_bytes(),
        )
    return path.read_bytes()


class LocalServer:
    """Serve the fixture lists through httpx.MockTransport (no network)."""

    def __init__(self, tmp_path: Path):
        self.bodies = {
            FIDE.url: _fide_zip_bytes(tmp_path),
            CFC.url: (FIXTURES / "tdlist_sample.txt").read_bytes(),
        }
        self.requests: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        body = self.bodies[str(request.url)]
        headers = {"etag": '"v1"', "content-length": str(len(body))}
        if request.headers.get("if-none-match") == '"v1"':
            return httpx.Response(304, headers={"etag": '"v1"'})
        if request.method == "HEAD":
            return httpx.Response(200, headers=headers)
        return httpx.Response(200, headers=headers, content=body)

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self.handler))


class NoLive:
    """Live lookups that fail the test if called."""

    def lookups(self) -> LiveLookups:
        def fail(*_args):
            raise AssertionError("live lookup used although a list is downloaded")

        return LiveLookups(fail)


@pytest.fixture
def server(tmp_path):
    return LocalServer(tmp_path)


def _updater(tmp_path: Path, server: LocalServer, selected) -> PlayerListUpdater:
    store = PlayerListStore(tmp_path / "data", min_rows=1)
    store.save_selection(selected)
    return PlayerListUpdater(store=store, client_factory=server.client)


def _download_all(updater: PlayerListUpdater) -> None:
    updater.update_now([FIDE.key, CFC.key])
    _wait_until(lambda: not updater.is_busy)


def _search(dialog: PlayerManagementDialog, mode: SearchMode, text: str) -> None:
    dialog.search_by_combo.setCurrentIndex(list(SearchMode).index(mode))
    dialog.search_edit.setText(text)
    dialog._on_search()
    _wait_until(lambda: not dialog._search_jobs)


def test_merged_search_tab_searches_local_lists_and_fills_both_ids(tmp_path, server):
    _app()
    updater = _updater(tmp_path, server, [FIDE.key, CFC.key])
    _download_all(updater)
    assert updater.store.state(FIDE) is ListState.DOWNLOADED
    assert updater.store.state(CFC) is ListState.DOWNLOADED

    dialog = PlayerManagementDialog(updater=updater, live_lookups=NoLive().lookups())
    _search(dialog, SearchMode.NAME, "Tremblay")

    table = dialog.results_table
    assert "matched on FIDE number" in table.horizontalHeaderItem(1).toolTip()
    assert "exact number" in dialog.search_by_combo.toolTip()
    assert [table.horizontalHeaderItem(i).text() for i in range(6)] == [
        "Name",
        "Source",
        "FIDE ID",
        "CFC ID",
        "FIDE rating",
        "CFC rating",
    ]
    assert table.rowCount() == 2
    assert [table.item(0, col).text() for col in range(6)] == [
        "Tremblay, Marc",
        "FIDE + CFC",
        "2600001",
        "171117",
        "1950",
        "1991",
    ]
    assert table.item(1, 1).text() == "FIDE"
    status = dialog.search_status_label.text()
    assert status == "FIDE: 2 results (local list) · CFC: 1 result (local list)"

    table.selectRow(0)
    assert dialog.btn_use_selected.isEnabled()
    dialog.btn_use_selected.click()
    assert dialog.tab_widget.currentIndex() == 0
    assert dialog.fide_id_edit.text() == "2600001"
    assert dialog.cfc_id_edit.text() == "171117"
    assert dialog.fide_std_edit.text() == "1950"
    data = dialog.get_player_data()
    assert data["fide_id"] == 2600001 and data["cfc_id"] == 171117
    dialog.close()


def test_using_a_single_source_row_never_blanks_existing_ids(tmp_path, server):
    _app()
    updater = _updater(tmp_path, server, [FIDE.key, CFC.key])
    _download_all(updater)
    dialog = PlayerManagementDialog(
        player_data={"name": "Ethan Ngo", "rating": 200, "fide_id": 2600009},
        updater=updater,
        live_lookups=NoLive().lookups(),
    )
    dialog.source_fide_check.setChecked(False)
    _search(dialog, SearchMode.CFC_ID, "165306")

    assert dialog.search_status_label.text() == "CFC: 1 result (local list)"
    dialog.results_table.selectRow(0)
    dialog._use_selected_result()

    assert dialog.cfc_id_edit.text() == "165306"
    assert dialog.fide_id_edit.text() == "2600009"  # kept, CFC row had none
    assert dialog.get_player_data()["fide_id"] == 2600009

    dialog.source_fide_check.setChecked(True)
    dialog.source_cfc_check.setChecked(False)
    _search(dialog, SearchMode.FIDE_ID, "2600002")
    dialog.results_table.selectRow(0)
    dialog._use_selected_result()
    assert dialog.fide_id_edit.text() == "2600002"
    assert dialog.cfc_id_edit.text() == "165306"  # kept, FIDE row had none
    dialog.close()


def test_source_checkboxes_gate_the_search_button(tmp_path, server):
    _app()
    dialog = PlayerManagementDialog(updater=_updater(tmp_path, server, []))
    assert dialog.btn_search.isEnabled()
    dialog.source_fide_check.setChecked(False)
    assert dialog.btn_search.isEnabled()
    dialog.source_cfc_check.setChecked(False)
    assert not dialog.btn_search.isEnabled()
    dialog.source_cfc_check.setChecked(True)
    assert dialog.btn_search.isEnabled()
    dialog.search_by_combo.setCurrentIndex(2)
    assert "CFC ID" in dialog.search_edit.placeholderText()
    dialog.close()


def test_search_without_lists_reports_each_source_as_unavailable(tmp_path, server):
    _app()
    dialog = PlayerManagementDialog(
        updater=_updater(tmp_path, server, []), live_lookups=NoLive().lookups()
    )
    _search(dialog, SearchMode.NAME, "Lovelace")

    assert dialog.results_table.rowCount() == 0
    assert dialog.search_status_label.text().count("Player lists") == 2
    assert server.requests == []
    dialog.close()


def test_player_lists_dialog_shows_lists_states_and_updates_now(tmp_path, server):
    _app()
    store = PlayerListStore(tmp_path / "data", min_rows=1)  # no selection saved
    updater = PlayerListUpdater(store=store, client_factory=server.client)
    dialog = PlayerListsDialog(updater=updater)
    table = dialog.lists_table

    assert table.rowCount() == len(PLAYER_LISTS) == 5
    names = [table.item(row, 0).text() for row in range(5)]
    assert names == [
        "FIDE combined",
        "FIDE standard",
        "FIDE rapid",
        "FIDE blitz",
        "CFC member list",
    ]
    assert [table.item(row, 1).text() for row in range(5)] == ["FIDE"] * 4 + ["CFC"]
    assert dialog.selected_keys() == ["fide_combined"]
    assert all(table.item(row, 2).text() == "Not downloaded" for row in range(5))
    assert "FIDE" in dialog.attribution_label.text()
    assert "Chess Federation of Canada" in dialog.attribution_label.text()

    table.selectRow(4)
    assert "names, cities and CFC IDs" in dialog.details_label.text()
    assert dialog.btn_update_now.isEnabled()
    dialog.btn_update_now.click()
    _wait_until(lambda: not updater.is_busy)

    assert table.item(4, 2).text().startswith("Downloaded ")
    assert "9 players" in table.item(4, 2).text()
    assert "6 rows skipped" in table.item(4, 2).toolTip()
    assert "CFC member list" in dialog.progress_label.text()

    table.item(4, 0).setCheckState(Qt.CheckState.Checked)
    dialog.accept()
    assert store.selected_keys() == ("fide_combined", "cfc_members")
    # OK downloads the newly selected FIDE list; the CFC list was already kept.
    _wait_until(lambda: not updater.is_busy)
    assert store.has_data_file(FIDE)
    assert [request.method for request in server.requests] == ["GET", "GET"]


def test_scheduled_checks_respect_selection_and_daily_throttle(tmp_path, server):
    _app()
    updater = _updater(tmp_path, server, [])
    assert updater.run_scheduled_checks() == []

    updater.store.save_selection([CFC.key])
    updater.store.write_metadata(
        CFC, ListMetadata(checked_at=(utc_now() - timedelta(hours=1)).isoformat())
    )
    assert updater.run_scheduled_checks() == []
    assert server.requests == []

    # "Update now" ignores the interval.
    assert updater.update_now([CFC.key]) == [CFC.key]
    _wait_until(lambda: not updater.is_busy)
    assert updater.store.is_downloaded(CFC)
    assert updater.run_scheduled_checks() == []


def test_dialog_triggers_checks_on_open_and_first_search_tab_activation(
    tmp_path, server
):
    _app()
    updater = _updater(tmp_path, server, [CFC.key])
    calls = []
    original = updater.run_scheduled_checks

    def recording():
        calls.append("check")
        return original()

    updater.run_scheduled_checks = recording  # type: ignore[method-assign]
    dialog = PlayerManagementDialog(updater=updater)
    assert calls == ["check"]
    _wait_until(lambda: not updater.is_busy)
    assert updater.store.is_downloaded(CFC)

    dialog.tab_widget.setCurrentWidget(dialog.search_tab)
    dialog.tab_widget.setCurrentIndex(0)
    dialog.tab_widget.setCurrentWidget(dialog.search_tab)
    assert calls == ["check", "check"]
    # The second trigger found the list checked moments ago: no new request.
    assert [request.method for request in server.requests] == ["GET"]
    dialog.close()


def test_selected_results_are_added_together_and_marked(tmp_path, server):
    _app()
    updater = _updater(tmp_path, server, [FIDE.key, CFC.key])
    _download_all(updater)
    tournament = Tournament("City Open", [], 5)
    batches = []

    def add_players(results):
        batches.append(len(results))
        return add_registrations(tournament, results)

    dialog = PlayerManagementDialog(
        updater=updater,
        live_lookups=NoLive().lookups(),
        tournament=tournament,
        on_add_players=add_players,
    )
    _search(dialog, SearchMode.NAME, "Tremblay")
    table = dialog.results_table
    assert table.rowCount() == 2

    table.selectRow(0)
    selection = table.selectionModel()
    selection.select(
        table.model().index(1, 0),
        QItemSelectionModel.SelectionFlag.Select
        | QItemSelectionModel.SelectionFlag.Rows,
    )
    assert dialog.btn_add_selected.isEnabled()
    dialog.btn_add_selected.click()

    assert batches == [2]
    assert sorted(player.name for player in tournament.players.values()) == [
        "Tremblay, Marc",
        "Tremblay, Sophie",
    ]
    assert dialog.search_status_label.text() == "Added 2 of 2 selected."
    assert table.item(0, 0).text() == "Tremblay, Marc (in tournament)"
    assert table.item(1, 0).text() == "Tremblay, Sophie (in tournament)"

    dialog.btn_add_selected.click()
    assert batches == [2]
    assert dialog.search_status_label.text() == (
        "Added 0 of 2 selected. The others are already in the tournament or invalid."
    )
    dialog.close()
