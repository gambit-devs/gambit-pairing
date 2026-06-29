"""Workflow helpers for the tournament tab.

The Qt widget owns rendering and signals; this module owns deterministic
view-state decisions and small tournament-data projections used by that view.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Optional, Sequence

from gambitpairing.constants import BYE_SCORE, WIN_SCORE
from gambitpairing.models import Player
from gambitpairing.models.tournament import TournamentPhase, TournamentState

RoundControlState = Literal["start", "prepare", "record", "finished"]
MinimumPlayerCheckKind = Literal["ok", "blocking", "confirm"]


@dataclass(frozen=True)
class TournamentViewState:
    """Computed visibility, action, and status state for TournamentView."""

    tournament_exists: bool
    show_placeholder: bool
    show_header: bool
    show_pre_tournament_start: bool
    show_round_card: bool
    round_control_state: RoundControlState
    undo_enabled: bool
    undo_visible: bool
    status_message: str
    status_state: str
    status_visible: bool
    edit_pairings_visible: bool
    edit_pairings_enabled: bool
    print_pairings_enabled: bool


@dataclass(frozen=True)
class ExistingRoundPairings:
    """Player objects resolved from stored round pairing IDs."""

    pairings: list[tuple[Player, Player]]
    bye_player: Optional[Player]
    missing_pairing_ids: list[tuple[Any, Any]]

    @property
    def bye_players(self) -> list[Player]:
        return [self.bye_player] if self.bye_player else []


@dataclass(frozen=True)
class MinimumPlayerCheck:
    """Result of checking whether a tournament workflow can proceed."""

    kind: MinimumPlayerCheckKind
    title: str = ""
    message: str = ""

    @property
    def can_continue(self) -> bool:
        return self.kind == "ok"

    @property
    def requires_confirmation(self) -> bool:
        return self.kind == "confirm"


@dataclass(frozen=True)
class RecordedRoundViewUpdate:
    """View updates needed after results are successfully recorded."""

    next_round_index: int
    status_message: str
    header_title: str
    history_lines: list[str]


@dataclass(frozen=True)
class UndoAvailability:
    """Whether the current view state can undo the last recorded results."""

    can_undo: bool
    title: str = ""
    message: str = ""


def build_tournament_view_state(
    tournament: Any, current_round_index: int, pairings_row_count: int
) -> TournamentViewState:
    """Compute the TournamentView state without touching Qt widgets."""

    state = TournamentState.compute(tournament, current_round_index)
    if not state.tournament_exists:
        return TournamentViewState(
            tournament_exists=False,
            show_placeholder=True,
            show_header=False,
            show_pre_tournament_start=False,
            show_round_card=False,
            round_control_state="finished",
            undo_enabled=False,
            undo_visible=False,
            status_message="",
            status_state="default",
            status_visible=False,
            edit_pairings_visible=False,
            edit_pairings_enabled=False,
            print_pairings_enabled=False,
        )

    status_message = state.get_status_message(pairings_row_count)
    return TournamentViewState(
        tournament_exists=True,
        show_placeholder=False,
        show_header=True,
        show_pre_tournament_start=state.phase == TournamentPhase.NOT_STARTED,
        show_round_card=state.phase != TournamentPhase.NOT_STARTED,
        round_control_state=_round_control_state(state.phase),
        undo_enabled=state.can_undo,
        undo_visible=state.tournament_started,
        status_message=status_message,
        status_state=state.status_state if status_message else "default",
        status_visible=bool(status_message),
        edit_pairings_visible=state.has_pairings,
        edit_pairings_enabled=state.can_record,
        print_pairings_enabled=pairings_row_count > 0,
    )


def resolve_existing_round_pairings(
    tournament: Any, round_index: int
) -> ExistingRoundPairings:
    """Resolve stored pairing IDs for a round into player objects."""

    if round_index >= len(tournament.rounds_pairings_ids):
        return ExistingRoundPairings(
            pairings=[], bye_player=None, missing_pairing_ids=[]
        )

    pairings: list[tuple[Player, Player]] = []
    missing_pairing_ids: list[tuple[Any, Any]] = []
    for white_id, black_id in tournament.rounds_pairings_ids[round_index]:
        white = tournament.players.get(white_id)
        black = tournament.players.get(black_id)
        if white and black:
            pairings.append((white, black))
        else:
            missing_pairing_ids.append((white_id, black_id))

    bye_id = (
        tournament.rounds_byes_ids[round_index]
        if round_index < len(tournament.rounds_byes_ids)
        else None
    )
    bye_player = tournament.players.get(bye_id) if bye_id else None
    return ExistingRoundPairings(
        pairings=pairings,
        bye_player=bye_player,
        missing_pairing_ids=missing_pairing_ids,
    )


def active_players_for_manual_pairing(tournament: Any) -> list[Player]:
    """Return active players in the order held by the tournament."""

    return [player for player in tournament.players.values() if player.is_active]


def evaluate_minimum_player_check(
    tournament: Any, for_preparation: bool = False
) -> MinimumPlayerCheck:
    """Evaluate player-count workflow rules without showing Qt prompts."""

    pairing_system = getattr(tournament, "pairing_system", "dutch_swiss")
    if for_preparation:
        players = [
            player
            for player in tournament.players.values()
            if getattr(player, "is_active", True)
        ]
    else:
        players = list(tournament.players.values())

    num_players = len(players)
    min_players = 2**tournament.num_rounds
    player_type = "active " if for_preparation else ""
    title = "Start Error" if not for_preparation else "Prepare Error"

    if pairing_system == "round_robin" and num_players < 3:
        return MinimumPlayerCheck(
            kind="blocking",
            title=title,
            message=(
                f"Round Robin tournaments require at least three "
                f"{player_type}players."
            ),
        )

    if pairing_system == "dutch_swiss":
        if num_players < 2:
            return MinimumPlayerCheck(
                kind="blocking",
                title=title,
                message=(
                    f"FIDE Dutch Swiss tournaments require at least two "
                    f"{player_type}players."
                ),
            )
        if num_players < min_players:
            return MinimumPlayerCheck(
                kind="confirm",
                title="Insufficient Players",
                message=(
                    f"For a {tournament.num_rounds}-round FIDE Dutch Swiss "
                    f"tournament, a minimum of {min_players} players is "
                    "recommended. The tournament may not work properly. Do you "
                    "want to continue anyway?"
                ),
            )

    if pairing_system == "manual" and num_players < 2:
        return MinimumPlayerCheck(
            kind="blocking",
            title=title,
            message=(
                f"Manual pairing tournaments require at least two "
                f"{player_type}players."
            ),
        )

    return MinimumPlayerCheck(kind="ok")


def format_generated_pairing_history_lines(
    display_round_number: int, pairings: Sequence[Any], bye_player: Optional[Player]
) -> list[str]:
    """Build history log lines for generated pairings."""

    lines = [f"--- Round {display_round_number} Pairings Generated ---"]
    for pair in pairings:
        if len(pair) == 3:
            white, black, color = pair
            lines.append(
                f"  {white.name} ({color}) vs {black.name} ({'B' if color == 'W' else 'W'})"
            )
        else:
            white, black = pair
            lines.append(f"  {white.name} (W) vs {black.name} (B)")
    if bye_player:
        lines.append(f"  Bye: {bye_player.name}")
    lines.append("-" * 20)
    return lines


def format_manual_pairing_history_lines(
    display_round_number: int,
    pairing_type: str,
    pairings: Sequence[tuple[Player, Player]],
    bye_players: Sequence[Player],
) -> list[str]:
    """Build history log lines for manually edited pairings."""

    lines = [f"--- Round {display_round_number} {pairing_type} Pairings Updated ---"]
    for board_number, (white, black) in enumerate(pairings, 1):
        lines.append(f"  Board {board_number}: {white.name} (W) vs {black.name} (B)")
    if len(bye_players) == 1:
        lines.append(f"  Bye: {bye_players[0].name}")
    elif len(bye_players) > 1:
        bye_names = ", ".join(player.name for player in bye_players)
        lines.append(f"  Byes ({len(bye_players)}): {bye_names}")
    lines.append("-" * 20)
    return lines


def format_recorded_result_history_lines(
    tournament: Any, results_data: Sequence[Sequence[Any]], round_index_recorded: int
) -> list[str]:
    """Build history log lines for recorded round results."""

    lines = [f"--- Round {round_index_recorded + 1} Results Recorded ---"]
    for result_entry in results_data:
        white_id, black_id, score_white = result_entry[:3]
        score_black = (
            result_entry[3] if len(result_entry) > 3 else WIN_SCORE - score_white
        )
        white = tournament.players.get(white_id)
        black = tournament.players.get(black_id)
        lines.append(
            f"  {white.name if white else white_id} ({score_white:.1f}) - "
            f"{black.name if black else black_id} ({score_black:.1f})"
        )

    if round_index_recorded < len(tournament.rounds_byes_ids):
        bye_id = tournament.rounds_byes_ids[round_index_recorded]
        if bye_id:
            bye_player = tournament.players.get(bye_id)
            if bye_player:
                status = " (Inactive - No Score)" if not bye_player.is_active else ""
                bye_score_awarded = BYE_SCORE if bye_player.is_active else 0.0
                lines.append(
                    f"  Bye point ({bye_score_awarded:.1f}) awarded to: "
                    f"{bye_player.name}{status}"
                )
            else:
                lines.append(
                    f"  Bye player ID {bye_id} not found in player list (error)."
                )
    lines.append("-" * 20)
    return lines


def build_recorded_round_view_update(
    total_rounds: int, round_index_recorded: int
) -> RecordedRoundViewUpdate:
    """Compute view text/state after a successful result recording."""

    display_round_number = round_index_recorded + 1
    next_round_index = round_index_recorded + 1
    if next_round_index >= total_rounds:
        return RecordedRoundViewUpdate(
            next_round_index=next_round_index,
            status_message=f"Tournament finished after {total_rounds} rounds.",
            header_title="Tournament Finished",
            history_lines=[f"--- Tournament Finished ({total_rounds} Rounds) ---"],
        )

    return RecordedRoundViewUpdate(
        next_round_index=next_round_index,
        status_message=(
            f"Round {display_round_number} results recorded. "
            f"Prepare Round {next_round_index + 1}."
        ),
        header_title=f"Round {next_round_index + 1} (Pending Preparation)",
        history_lines=[],
    )


def evaluate_undo_availability(
    tournament: Any, last_recorded_results_data: Sequence[Any], current_round_index: int
) -> UndoAvailability:
    """Check whether undo can proceed from the current view state."""

    if not tournament or not last_recorded_results_data or current_round_index == 0:
        return UndoAvailability(
            can_undo=False,
            title="Undo Error",
            message="No results from a completed round are available to undo.",
        )
    return UndoAvailability(can_undo=True)


def undo_confirmation_message(current_round_index: int) -> str:
    """Build the confirmation prompt for undoing the displayed completed round."""

    return (
        f"Undo results from Round {current_round_index} and revert to its "
        "pairing stage?"
    )


def players_to_revert_for_undo(
    tournament: Any, results_data: Sequence[Sequence[Any]], round_index_being_undone: int
) -> list[Player]:
    """Resolve players whose last-round data should be reverted for undo."""

    players: list[Player] = []
    seen_ids: set[Any] = set()

    def add_player(player_id: Any) -> None:
        if player_id in seen_ids:
            return
        player = tournament.players.get(player_id)
        if player:
            players.append(player)
            seen_ids.add(player_id)

    for result_entry in results_data:
        white_id, black_id = result_entry[:2]
        add_player(white_id)
        add_player(black_id)

    if round_index_being_undone < len(tournament.rounds_byes_ids):
        bye_player_id = tournament.rounds_byes_ids[round_index_being_undone]
        if bye_player_id:
            add_player(bye_player_id)

    return players


def revert_player_round_data(player: Player) -> bool:
    """Remove the last round's result/history data from a player."""

    if not player.results:
        return False

    last_result = player.results.pop()
    if last_result is not None:
        player.score = round(player.score - last_result, 1)

    if player.running_scores:
        player.running_scores.pop()

    last_opponent_id = player.opponent_ids.pop() if player.opponent_ids else None
    last_color = player.color_history.pop() if player.color_history else None

    if last_color == "Black":
        player.num_black_games = max(0, player.num_black_games - 1)

    if last_opponent_id is None:
        player.has_received_bye = (
            (None in player.opponent_ids) if player.opponent_ids else False
        )

    player._opponents_played_cache = []
    return True


def _round_control_state(phase: TournamentPhase) -> RoundControlState:
    if phase == TournamentPhase.NOT_STARTED:
        return "start"
    if phase == TournamentPhase.AWAITING_RESULTS:
        return "record"
    if phase == TournamentPhase.AWAITING_NEXT_ROUND:
        return "prepare"
    return "finished"
