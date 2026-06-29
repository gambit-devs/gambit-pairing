from .match_result import MatchResult
from .pairing_history import PairingHistory
from .round_data import RoundData
from .tournament_config import TournamentConfig
from .tournament_state import (
    TournamentPhase,
    TournamentState,
)

__all__ = [
    "MatchResult",
    "PairingHistory",
    "RoundData",
    "Tournament",
    "TournamentConfig",
    "TournamentPhase",
    "TournamentState",
]


def __getattr__(name: str):
    if name == "Tournament":
        from importlib import import_module

        return import_module("gambitpairing.models.tournament.tournament").Tournament
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
