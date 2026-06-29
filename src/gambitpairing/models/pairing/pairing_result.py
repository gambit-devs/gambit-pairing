"""Pairing result data class."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from gambitpairing.models.player import Player


@dataclass(slots=True)
class PairingResult:
    """Result of a pairing computation for a single round."""

    pairings: List[Tuple[Player, Player]]
    bye_player: Optional[Player]
    pairing_ids: List[Tuple[str, str]]
    bye_player_id: Optional[str]
