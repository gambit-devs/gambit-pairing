from gambitpairing.gui.main_window_state import build_main_window_ui_state
from gambitpairing.models.player import Player
from gambitpairing.models.tournament import Tournament


def _tournament(player_count: int = 0, rounds: int = 3) -> Tournament:
    players = [Player(f"Player {index}", 1200 + index) for index in range(player_count)]
    return Tournament("City Open", players, rounds)


def test_main_window_ui_state_without_tournament_preserves_initial_status():
    state = build_main_window_ui_state(
        tournament=None,
        current_round_index=0,
        last_recorded_results_data=[],
        dirty=False,
        current_filepath=None,
        app_name="Gambit Pairing",
    )

    assert not state.tournament_exists
    assert not state.can_start
    assert not state.can_save
    assert state.can_add_player
    assert state.window_title == "Gambit Pairing"
    assert state.status_message == "Ready - Create New or Load Tournament."
    assert state.toolbar_tournament_label == "No Tournament Loaded"


def test_main_window_ui_state_for_unstarted_tournament_matches_current_actions():
    tournament = _tournament(player_count=2)
    state = build_main_window_ui_state(
        tournament=tournament,
        current_round_index=0,
        last_recorded_results_data=[],
        dirty=True,
        current_filepath="city-open.json",
        app_name="Gambit Pairing",
    )

    assert state.tournament_exists
    assert state.can_start
    assert state.can_save
    assert state.can_import_players
    assert state.can_export_players
    assert state.can_open_settings
    assert not state.can_record
    assert state.window_title == "City Open* - city-open.json - Gambit Pairing"
    assert state.toolbar_tournament_label == "City Open *"
    assert (
        state.status_message
        == "Tournament 'City Open': Add players, then Start. 2 players registered."
    )


def test_main_window_ui_state_for_record_and_prepare_phases():
    tournament = _tournament(player_count=2)
    players = tournament.get_player_list()
    tournament.rounds_pairings_ids = [[(players[0].id, players[1].id)]]

    record_state = build_main_window_ui_state(
        tournament=tournament,
        current_round_index=0,
        last_recorded_results_data=[],
        dirty=False,
        current_filepath=None,
        app_name="Gambit Pairing",
    )

    assert record_state.tournament_started
    assert record_state.can_record
    assert not record_state.can_prepare
    assert not record_state.can_import_players
    assert record_state.status_message == (
        "Round 1 pairings ready for 'City Open'. Please enter results."
    )

    prepare_state = build_main_window_ui_state(
        tournament=tournament,
        current_round_index=1,
        last_recorded_results_data=[("result",)],
        dirty=False,
        current_filepath=None,
        app_name="Gambit Pairing",
    )

    assert prepare_state.can_prepare
    assert prepare_state.can_undo
    assert not prepare_state.can_record
    assert prepare_state.status_message == (
        "Round 1 results recorded for 'City Open'. Prepare Round 2."
    )
