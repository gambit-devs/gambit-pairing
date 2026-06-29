import pytest

from gambitpairing.gui.dialogs.manual_pairing_io import (
    build_pairings_export_data,
    parse_pairings_import_data,
)
from gambitpairing.gui.dialogs.manual_pairing_state import (
    build_stats_text,
    build_unresolved_players_message,
    build_validation_projection,
    repeat_pairing_boards,
    unresolved_active_players,
)
from gambitpairing.models.player import Player


def _player(name: str, rating: int = 1000, active: bool = True) -> Player:
    player = Player(name, rating)
    player.is_active = active
    return player


def test_manual_pairing_stats_and_validation_projection():
    ada = _player("Ada")
    ben = _player("Ben")
    cy = _player("Cy")

    stats = build_stats_text([ada, ben, cy], [(ada, ben)], [cy])
    validation = build_validation_projection([ada, ben, cy], [(ada, ben)], [cy])

    assert stats == (
        "Players: 2/3 active paired • 0 active remaining • "
        "0 incomplete boards • Bye: Cy"
    )
    assert validation.text == "✅ All validations passed"
    assert not validation.has_warnings


def test_manual_pairing_validation_warnings_and_repeat_boards():
    ada = _player("Ada")
    ben = _player("Ben")
    cy = _player("Cy")
    previous_matches = {frozenset([ada.id, ben.id])}

    validation = build_validation_projection(
        [ada, ben, cy], [(ada, ben), (cy, None)], [], previous_matches
    )

    assert validation.has_warnings
    assert "1 incomplete boards need completion" in validation.text
    assert "Repeat pairings on boards: 1" in validation.text
    assert repeat_pairing_boards([(ada, ben)], previous_matches) == ["1"]


def test_unresolved_active_players_and_message():
    ada = _player("Ada")
    ben = _player("Ben")
    cy = _player("Cy", active=False)

    unresolved = unresolved_active_players([ada, ben, cy], [(ada, None)], [])
    message = build_unresolved_players_message(unresolved)

    assert unresolved == {ada, ben}
    assert "Ada" in message
    assert "Ben" in message
    assert "withdraw all these players" in message


def test_manual_pairing_export_and_import_round_trip():
    ada = _player("Ada")
    ben = _player("Ben")
    cy = _player("Cy")
    export_data = build_pairings_export_data(2, [(ada, ben)], [cy])

    assert export_data["round_number"] == 2
    assert export_data["pairings"][0]["white"]["id"] == ada.id
    assert export_data["bye_players"][0]["id"] == cy.id

    pairings, byes = parse_pairings_import_data(
        export_data, {player.id: player for player in [ada, ben, cy]}
    )

    assert pairings == [(ada, ben)]
    assert byes == [cy]


def test_manual_pairing_import_rejects_invalid_shape():
    with pytest.raises(ValueError, match="Invalid pairings file format"):
        parse_pairings_import_data({}, {})
