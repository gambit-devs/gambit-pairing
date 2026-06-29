"""Tournament model façade.

The model owns tournament state and delegates operations to controller/helper
classes. Serialization is intentionally delegated to
``gambitpairing.representation.tournament``.
"""

from __future__ import annotations

import functools
from importlib import import_module
from typing import Any, Callable, Dict, List, Optional, Tuple

from gambitpairing.models.player import Player
from gambitpairing.utils import setup_logger

from .pairing_history import PairingHistory
from .round_data import RoundData
from .tournament_config import TournamentConfig

logger = setup_logger(__name__)


class Tournament:
    """State holder and compatibility façade for tournament workflows."""

    def __init__(
        self,
        name: str,
        players: List[Player],
        num_rounds: int,
        tiebreak_order: Optional[List[str]] = None,
        pairing_system: str = "dutch_swiss",
    ) -> None:
        self.config = TournamentConfig(
            name=name,
            num_rounds=num_rounds,
            pairing_system=pairing_system,
            tiebreak_order=tiebreak_order or TournamentConfig("", 0).tiebreak_order,
        )
        self.players: Dict[str, Player] = {player.id: player for player in players}
        self.pairing_history = PairingHistory()

        from gambitpairing.controllers.tournament.round import RoundController
        from gambitpairing.controllers.tournament.result import ResultRecorder
        from gambitpairing.controllers.tournament.tiebreak_calculator import (
            TiebreakCalculator,
        )

        self.round_controller = RoundController(
            pairing_system=self.config.pairing_system,
            num_rounds=self.config.num_rounds,
            pairing_history=self.pairing_history,
        )
        self.round_manager = self.round_controller
        self.result_recorder = ResultRecorder()
        self.tiebreak_calculator = TiebreakCalculator()

    @property
    def name(self) -> str:
        return self.config.name

    @name.setter
    def name(self, value: str) -> None:
        self.config.name = value

    @property
    def num_rounds(self) -> int:
        return self.config.num_rounds

    @num_rounds.setter
    def num_rounds(self, value: int) -> None:
        self.config.num_rounds = value
        self.round_controller.num_rounds = value

    @property
    def pairing_system(self) -> str:
        return self.config.pairing_system

    @pairing_system.setter
    def pairing_system(self, value: str) -> None:
        self.config.pairing_system = value
        self.round_controller.pairing_system = value

    @property
    def tiebreak_order(self) -> List[str]:
        return self.config.tiebreak_order

    @tiebreak_order.setter
    def tiebreak_order(self, value: List[str]) -> None:
        self.config.tiebreak_order = value

    @property
    def tournament_over(self) -> bool:
        return self.config.tournament_over

    @tournament_over.setter
    def tournament_over(self, value: bool) -> None:
        self.config.tournament_over = value

    @property
    def rounds(self) -> List[RoundData]:
        return self.round_controller.rounds

    @rounds.setter
    def rounds(self, value: List[RoundData]) -> None:
        self.round_controller.rounds = value
        self._rebuild_pairing_history()

    def get_player_list(self, active_only: bool = False) -> List[Player]:
        players = list(self.players.values())
        if active_only:
            return [player for player in players if player.is_active]
        return players

    def add_player(self, player: Player) -> None:
        self.players[player.id] = player

    def remove_player(self, player_id: str) -> bool:
        return self.players.pop(player_id, None) is not None

    def set_player_active(self, player_id: str, is_active: bool) -> bool:
        player = self.players.get(player_id)
        if not player:
            return False
        player.is_active = is_active
        return True

    def _get_active_players(self) -> List[Player]:
        return self.get_player_list(active_only=True)

    def create_pairings(
        self,
        current_round: int,
        allow_repeat_pairing_callback: Optional[Callable] = None,
    ) -> Tuple[List[Tuple[Player, Player]], Optional[Player]]:
        pairings, bye_player = self.round_controller.create_next_round(
            players=self.players,
            bye_callback=self._get_eligible_bye_player,
            repeat_pairing_callback=allow_repeat_pairing_callback,
        )
        self.config.num_rounds = self.round_controller.num_rounds
        logger.info(
            "Created pairings for round %s: %s games, bye: %s",
            current_round,
            len(pairings),
            bye_player.name if bye_player else "None",
        )
        return pairings, bye_player

    def get_pairings_for_round(
        self, round_index: int
    ) -> Tuple[List[Tuple[Player, Player]], Optional[Player]]:
        return self.round_controller.get_pairings_for_display(
            round_index + 1, self.players
        )

    def set_manual_pairings(
        self,
        round_index: int,
        pairings: List[Tuple[Player, Player]],
        bye_player: Optional[Player],
    ) -> bool:
        return self.round_controller.set_manual_pairings(
            round_index + 1, pairings, bye_player
        )

    def record_results(self, round_index: int, results_data: List[tuple]) -> bool:
        round_data = self.round_controller.get_round(round_index + 1)
        if round_data is None:
            logger.error("Cannot record results: round %s does not exist", round_index + 1)
            return False

        success = self.result_recorder.record_round_results(
            round_data, results_data, self.players
        )
        if success:
            self.round_controller.mark_round_completed(round_index + 1)
        return success

    def compute_tiebreakers(self) -> None:
        self.tiebreak_calculator.calculate_all_tiebreaks(self.players)

    def get_standings(self) -> List[Player]:
        active_players = self.get_player_list(active_only=True)
        if not active_players:
            return []
        self.compute_tiebreakers()
        return sorted(
            active_players,
            key=functools.cmp_to_key(self._compare_players),
            reverse=True,
        )

    def _compare_players(self, p1: Player, p2: Player) -> int:
        if p1.score != p2.score:
            return 1 if p1.score > p2.score else -1

        p1_won, p2_won = self.tiebreak_calculator.calculate_head_to_head(p1, p2)
        if p1_won and not p2_won:
            return 1
        if p2_won and not p1_won:
            return -1

        for tiebreak_key in self.config.tiebreak_order:
            tb1 = p1.tiebreakers.get(tiebreak_key, 0.0)
            tb2 = p2.tiebreakers.get(tiebreak_key, 0.0)
            if tb1 != tb2:
                return 1 if tb1 > tb2 else -1

        if p1.rating != p2.rating:
            return 1 if p1.rating > p2.rating else -1
        if p1.name != p2.name:
            return -1 if p1.name < p2.name else 1
        return 0

    def get_completed_rounds(self) -> int:
        return self.round_controller.completed_rounds_count

    def clear_rounds_from(self, round_index: int) -> None:
        """Remove pairings/results/history for ``round_index`` and later."""
        if round_index < 0:
            round_index = 0
        self.round_controller.rounds = self.round_controller.rounds[:round_index]
        self._rebuild_pairing_history()

    def _get_eligible_bye_player(
        self, potential_bye_players: List[Player]
    ) -> Optional[Player]:
        active_players = [player for player in potential_bye_players if player.is_active]
        if not active_players:
            return None

        no_bye_players = [
            player for player in active_players if not player.has_received_bye
        ]
        candidates = no_bye_players or active_players
        candidates.sort(key=lambda player: (player.score, player.rating, player.name))
        return candidates[0]

    def _rebuild_pairing_history(self) -> None:
        self.pairing_history = PairingHistory(
            manual_adjustments={
                key: value
                for key, value in self.pairing_history.manual_adjustments.items()
                if key <= len(self.round_controller.rounds)
            }
        )
        for round_data in self.round_controller.rounds:
            for white_id, black_id in round_data.pairings:
                self.pairing_history.add_pairing(white_id, black_id)
        self.round_controller.pairing_history = self.pairing_history

    def to_dict(self) -> Dict[str, Any]:
        """Compatibility wrapper for representation serialization."""
        representation = import_module("gambitpairing.representation.tournament")
        return representation.tournament_to_dict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Tournament":
        """Compatibility wrapper for representation deserialization."""
        representation = import_module("gambitpairing.representation.tournament")
        return representation.tournament_from_dict(data)

    @property
    def rounds_pairings_ids(self) -> List[List[Tuple[str, str]]]:
        return [round_data.pairings for round_data in self.round_controller.rounds]

    @rounds_pairings_ids.setter
    def rounds_pairings_ids(self, value: List[List[Tuple[str, str]]]) -> None:
        existing_rounds = self.round_controller.rounds
        new_rounds: List[RoundData] = []
        for index, pairings in enumerate(value):
            existing = existing_rounds[index] if index < len(existing_rounds) else None
            pairing_ids: List[Tuple[str, str]] = [
                (str(pairing[0]), str(pairing[1])) for pairing in pairings
            ]
            new_rounds.append(
                RoundData(
                    round_number=index + 1,
                    pairings=pairing_ids,
                    bye_player_id=existing.bye_player_id if existing else None,
                    results=existing.results if existing else [],
                    is_completed=existing.is_completed if existing else False,
                )
            )
        self.rounds = new_rounds

    @property
    def rounds_byes_ids(self) -> List[Optional[str]]:
        return [round_data.bye_player_id for round_data in self.round_controller.rounds]

    @rounds_byes_ids.setter
    def rounds_byes_ids(self, value: List[Optional[str]]) -> None:
        while len(self.round_controller.rounds) < len(value):
            self.round_controller.rounds.append(
                RoundData(round_number=len(self.round_controller.rounds) + 1)
            )
        self.round_controller.rounds = self.round_controller.rounds[: len(value)]
        for index, bye_player_id in enumerate(value):
            self.round_controller.rounds[index].bye_player_id = bye_player_id
        self._rebuild_pairing_history()

    @property
    def previous_matches(self):
        return self.pairing_history.previous_matches

    @property
    def manual_pairings(self):
        return self.pairing_history.manual_adjustments
