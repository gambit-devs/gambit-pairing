from types import SimpleNamespace
from typing import cast

from gambitpairing.gui.views.tournament.tournament_view_workflow import (
    active_players_for_manual_pairing,
    build_pairing_exception_prompt,
    build_pairing_generation_failure_prompt,
    build_recorded_round_view_update,
    build_reprepare_round_prompt,
    build_round_end_prompt,
    build_round_preparation_messages,
    build_tournament_view_state,
    evaluate_minimum_player_check,
    evaluate_undo_availability,
    format_generated_pairing_history_lines,
    format_manual_pairing_history_lines,
    format_recorded_result_history_lines,
    players_to_revert_for_undo,
    revert_player_round_data,
    resolve_existing_round_pairings,
    round_preparation_mode,
    should_report_empty_pairings_failure,
    undo_confirmation_message,
)
from gambitpairing.models.enums import Colour
from gambitpairing.models import Player


def _players():
    return Player("Ada"), Player("Bert"), Player("Cora")


def _player_id(player):
    return cast(str, getattr(player, "id"))


def _tournament(players, num_rounds=3, pairings=None, byes=None):
    return SimpleNamespace(
        players={_player_id(player): player for player in players},
        num_rounds=num_rounds,
        pairing_system="dutch_swiss",
        rounds_pairings_ids=pairings or [],
        rounds_byes_ids=byes or [],
    )


def _with_pairing_system(tournament, pairing_system):
    tournament.pairing_system = pairing_system
    return tournament


def test_tournament_view_state_without_tournament_shows_placeholder():
    state = build_tournament_view_state(None, current_round_index=0, pairings_row_count=0)

    assert state.tournament_exists is False
    assert state.show_placeholder is True
    assert state.show_header is False
    assert state.show_round_card is False
    assert state.round_control_state == "finished"
    assert state.status_visible is False
    assert state.edit_pairings_visible is False
    assert state.print_pairings_enabled is False


def test_tournament_view_state_before_start_shows_start_controls():
    tournament = _tournament(_players(), num_rounds=3)

    state = build_tournament_view_state(tournament, 0, 0)

    assert state.show_placeholder is False
    assert state.show_header is True
    assert state.show_pre_tournament_start is True
    assert state.show_round_card is False
    assert state.round_control_state == "start"
    assert state.undo_visible is False
    assert state.status_state == "ready"
    assert "Click 'Start Tournament'" in state.status_message


def test_tournament_view_state_waiting_for_results_enables_pairing_actions():
    player_one, player_two, bye_player = _players()
    tournament = _tournament(
        [player_one, player_two, bye_player],
        pairings=[[(_player_id(player_one), _player_id(player_two))]],
        byes=[_player_id(bye_player)],
    )

    state = build_tournament_view_state(tournament, 0, 1)

    assert state.show_pre_tournament_start is False
    assert state.show_round_card is True
    assert state.round_control_state == "record"
    assert state.undo_enabled is False
    assert state.undo_visible is True
    assert state.status_state == "recording"
    assert state.edit_pairings_visible is True
    assert state.edit_pairings_enabled is True
    assert state.print_pairings_enabled is True


def test_tournament_view_state_after_completed_round_prepares_next_round():
    player_one, player_two, _ = _players()
    tournament = _tournament(
        [player_one, player_two],
        num_rounds=3,
        pairings=[[(_player_id(player_one), _player_id(player_two))]],
        byes=[None],
    )

    state = build_tournament_view_state(tournament, 1, 0)

    assert state.round_control_state == "prepare"
    assert state.undo_enabled is True
    assert state.undo_visible is True
    assert state.status_state == "prepare"
    assert state.edit_pairings_visible is False
    assert state.print_pairings_enabled is False


def test_tournament_view_state_after_final_round_is_finished():
    player_one, player_two, _ = _players()
    tournament = _tournament(
        [player_one, player_two],
        num_rounds=1,
        pairings=[[(_player_id(player_one), _player_id(player_two))]],
        byes=[None],
    )

    state = build_tournament_view_state(tournament, 1, 0)

    assert state.round_control_state == "finished"
    assert state.status_state == "finished"
    assert "Tournament complete" in state.status_message
    assert state.edit_pairings_visible is False


def test_round_pairing_resolution_and_active_players_ignore_missing_entries():
    player_one, player_two, inactive_player = _players()
    inactive_player.is_active = False
    tournament = _tournament(
        [player_one, player_two, inactive_player],
        pairings=[
            [
                (_player_id(player_one), _player_id(player_two)),
                ("missing", _player_id(player_two)),
            ]
        ],
        byes=[_player_id(inactive_player)],
    )

    existing = resolve_existing_round_pairings(tournament, 0)

    assert existing.pairings == [(player_one, player_two)]
    assert existing.bye_player is inactive_player
    assert existing.bye_players == [inactive_player]
    assert existing.missing_pairing_ids == [("missing", _player_id(player_two))]
    assert active_players_for_manual_pairing(tournament) == [player_one, player_two]


