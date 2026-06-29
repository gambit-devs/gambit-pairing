"""Tournament dictionary and JSON document representation."""

from __future__ import annotations

import json
from importlib import import_module
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from gambitpairing.models.player import create_player_from_dict
from gambitpairing.models.tournament import (
    MatchResult,
    PairingHistory,
    RoundData,
    TournamentConfig,
)


def tournament_to_dict(tournament: Any) -> Dict[str, Any]:
    """Project a tournament model into JSON-safe primitives."""
    return {
        "__version__": 1,
        "config": tournament.config.to_dict(),
        "players": [player.to_dict() for player in tournament.players.values()],
        "rounds": [round_data_to_dict(round_data) for round_data in tournament.rounds],
        "pairing_history": pairing_history_to_dict(tournament.pairing_history),
    }


def tournament_from_dict(data: Dict[str, Any]) -> Any:
    """Reconstruct a tournament from current or legacy dictionary shapes."""
    tournament_module = import_module("gambitpairing.models.tournament.tournament")
    Tournament = tournament_module.Tournament

    config = tournament_config_from_dict(data.get("config", data))
    players = [
        create_player_from_dict(player_data)
        for player_data in _iter_player_dicts(data.get("players", []))
    ]

    tournament = Tournament(
        name=config.name,
        players=players,
        num_rounds=config.num_rounds,
        tiebreak_order=config.tiebreak_order,
        pairing_system=config.pairing_system,
    )
    tournament.config = config
    tournament.round_controller.pairing_system = config.pairing_system
    tournament.round_controller.num_rounds = config.num_rounds

    if "rounds" in data:
        tournament.rounds = [round_data_from_dict(item) for item in data["rounds"]]
    else:
        tournament.rounds = _legacy_rounds_from_dict(data)

    if "pairing_history" in data:
        tournament.pairing_history = pairing_history_from_dict(data["pairing_history"])
        tournament.round_controller.pairing_history = tournament.pairing_history
    else:
        tournament._rebuild_pairing_history()
        tournament.pairing_history.manual_adjustments = {
            int(key): value for key, value in data.get("manual_pairings", {}).items()
        }

    for player in tournament.players.values():
        player._opponents_played_cache = []

    return tournament


def save_tournament_document(
    path: str | Path,
    tournament: Any,
    gui_state: Optional[Dict[str, Any]] = None,
) -> None:
    """Save a tournament JSON document."""
    data = tournament_to_dict(tournament)
    if gui_state is not None:
        data["gui_state"] = gui_state
    Path(path).write_text(json.dumps(data, indent=4), encoding="utf-8")


def load_tournament_document(path: str | Path) -> Tuple[Any, Dict[str, Any]]:
    """Load a tournament JSON document and return model plus GUI state."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return tournament_from_dict(data), data.get("gui_state", {})


def tournament_config_to_dict(config: TournamentConfig) -> Dict[str, Any]:
    return config.to_dict()


def tournament_config_from_dict(data: Dict[str, Any]) -> TournamentConfig:
    return TournamentConfig.from_dict(data)


def round_data_to_dict(round_data: RoundData) -> Dict[str, Any]:
    return round_data.to_dict()


def round_data_from_dict(data: Dict[str, Any]) -> RoundData:
    return RoundData.from_dict(data)


def match_result_to_dict(match_result: MatchResult) -> Dict[str, Any]:
    return match_result.to_dict()


def match_result_from_dict(data: Dict[str, Any]) -> MatchResult:
    return MatchResult.from_dict(data)


def pairing_history_to_dict(pairing_history: PairingHistory) -> Dict[str, Any]:
    return pairing_history.to_dict()


def pairing_history_from_dict(data: Dict[str, Any]) -> PairingHistory:
    return PairingHistory.from_dict(data)


def _iter_player_dicts(players: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(players, dict):
        return players.values()
    return players


def _legacy_rounds_from_dict(data: Dict[str, Any]) -> List[RoundData]:
    pairings_by_round = data.get("rounds_pairings_ids", [])
    byes_by_round = data.get("rounds_byes_ids", [])
    rounds: List[RoundData] = []

    for index, pairings in enumerate(pairings_by_round):
        rounds.append(
            RoundData(
                round_number=index + 1,
                pairings=[tuple(pairing) for pairing in pairings],
                bye_player_id=byes_by_round[index]
                if index < len(byes_by_round)
                else None,
            )
        )

    return rounds
