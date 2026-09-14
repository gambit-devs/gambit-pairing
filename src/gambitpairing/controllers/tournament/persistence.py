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
    """Persisted UI state needed to restore an open tournament."""

    current_round_index: int = 0
    last_recorded_results_data: List[list[Any] | tuple[Any, ...]] = field(
        default_factory=list
    )
    history_log: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_round_index": self.current_round_index,
            "last_recorded_results_data": self.last_recorded_results_data,
            "history_log": self.history_log,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any] | None) -> "TournamentGuiState":
        if data is None:
            return cls()
        if not isinstance(data, dict):
            raise ValueError("GUI state must be an object")
        current_round_index = data.get("current_round_index", 0)
        if (
            not isinstance(current_round_index, int)
            or isinstance(current_round_index, bool)
            or current_round_index < 0
        ):
            raise ValueError("GUI current_round_index must be a non-negative integer")
        results_data = data.get("last_recorded_results_data", [])
        if not isinstance(results_data, list):
            raise ValueError("GUI last_recorded_results_data must be a list")
        history_log = data.get("history_log", [])
        if not isinstance(history_log, list) or not all(
            isinstance(message, str) for message in history_log
        ):
            raise ValueError("GUI history_log must be a list of strings")
        return cls(
            current_round_index=current_round_index,
            last_recorded_results_data=list(results_data),
            history_log=list(history_log),
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
        # Legacy GUI progress is a cache, never the authority for domain state.
        gui_state_data["current_round_index"] = tournament.get_completed_rounds()
        completed = [item for item in tournament.rounds if item.is_completed]
        gui_state_data["last_recorded_results_data"] = [
            (
                item.white_id,
                item.black_id,
                item.white_score,
                item.black_score,
                item.outcome_type,
            )
            for item in (completed[-1].results if completed else [])
        ]
        return LoadedTournamentDocument(
            tournament=tournament,
            gui_state=TournamentGuiState.from_dict(gui_state_data),
        )
