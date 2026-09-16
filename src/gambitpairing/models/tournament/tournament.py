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
    # Tiebreak values are derived from this tournament's rounds and rules.
    # They are deliberately not part of a Player or the persisted document.
    tiebreakers: dict[str, dict[str, float]] = field(
        default_factory=dict, repr=False, compare=False
    )

    def invalidate_tiebreakers(self) -> None:
        """Discard values derived from the tournament's current state."""
        self.tiebreakers.clear()
