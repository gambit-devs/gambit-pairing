"""Application session: owns services and commands for a tournament model."""

from __future__ import annotations

from copy import deepcopy
from importlib import import_module
from typing import Any, Callable, Dict, List, Optional, Tuple

from gambitpairing.constants import DEFAULT_MODE
from gambitpairing.models.player import Player
from gambitpairing.models.tournament.pairing_history import PairingHistory
from gambitpairing.models.tournament.round_data import RoundData
from gambitpairing.models.tournament.tournament import Tournament
from gambitpairing.models.tournament.tournament_config import TournamentConfig
from gambitpairing.utils import setup_logger

logger = setup_logger(__name__)


class TournamentSession:
    """Qt-free application controller around canonical model state."""

    def __init__(
        self,
        name: str,
        players: List[Player],
        num_rounds: int,
        tiebreak_order: Optional[List[str]] = None,
        pairing_system: str = "dutch_swiss",
        tournament_mode: Optional[str] = None,
        fide_strict: bool = False,
        use_experimental_dutch: bool = False,
    ) -> None:
        config = TournamentConfig(
            name=name,
            num_rounds=num_rounds,
            pairing_system=pairing_system,
            use_experimental_dutch=use_experimental_dutch,
            tournament_mode=tournament_mode or DEFAULT_MODE,
            fide_strict=fide_strict,
            tiebreak_order=tiebreak_order,
        )
        self.model = Tournament(
            config=config, players={player.id: player for player in players}
        )

        from gambitpairing.controllers.tournament.result import ResultRecorder
        from gambitpairing.controllers.tournament.round import RoundController
        from gambitpairing.controllers.tournament.tiebreak_calculator import (
            TiebreakCalculator,
        )

        self.round_controller = RoundController(
            model=self.model,
            pairing_system=self.config.pairing_system,
            num_rounds=self.config.num_rounds,
            pairing_history=self.pairing_history,
            fide_strict=self.config.fide_strict,
            use_experimental_dutch=self.config.use_experimental_dutch,
        )
        self.round_manager = self.round_controller
        self.result_recorder = ResultRecorder()
        self.tiebreak_calculator = TiebreakCalculator()

    @property
    def config(self):
        return self.model.config

    @config.setter
    def config(self, value):
        self.model.config = value

    @property
    def players(self):
        return self.model.players

    @property
    def pairing_history(self):
        return self.model.pairing_history

    @pairing_history.setter
    def pairing_history(self, value):
        self.model.pairing_history = value

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
        if value == "bbp_dutch":
            value = "dutch_swiss"
            self.use_experimental_dutch = False
        self.config.pairing_system = value
        self.round_controller.pairing_system = value

    @property
    def use_experimental_dutch(self) -> bool:
        return self.config.use_experimental_dutch

    @use_experimental_dutch.setter
    def use_experimental_dutch(self, value: bool) -> None:
        normalized_value = bool(value)
        self.config.use_experimental_dutch = normalized_value
        if hasattr(self, "round_controller"):
            self.round_controller.use_experimental_dutch = normalized_value

    @property
    def tournament_mode(self) -> str:
        return self.config.tournament_mode

    @tournament_mode.setter
    def tournament_mode(self, value: str) -> None:
        self.config.tournament_mode = value

    @property
    def fide_strict(self) -> bool:
        return self.config.fide_strict

    @fide_strict.setter
    def fide_strict(self, value: bool) -> None:
        self.config.fide_strict = bool(value)
        self.round_controller.fide_strict = bool(value)

    @property
    def tiebreak_order(self) -> List[str]:
        return self.config.tiebreak_order or []

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

    def update_settings(
        self, num_rounds: int, tiebreak_order: List[str], mode: str
    ) -> List[str]:
        from gambitpairing.constants import MODE_FIDE, MODE_USCF, TIEBREAK_NAMES

        if mode not in {MODE_FIDE, MODE_USCF}:
            raise ValueError("Unsupported federation mode")
        if (
            not isinstance(num_rounds, int)
            or isinstance(num_rounds, bool)
            or num_rounds < 1
        ):
            raise ValueError("Round count must be a positive integer")
        if any(key not in TIEBREAK_NAMES for key in tiebreak_order) or len(
            set(tiebreak_order)
        ) != len(tiebreak_order):
            raise ValueError("Invalid tiebreak order")
        if num_rounds != self.num_rounds and (
            self.rounds or self.pairing_system == "round_robin"
        ):
            raise ValueError(
                "Round count cannot change after pairing or for round robin"
            )
        messages = []
        if mode == MODE_FIDE and self.pairing_system == "round_robin":
            from gambitpairing.constants import (
                TB_BUCHHOLZ,
                TB_BUCHHOLZ_CUT_1,
                TB_BUCHHOLZ_MEDIAN_1,
            )

            if any(
                key in {TB_BUCHHOLZ, TB_BUCHHOLZ_CUT_1, TB_BUCHHOLZ_MEDIAN_1}
                for key in tiebreak_order
            ):
                raise ValueError(
                    "Buchholz tiebreaks cannot be used for FIDE round robins"
                )
        if num_rounds != self.num_rounds:
            self.num_rounds = num_rounds
            messages.append(f"Number of rounds set to {num_rounds}.")
        if list(tiebreak_order) != self.tiebreak_order:
            self.tiebreak_order = list(tiebreak_order)
            messages.append("Tiebreak order updated.")
        if mode != self.tournament_mode:
            self.tournament_mode = mode
            messages.append(f"Chess federation changed to {mode}.")
        return messages

    def add_player(self, player: Player) -> None:
        self.players[player.id] = player

    def update_player(self, player_id: str, data: Dict[str, Any]) -> Player:
        """Update registration metadata without replacing tournament history."""
        from gambitpairing.models.player import create_player_from_dict

        player = self.players[player_id]
        editable = {
            "name",
            "rating",
            "phone",
            "email",
            "gender",
            "dob",
            "club",
            "federation",
            "cfc_id",
            "fide_id",
            "fide_title",
            "fide_standard",
            "fide_rapid",
            "fide_blitz",
            "birth_year",
        }
        changes = {key: value for key, value in data.items() if key in editable}
        name = changes.get("name", player.name)
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Player name is required")
        if any(
            other.id != player_id and other.name == name
            for other in self.players.values()
        ):
            raise ValueError("A player with this name already exists")
        replacement = create_player_from_dict({**player.to_dict(), **changes})
        self.players[player_id] = replacement
        return replacement

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
        if current_round != len(self.rounds) + 1:
            raise ValueError("Pairings must be generated in round order")
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
        bye_type: str = "full",
    ) -> bool:
        if bye_type not in {"full", "half", "zero"}:
            return False
        assigned = [player.id for pair in pairings for player in pair]
        if bye_player is not None:
            assigned.append(bye_player.id)
        if set(assigned) != {
            player.id for player in self.get_player_list(active_only=True)
        }:
            return False
        success = self.round_controller.set_manual_pairings(
            round_index + 1, pairings, bye_player
        )
        if success:
            self.rounds[round_index].bye_type = bye_type
            self.rounds[round_index].active_player_ids = sorted(assigned)
        return success

    def record_results(self, round_index: int, results_data: List[tuple]) -> bool:
        if round_index < 0 or any(
            not item.is_completed for item in self.rounds[:round_index]
        ):
            return False
        round_data = self.round_controller.get_round(round_index + 1)
        if round_data is None:
            logger.error(
                "Cannot record results: round %s does not exist", round_index + 1
            )
            return False

        success = self.result_recorder.record_round_results(
            round_data, results_data, self.players
        )
        if success:
            self._rebuild_pairing_history()
            round_data.pending_results.clear()
            self.round_controller.mark_round_completed(round_index + 1)
        return success

    def set_pending_results(self, round_index: int, results_data: List[tuple]) -> bool:
        """Persist result-entry progress for an uncompleted round.

        Pending results deliberately do not touch player scores, standings, or
        the completed-round count. They are part of the round model so the
        normal tournament save/load path can restore an interrupted entry
        session.
        """
        round_data = self.round_controller.get_round(round_index + 1)
        if round_data is None or round_data.is_completed:
            return False
        return self.result_recorder.set_pending_results(round_data, results_data)

    def compute_tiebreakers(self) -> None:
        self.tiebreak_calculator.mode = self.config.tournament_mode
        self.tiebreak_calculator.rounds = self.get_completed_rounds()
        self.tiebreak_calculator.pairing_system = self.pairing_system
        self.tiebreak_calculator.calculate_all_tiebreaks(self.players)

    def get_standings(self) -> List[Player]:
        from gambitpairing.controllers.tournament.standings import rank_players

        return rank_players(
            self.players,
            self.tiebreak_order,
            self.config.tournament_mode,
            self.get_completed_rounds(),
            self.pairing_system,
        )

    def _compare_players(self, p1: Player, p2: Player) -> int:
        """Compatibility comparator using the canonical group-aware ranking."""
        ranks = {player.id: player.standing_rank for player in self.get_standings()}
        first, second = ranks.get(p1.id), ranks.get(p2.id)
        if first is None or second is None:
            raise ValueError("Cannot compare players outside the standings")
        return (second > first) - (second < first)

    def get_completed_rounds(self) -> int:
        return self.round_controller.completed_rounds_count

    def clear_rounds_from(self, round_index: int) -> None:
        """Remove pairings/results/history for ``round_index`` and later."""
        if round_index < 0:
            round_index = 0
        # Roll back on detached state first so a failed undo cannot partially
        # mutate the live roster or invalidate references held by views.
        trial_players = deepcopy(self.players)
        trial_rounds = deepcopy(self.rounds)
        for item in reversed(trial_rounds[round_index:]):
            if item.is_completed and not self.result_recorder.undo_round_results(
                item, trial_players
            ):
                raise ValueError("Round histories cannot be rolled back safely")
        for player_id, player in trial_players.items():
            self.players[player_id].__dict__.update(player.__dict__)
            self.players[player_id]._opponents_played_cache = []
        self.round_controller.rounds = self.round_controller.rounds[:round_index]
        self._rebuild_pairing_history()

    def _get_eligible_bye_player(
        self, potential_bye_players: List[Player]
    ) -> Optional[Player]:
        active_players = [
            player for player in potential_bye_players if player.is_active
        ]
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
            unplayed = {
                frozenset((result.white_id, result.black_id))
                for result in round_data.results
                if result.outcome_type != "normal"
            }
            for white_id, black_id in round_data.pairings:
                if frozenset((white_id, black_id)) not in unplayed:
                    self.pairing_history.add_pairing(white_id, black_id)
        self.round_controller.pairing_history = self.pairing_history

    def to_dict(self) -> Dict[str, Any]:
        """Compatibility wrapper for representation serialization."""
        representation = import_module("gambitpairing.representation.tournament")
        return representation.tournament_to_dict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TournamentSession":
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
                    bye_type=existing.bye_type if existing else "full",
                    results=existing.results if existing else [],
                    is_completed=existing.is_completed if existing else False,
                    pending_results=(existing.pending_results if existing else []),
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
