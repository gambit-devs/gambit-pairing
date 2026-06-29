"""Tournament document persistence workflow.

This module intentionally stays free of Qt imports. GUI code can own file
dialogs and user prompts, while this service owns conversion between the
application's runtime tournament state and the representation document.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from gambitpairing.representation import (
    load_tournament_document,
    save_tournament_document,
)


@dataclass
class TournamentGuiState:
    """Small persisted UI state needed to restore an open tournament."""

    current_round_index: int = 0
    last_recorded_results_data: List[list[Any] | tuple[Any, ...]] = field(
        default_factory=list
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_round_index": self.current_round_index,
            "last_recorded_results_data": self.last_recorded_results_data,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any] | None) -> "TournamentGuiState":
        if not data:
            return cls()
        return cls(
            current_round_index=int(data.get("current_round_index", 0)),
            last_recorded_results_data=list(
                data.get("last_recorded_results_data", [])
            ),
        )


@dataclass
class LoadedTournamentDocument:
    """Result of loading a tournament document."""

    tournament: Any
    gui_state: TournamentGuiState


class TournamentPersistenceService:
    """Save and load tournament documents through the representation layer."""

    def save(
        self,
        path: str | Path,
        tournament: Any,
        gui_state: TournamentGuiState,
    ) -> None:
        save_tournament_document(path, tournament, gui_state.to_dict())

    def load(self, path: str | Path) -> LoadedTournamentDocument:
        tournament, gui_state_data = load_tournament_document(path)
        return LoadedTournamentDocument(
            tournament=tournament,
            gui_state=TournamentGuiState.from_dict(gui_state_data),
        )