def test_pairing_history_formatters_preserve_existing_message_shapes():
    player_one, player_two, bye_player = _players()

    generated_lines = format_generated_pairing_history_lines(
        2, [(player_one, player_two)], bye_player
    )
    manual_lines = format_manual_pairing_history_lines(
        2, "Edited", [(player_one, player_two)], [bye_player]
    )

    assert generated_lines == [
        "--- Round 2 Pairings Generated ---",
        f"  {player_one.name} (W) vs {player_two.name} (B)",
        f"  Bye: {bye_player.name}",
        "-" * 20,
    ]
    assert manual_lines == [
        "--- Round 2 Edited Pairings Updated ---",
        f"  Board 1: {player_one.name} (W) vs {player_two.name} (B)",
        f"  Bye: {bye_player.name}",
        "-" * 20,
    ]


def test_minimum_player_check_blocks_pairing_systems_with_too_few_players():
    one_player = [Player("Solo")]

    round_robin = evaluate_minimum_player_check(
        _with_pairing_system(_tournament(one_player, num_rounds=1), "round_robin")
    )
    swiss = evaluate_minimum_player_check(_tournament(one_player, num_rounds=1))
    manual = evaluate_minimum_player_check(
        _with_pairing_system(_tournament(one_player, num_rounds=1), "manual")
    )

    assert round_robin.kind == "blocking"
    assert round_robin.title == "Start Error"
    assert "at least three players" in round_robin.message
    assert swiss.kind == "blocking"
    assert "at least two players" in swiss.message
    assert manual.kind == "blocking"
    assert "Manual pairing" in manual.message


def test_minimum_player_check_returns_confirmation_for_small_swiss_field():
    players = [Player("Ada"), Player("Bert"), Player("Cora")]
    tournament = _tournament(players, num_rounds=3)

    check = evaluate_minimum_player_check(tournament)

    assert check.kind == "confirm"
    assert check.requires_confirmation is True
    assert check.title == "Insufficient Players"
    assert "minimum of 8 players is recommended" in check.message


def test_minimum_player_check_uses_active_players_for_preparation():
    player_one, player_two, inactive_player = _players()
    inactive_player.is_active = False
    tournament = _with_pairing_system(
        _tournament([player_one, player_two, inactive_player], num_rounds=1),
        "round_robin",
    )

    check = evaluate_minimum_player_check(tournament, for_preparation=True)

    assert check.kind == "blocking"
    assert check.title == "Prepare Error"
    assert "three active players" in check.message


def test_minimum_player_check_allows_valid_fields():
    players = [Player("Ada"), Player("Bert"), Player("Cora"), Player("Drew")]
    swiss = _tournament(players, num_rounds=2)
    manual = _with_pairing_system(_tournament(players[:2], num_rounds=1), "manual")

    assert evaluate_minimum_player_check(swiss).can_continue is True
    assert evaluate_minimum_player_check(manual).can_continue is True


def test_round_preparation_prompt_and_message_helpers_preserve_text():
    end_prompt = build_round_end_prompt()
    reprepare_prompt = build_reprepare_round_prompt(1)
    messages = build_round_preparation_messages(2)
    failure_prompt = build_pairing_generation_failure_prompt(2)
    exception_prompt = build_pairing_exception_prompt(2, RuntimeError("boom"))

    assert end_prompt.title == "Tournament End"
    assert "All tournament rounds" in end_prompt.message
    assert reprepare_prompt.title == "Re-Prepare Round?"
    assert "Pairings for Round 2 already exist" in reprepare_prompt.message
    assert messages.started_status == "Generating pairings for Round 2..."
    assert messages.ready_status == "Round 2 pairings ready. Enter results."
    assert messages.error_status == "Error generating pairings for Round 2."
    assert messages.header_title == "Round 2 Pairings & Results"
    assert messages.reprepare_history_line == "--- Re-preparing pairings for Round 2 ---"
    assert failure_prompt.title == "Pairing Error"
    assert "No pairings returned" in failure_prompt.message
    assert exception_prompt.message == "Pairing generation failed for Round 2:\nboom"


def test_round_preparation_mode_and_empty_pairings_failure_decision():
    players = [Player("Ada"), Player("Bert")]
    manual = _with_pairing_system(_tournament(players, num_rounds=1), "manual")
    swiss = _tournament(players, num_rounds=1)

    assert round_preparation_mode(manual) == "manual"
    assert round_preparation_mode(swiss) == "generated"
    assert should_report_empty_pairings_failure([], 2, None) is True
    assert should_report_empty_pairings_failure([], 1, None) is False
    assert should_report_empty_pairings_failure([("pairing",)], 2, None) is False
    assert should_report_empty_pairings_failure([], 2, players[0]) is False


