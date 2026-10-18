"""Shared test setup.

Every test runs against its own empty data directory with no player lists
selected, so nothing in the suite checks or downloads lists, and any attempt
to open a real HTTP client for player lists fails loudly.
"""

import json

import pytest

from gambitpairing.player_lists import store as player_list_store
from gambitpairing.player_lists import updates as player_list_updates


def _no_network_client():
    raise AssertionError("Tests must not open a network client for player lists")


@pytest.fixture(autouse=True)
def isolated_player_lists(tmp_path_factory, monkeypatch):
    # Not tmp_path: some tests assert that their tmp_path stays empty.
    data_dir = tmp_path_factory.mktemp("gambit-data")
    lists_dir = data_dir / player_list_store.PLAYER_LISTS_DIR_NAME
    lists_dir.mkdir()
    (lists_dir / player_list_store.SELECTION_FILE_NAME).write_text(
        json.dumps({"selected": []}), encoding="utf-8"
    )
    monkeypatch.setenv(player_list_store.DATA_DIR_ENV, str(data_dir))
    monkeypatch.setattr(player_list_updates, "create_http_client", _no_network_client)
    # The app-wide updater remembers its data directory; start each test fresh.
    monkeypatch.setattr("gambitpairing.gui.player_list_workflow._UPDATER", None)
    yield data_dir
