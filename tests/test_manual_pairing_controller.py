from gambitpairing.controllers.pairing.manual_pairing_controller import (
    ManualPairingController,
)
from gambitpairing.models.player import Player


def _players() -> tuple[Player, Player, Player]:
    return Player("Ada", 1800), Player("Bert", 1700), Player("Cora", 1600)


def test_controller_owns_pairing_mutations_and_undo_state():
    ada, bert, cora = _players()
    controller = ManualPairingController([ada, bert, cora])

    assert controller.place_player(ada.id, 0, "white")
    assert controller.place_player(bert.id, 0, "black")
    assert controller.pairings == [(ada, bert)]

    assert controller.swap_colors(0)
    assert controller.pairings == [(bert, ada)]
    assert controller.undo()
    assert controller.pairings == [(ada, bert)]

    assert controller.assign_bye(cora)
    assert controller.bye_players == [cora]
    assert controller.is_player_assigned(cora.id)
    assert not controller.assign_bye(cora)


def test_controller_can_generate_simple_pairings_without_a_tournament_context():
    ada, bert, cora = _players()
    controller = ManualPairingController([ada, bert, cora])

    pairings, bye_player = controller.get_dutch_pairings([ada, bert, cora])

    assert pairings == [(ada, bert)]
    assert bye_player is cora