def test_recorded_result_history_lines_include_games_and_active_bye():
    player_one, player_two, bye_player = _players()
    tournament = _tournament(
        [player_one, player_two, bye_player],
        pairings=[[(_player_id(player_one), _player_id(player_two))]],
        byes=[_player_id(bye_player)],
    )

    lines = format_recorded_result_history_lines(
        tournament,
        [(_player_id(player_one), _player_id(player_two), 1.0, 0.0)],
        round_index_recorded=0,
    )

    assert lines == [
        "--- Round 1 Results Recorded ---",
        f"  {player_one.name} (1.0) - {player_two.name} (0.0)",
        f"  Bye point (1.0) awarded to: {bye_player.name}",
        "-" * 20,
    ]


def test_recorded_result_history_lines_handle_inactive_and_missing_byes():
    player_one, player_two, bye_player = _players()
    bye_player.is_active = False
    inactive_bye_tournament = _tournament(
        [player_one, player_two, bye_player],
        pairings=[[(_player_id(player_one), _player_id(player_two))]],
        byes=[_player_id(bye_player)],
    )
    missing_bye_tournament = _tournament(
        [player_one, player_two],
        pairings=[[(_player_id(player_one), _player_id(player_two))]],
        byes=["missing-bye"],
    )

    inactive_lines = format_recorded_result_history_lines(
        inactive_bye_tournament,
        [(_player_id(player_one), _player_id(player_two), 0.5)],
        0,
    )
    missing_lines = format_recorded_result_history_lines(
        missing_bye_tournament,
        [(_player_id(player_one), _player_id(player_two), 0.5)],
        0,
    )

    assert (
        f"  Bye point (0.0) awarded to: {bye_player.name} (Inactive - No Score)"
        in inactive_lines
    )
    assert "  Bye player ID missing-bye not found in player list (error)." in missing_lines


def test_recorded_round_view_update_distinguishes_next_round_from_finished():
    next_round = build_recorded_round_view_update(total_rounds=3, round_index_recorded=0)
    finished = build_recorded_round_view_update(total_rounds=1, round_index_recorded=0)

    assert next_round.next_round_index == 1
    assert next_round.status_message == "Round 1 results recorded. Prepare Round 2."
    assert next_round.header_title == "Round 2 (Pending Preparation)"
    assert next_round.history_lines == []

    assert finished.next_round_index == 1
    assert finished.status_message == "Tournament finished after 1 rounds."
    assert finished.header_title == "Tournament Finished"
    assert finished.history_lines == ["--- Tournament Finished (1 Rounds) ---"]


def test_undo_availability_and_confirmation_text():
    player_one, player_two, _ = _players()
    tournament = _tournament([player_one, player_two])

    unavailable = evaluate_undo_availability(tournament, [], 1)
    available = evaluate_undo_availability(tournament, [("result",)], 1)

    assert unavailable.can_undo is False
    assert unavailable.title == "Undo Error"
    assert "No results from a completed round" in unavailable.message
    assert available.can_undo is True
    assert (
        undo_confirmation_message(2)
        == "Undo results from Round 2 and revert to its pairing stage?"
    )


def test_players_to_revert_for_undo_includes_bye_once():
    player_one, player_two, bye_player = _players()
    tournament = _tournament(
        [player_one, player_two, bye_player],
        byes=[_player_id(bye_player)],
    )

    players = players_to_revert_for_undo(
        tournament,
        [
            (_player_id(player_one), _player_id(player_two), 1.0),
            (_player_id(player_one), "missing", 0.0),
        ],
        round_index_being_undone=0,
    )

    assert players == [player_one, player_two, bye_player]


def test_revert_player_round_data_removes_last_result_and_cache():
    player = Player("Ada")
    player.score = 1.5
    player.results = [1.0, 0.5]
    player.running_scores = [1.0, 1.5]
    player.opponent_ids = ["opponent-1", "opponent-2"]
    player.color_history = [Colour.WHITE, Colour.BLACK]
    player.num_black_games = 1
    player._opponents_played_cache = [Player("Cached")]

    assert revert_player_round_data(player) is True
    assert player.score == 1.0
    assert player.results == [1.0]
    assert player.running_scores == [1.0]
    assert player.opponent_ids == ["opponent-1"]
    assert player.color_history == [Colour.WHITE]
    assert player.num_black_games == 0
    assert player._opponents_played_cache == []


def test_revert_player_round_data_updates_bye_flag_when_last_round_was_bye():
    player = Player("Ada")
    player.score = 1.0
    player.results = [1.0]
    player.running_scores = [1.0]
    player.opponent_ids = [None]
    player.color_history = [None]
    player.has_received_bye = True

    assert revert_player_round_data(player) is True
    assert player.score == 0.0
    assert player.has_received_bye is False
    assert player.opponent_ids == []


def test_revert_player_round_data_noops_without_results():
    player = Player("Ada")

    assert revert_player_round_data(player) is False
