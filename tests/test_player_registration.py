import os
from datetime import date
from typing import cast

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6 import QtWidgets

from gambitpairing.controllers.tournament.session import TournamentSession as Tournament
from gambitpairing.gui.views.players.players_view import PlayersView
from gambitpairing.models.player import Player, create_player
from gambitpairing.player_lists.registration import (
    CFC_ID_TAKEN,
    FIDE_ID_TAKEN,
    NAME_TAKEN,
    RegistrationResult,
    add_registrations,
    registration_data,
)


class _Parent(QtWidgets.QWidget):
    def prompt_new_tournament(self) -> None:
        pass

    def load_tournament(self) -> None:
        pass


_APP: QtWidgets.QApplication | None = None


def _app() -> QtWidgets.QApplication:
    # Keep a reference: Qt must not lose the application to garbage collection.
    global _APP
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    _APP = cast(QtWidgets.QApplication, app)
    return _APP


def test_registration_data_uses_the_add_player_form_shapes():
    data = registration_data(
        {
            "name": " Doe, Jane ",
            "rating": "1850",
            "gender": "F",
            "date_of_birth": date(1990, 4, 2),
            "federation": "USA",
            "fide_id": "1503014",
            "fide_title": "WFM",
            "fide_standard": 2000,
            "cfc_id": 0,
        }
    )

    assert data == {
        "name": "Doe, Jane",
        "rating": 1850,
        "gender": "F",
        "date_of_birth": "1990-04-02",
        "federation": "USA",
        "phone": "",
        "email": "",
        "club": "",
        "fide_id": 1503014,
        "fide_title": "WFM",
        "fide_standard": 2000,
    }


def test_add_registrations_skips_players_already_in_the_tournament():
    existing = create_player(name="Doe, Jane", rating=1800, fide_id=1503014)
    tournament = Tournament("City Open", [existing], 5)

    result = add_registrations(
        tournament,
        [
            {"name": "Smith, Ann", "rating": 1500, "cfc_id": 100123},
            {"name": "Doe, Jane", "rating": 1850},
            {"name": "Roe, Tim", "rating": 1400, "fide_id": 1503014},
            # Same CFC ID as Ann, added earlier in this batch.
            {"name": "Lee, Sam", "rating": 1300, "cfc_id": 100123},
            {"name": "Kim, Lou", "rating": 1200},
            {"name": "   ", "rating": 1000},
        ],
    )

    assert [player.name for player in result.added] == ["Smith, Ann", "Kim, Lou"]
    assert result.skipped == (
        ("Doe, Jane", NAME_TAKEN),
        ("Roe, Tim", FIDE_ID_TAKEN),
        ("Lee, Sam", CFC_ID_TAKEN),
        ("(no name)", "no name"),
    )
    assert len(tournament.players) == 3


def test_registration_result_describes_what_happened():
    player = Player("Ada", 1800)

    assert RegistrationResult((player,), ()).describe() == "Added 1 player."
    assert (
        RegistrationResult((player, player), (("Ada", NAME_TAKEN),)).describe()
        == "Added 2 players; skipped 1 already in the tournament or invalid."
    )


def test_players_view_adds_search_results_in_one_go():
    _app()
    parent = _Parent()
    view = PlayersView(parent)
    tournament = Tournament("City Open", [Player("Ada", 1800)], 5)
    view.set_tournament(tournament)

    result = view.add_registrations_from_search(
        [
            {"name": "Grace", "rating": 1900},
            {"name": "Ada", "rating": 1800},
            {"name": "Linus", "rating": 1700},
        ]
    )

    assert [player.name for player in result.added] == ["Grace", "Linus"]
    assert len(tournament.players) == 3
    assert view.table_players.rowCount() == 3

    view.close()
    parent.close()
