"""Application-level controller placeholder.

The branch previously contained a recursive copy of ``__main__`` here. Keep a
small importable controller shell for code that still references the old name
while tournament behavior continues to move into dedicated controllers.
"""

from __future__ import annotations

from typing import Optional


class GampitPairingController:
    """Minimal application state coordinator used during the MVC transition."""

    def __init__(self) -> None:
        self.tournament: Optional[object] = None

    def set_tournament(self, tournament: Optional[object]) -> None:
        self.tournament = tournament
