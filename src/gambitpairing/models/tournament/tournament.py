"""Canonical tournament data. No controller, GUI, or I/O dependencies."""

from dataclasses import dataclass, field

from gambitpairing.models.player import Player

from .pairing_history import PairingHistory
from .round_data import RoundData
from .tournament_config import TournamentConfig


@dataclass
class Tournament:
    config: TournamentConfig
    players: dict[str, Player] = field(default_factory=dict)
    rounds: list[RoundData] = field(default_factory=list)
    pairing_history: PairingHistory = field(default_factory=PairingHistory)
