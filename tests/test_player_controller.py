from gambitpairing.controllers.player import get_player_import_availability
from gambitpairing.models.player import Player
from gambitpairing.models.tournament import Tournament


def test_api_player_import_requires_a_tournament():
    availability = get_player_import_availability(None)

    assert not availability.allowed
    assert availability.title == "No Tournament"


def test_api_player_import_is_blocked_after_pairings_start():
    tournament = Tournament("City Open", [Player("Ada", 1800)], 5)
    tournament.rounds_pairings_ids = [[("white-id", "black-id")]]

    availability = get_player_import_availability(tournament)

    assert not availability.allowed
    assert availability.title == "Tournament Active"


def test_api_player_import_is_available_before_pairings_start():
    tournament = Tournament("City Open", [Player("Ada", 1800)], 5)

    availability = get_player_import_availability(tournament)

    assert availability.allowed
    assert availability.title == ""
    assert availability.message == ""
