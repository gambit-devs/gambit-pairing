"""Qt-free controller for editing a round's manual pairings.

The manual pairing dialog is a view.  This controller owns the editable
pairing state, undo snapshots, and pairing actions so the view only has to
render state and translate Qt events into intent-level calls.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol, Sequence

from gambitpairing.controllers.pairing.dutch_swiss import create_dutch_swiss_pairings
from gambitpairing.models.player import Player

PairingLike = tuple[Player | None, Player | None]


class PairingContext(Protocol):
    """Tournament data required by the manual pairing workflow."""

    @property
    def previous_matches(self) -> Iterable[frozenset[str]]: ...

    @property
    def num_rounds(self) -> int: ...


@dataclass(frozen=True)
class ValidationProjection:
    """Presentation-ready validation text returned to the view."""

    text: str
    has_warnings: bool


def paired_player_count(pairings: Sequence[PairingLike]) -> int:
    """Return the number of players on complete boards."""
    return sum(1 for white, black in pairings if white and black) * 2


def incomplete_pairing_count(pairings: Sequence[PairingLike]) -> int:
    """Return the number of boards with only one or no player."""
    return sum(1 for white, black in pairings if not (white and black))


def accounted_player_ids(
    pairings: Sequence[PairingLike], bye_players: Sequence[Player]
) -> set[str]:
    """Return IDs already assigned to a board or bye."""
    accounted: set[str] = set()
    for white, black in pairings:
        if white:
            accounted.add(white.id)
        if black:
            accounted.add(black.id)
    for bye_player in bye_players:
        accounted.add(bye_player.id)
    return accounted


def active_unpaired_players(
    players: Iterable[Player],
    pairings: Sequence[PairingLike],
    bye_players: Sequence[Player],
) -> list[Player]:
    """Return active players not represented in the current edit."""
    accounted = accounted_player_ids(pairings, bye_players)
    return [
        player for player in players if player.is_active and player.id not in accounted
    ]


def repeat_pairing_boards(
    pairings: Sequence[PairingLike], previous_matches: Iterable[frozenset[str]]
) -> list[str]:
    """Return board numbers that repeat an earlier opponent pairing."""
    repeat_boards: list[str] = []
    for index, (white, black) in enumerate(pairings):
        if not white or not black:
            continue
        for player_pair in previous_matches:
            if (
                isinstance(player_pair, frozenset)
                and len(player_pair) == 2
                and white.id in player_pair
                and black.id in player_pair
            ):
                repeat_boards.append(str(index + 1))
                break
    return repeat_boards


def build_stats_text(
    players: Sequence[Player],
    pairings: Sequence[PairingLike],
    bye_players: Sequence[Player],
) -> str:
    """Build the compact status line shown below the pairing table."""
    total_players = len(players)
    active_players = len([player for player in players if player.is_active])
    withdrawn_players = total_players - active_players
    paired_players = paired_player_count(pairings)
    incomplete_pairings = incomplete_pairing_count(pairings)
    bye_count = len(bye_players)
    remaining_active_players = active_players - paired_players - bye_count

    stats_text = (
        f"Players: {paired_players}/{active_players} active paired • "
        f"{remaining_active_players} active remaining • "
        f"{incomplete_pairings} incomplete boards"
    )
    if withdrawn_players > 0:
        stats_text += f" • {withdrawn_players} withdrawn"

    if bye_players:
        if len(bye_players) == 1:
            status = " (Withdrawn)" if not bye_players[0].is_active else ""
            stats_text += f" • Bye: {bye_players[0].name}{status}"
        else:
            withdrawn_byes = [player for player in bye_players if not player.is_active]
            bye_text = f" • Byes: {len(bye_players)} players"
            if withdrawn_byes:
                bye_text += f" ({len(withdrawn_byes)} withdrawn)"
            stats_text += bye_text
    return stats_text


def build_validation_projection(
    players: Sequence[Player],
    pairings: Sequence[PairingLike],
    bye_players: Sequence[Player],
    previous_matches: Iterable[frozenset[str]] | None = None,
) -> ValidationProjection:
    """Build validation text without importing Qt or touching widgets."""
    warnings: list[str] = []

    incomplete_count = incomplete_pairing_count(pairings)
    if incomplete_count > 0:
        warnings.append(f"{incomplete_count} incomplete boards need completion")

    unpaired = active_unpaired_players(players, pairings, bye_players)
    if unpaired:
        player_names = ", ".join([player.name for player in unpaired])
        warnings.append(f"{len(unpaired)} active player(s) not paired: {player_names}")

    if previous_matches:
        repeat_boards = repeat_pairing_boards(pairings, previous_matches)
        if repeat_boards:
            warnings.append(f"Repeat pairings on boards: {', '.join(repeat_boards)}")

    if warnings:
        return ValidationProjection("⚠️ " + " • ".join(warnings), True)
    return ValidationProjection("✅ All validations passed", False)


def unresolved_active_players(
    players: Sequence[Player],
    pairings: Sequence[PairingLike],
    bye_players: Sequence[Player],
) -> set[Player]:
    """Return active players that would prevent finalization."""
    accounted = accounted_player_ids(pairings, bye_players)
    unresolved: set[Player] = set()

    for white, black in pairings:
        if white and not black and white.is_active:
            unresolved.add(white)
        if black and not white and black.is_active:
            unresolved.add(black)

    for player in players:
        if player.is_active and player.id not in accounted:
            unresolved.add(player)

    return unresolved


def build_unresolved_players_message(players: Iterable[Player]) -> str:
    """Build the finalization prompt for unresolved active players."""
    unresolved = list(players)
    player_names = [f"• {player.name} ({player.rating})" for player in unresolved]
    names_text = "\n".join(player_names)
    return (
        f"The following {len(unresolved)} active player(s) are not paired, "
        "given a bye, or withdrawn:\n\n"
        f"{names_text}\n\nWould you like to withdraw all these players from the tournament?"
    )


class ManualPairingController:
    """Own and mutate the state edited by :class:`ManualPairingDialog`."""

    def __init__(
        self,
        players: list[Player],
        existing_pairings: Iterable[PairingLike] | None = None,
        existing_byes: Iterable[Player] | Player | None = None,
        round_number: int = 1,
        tournament: PairingContext | None = None,
        max_history: int = 10,
    ) -> None:
        self.players = players
        self.round_number = round_number
        self.tournament = tournament
        self.max_history = max_history
        self.pairings: list[PairingLike] = list(existing_pairings or [])
        if existing_byes is None:
            self.bye_players: list[Player] = []
        elif isinstance(existing_byes, Player):
            self.bye_players = [existing_byes]
        else:
            self.bye_players = list(existing_byes)
        self.history: list[tuple[list[PairingLike], list[Player]]] = []

    @property
    def can_undo(self) -> bool:
        """Whether a previous state is available."""
        return bool(self.history)

    @property
    def previous_matches(self) -> Iterable[frozenset[str]] | None:
        """Expose tournament repeat history without coupling the view to it."""
        if self.tournament is None:
            return None
        return self.tournament.previous_matches

    def save_state_for_undo(self) -> None:
        """Store a bounded snapshot before a user-visible mutation."""
        self.history.append((list(self.pairings), list(self.bye_players)))
        if len(self.history) > self.max_history:
            self.history.pop(0)

    def undo(self) -> bool:
        """Restore the most recent snapshot."""
        if not self.history:
            return False
        pairings, byes = self.history.pop()
        self.pairings = list(pairings)
        self.bye_players = list(byes)
        return True

    def clear_pairings(self) -> bool:
        """Clear boards and byes, returning whether anything changed."""
        if not self.pairings and not self.bye_players:
            return False
        self.save_state_for_undo()
        self.pairings.clear()
        self.bye_players.clear()
        return True

    def delete_pairing(self, row: int) -> bool:
        """Delete one board and return its players to the pool."""
        if not 0 <= row < len(self.pairings):
            return False
        self.save_state_for_undo()
        del self.pairings[row]
        return True

    def add_pairings(
        self, pairings: Iterable[PairingLike], bye_player: Player | None = None
    ) -> None:
        """Append generated pairings and an optional generated bye."""
        self.save_state_for_undo()
        self.pairings.extend(pairings)
        if bye_player is not None and bye_player not in self.bye_players:
            self.bye_players.append(bye_player)

    def replace_pairings(
        self, pairings: Iterable[PairingLike], bye_players: Iterable[Player]
    ) -> None:
        """Replace the current edit with imported pairings."""
        self.save_state_for_undo()
        self.pairings = list(pairings)
        self.bye_players = list(bye_players)

    def remove_player_from_all_positions(self, player_id: str) -> None:
        """Remove one player from boards and byes without taking a snapshot."""
        self.bye_players = [
            player for player in self.bye_players if player.id != player_id
        ]
        for index, (white, black) in enumerate(self.pairings):
            if white and white.id == player_id:
                self.pairings[index] = (None, black)
            if black and black.id == player_id:
                self.pairings[index] = (white, None)
        self.pairings = [
            (white, black)
            for white, black in self.pairings
            if white is not None or black is not None
        ]

    def is_player_assigned(self, player_id: str) -> bool:
        """Return whether a player is already on a board or in the bye pool."""
        return player_id in accounted_player_ids(self.pairings, self.bye_players)

    def place_player(self, player_id: str, row: int, color: str) -> bool:
        """Place a player into a board/color cell."""
        player = next((item for item in self.players if item.id == player_id), None)
        if player is None or color not in {"white", "black"} or row < 0:
            return False

        self.save_state_for_undo()
        self.remove_player_from_all_positions(player_id)
        while len(self.pairings) <= row:
            self.pairings.append((None, None))

        white, black = self.pairings[row]
        self.pairings[row] = (player, black) if color == "white" else (white, player)
        return True

    def assign_bye(self, player: Player) -> bool:
        """Move a player to the bye pool."""
        if player in self.bye_players:
            return False
        self.save_state_for_undo()
        self.remove_player_from_all_positions(player.id)
        self.bye_players.append(player)
        return True

    def swap_colors(self, row: int) -> bool:
        """Swap the colors on one complete or incomplete board."""
        if not 0 <= row < len(self.pairings):
            return False
        self.save_state_for_undo()
        white, black = self.pairings[row]
        self.pairings[row] = (black, white)
        return True

    def toggle_player_withdrawal(self, player: Player) -> None:
        """Toggle withdrawal and remove a newly withdrawn player from the edit."""
        self.save_state_for_undo()
        player.is_active = not player.is_active
        if not player.is_active:
            self.remove_player_from_all_positions(player.id)

    def withdraw_players(self, players: Iterable[Player]) -> None:
        """Withdraw unresolved players selected during finalization."""
        self.save_state_for_undo()
        for player in players:
            player.is_active = False
            self.remove_player_from_all_positions(player.id)

    def is_player_available(self, player: Player) -> bool:
        """Return whether an active player can be added to a new board."""
        if not player.is_active:
            return False
        return player.id not in accounted_player_ids(self.pairings, self.bye_players)

    def available_players(self) -> list[Player]:
        """Return active players not currently assigned."""
        return [player for player in self.players if self.is_player_available(player)]

    def get_dutch_pairings(
        self, available_players: list[Player]
    ) -> tuple[list[PairingLike], Player | None]:
        """Generate pairings for the current edit without any Qt dependency."""
        if self.tournament is None:
            players_copy = available_players.copy()
            pairings: list[PairingLike] = []
            while len(players_copy) >= 2:
                pairings.append((players_copy.pop(0), players_copy.pop(0)))
            return pairings, players_copy[0] if players_copy else None

        def get_eligible_bye_player(players: list[Player]) -> Player | None:
            candidates = sorted(players, key=lambda player: player.rating)
            for player in candidates:
                if not player.has_received_bye:
                    return player
            return candidates[0] if candidates else None

        previous_matches: set[frozenset[str]] = set(self.previous_matches or ())
        generated_pairings, bye_player, _pairing_ids, _bye_id = (
            create_dutch_swiss_pairings(
                available_players,
                self.round_number,
                previous_matches,
                get_eligible_bye_player,
                None,
                self.tournament.num_rounds,
            )
        )
        pairings: list[PairingLike] = [
            (white, black) for white, black in generated_pairings
        ]
        return pairings, bye_player
