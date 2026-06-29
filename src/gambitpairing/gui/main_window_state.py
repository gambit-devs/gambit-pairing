"""Pure UI-state helpers for the main window."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from gambitpairing.models.tournament import Tournament


@dataclass(frozen=True)
class MainWindowUiState:
    """Derived state that ``GambitPairingMainWindow`` applies to Qt widgets."""

    tournament_exists: bool
    pairings_generated: int
    results_recorded: int
    total_rounds: int
    tournament_started: bool
    tournament_finished: bool
    can_start: bool
    can_prepare: bool
    can_record: bool
    can_undo: bool
    can_save: bool
    can_export_standings: bool
    can_import_players: bool
    can_export_players: bool
    can_add_player: bool
    can_open_settings: bool
    window_title: str
    status_message: str
    toolbar_tournament_label: str


def build_main_window_ui_state(
    *,
    tournament: Tournament | None,
    current_round_index: int,
    last_recorded_results_data: Sequence[object],
    dirty: bool,
    current_filepath: str | None,
    app_name: str,
) -> MainWindowUiState:
    """Compute MainWindow UI state without touching Qt widgets."""
    tournament_exists = tournament is not None
    pairings_generated = len(tournament.rounds_pairings_ids) if tournament else 0
    results_recorded = current_round_index
    total_rounds = tournament.num_rounds if tournament else 0
    player_count = len(tournament.players) if tournament else 0
    tournament_started = tournament_exists and pairings_generated > 0
    tournament_finished = (
        tournament_exists and results_recorded >= total_rounds and total_rounds > 0
    )

    can_start = tournament_exists and not tournament_started
    can_prepare = (
        tournament_exists
        and tournament_started
        and pairings_generated == results_recorded
        and not tournament_finished
    )
    can_record = (
        tournament_exists
        and tournament_started
        and pairings_generated > results_recorded
        and not tournament_finished
    )
    can_undo = (
        tournament_exists
        and results_recorded > 0
        and bool(last_recorded_results_data)
    )

    window_title = _build_window_title(
        tournament=tournament,
        dirty=dirty,
        current_filepath=current_filepath,
        app_name=app_name,
    )
    status_message = _build_status_message(
        tournament=tournament,
        tournament_exists=tournament_exists,
        tournament_started=tournament_started,
        tournament_finished=tournament_finished,
        can_record=can_record,
        can_prepare=can_prepare,
        results_recorded=results_recorded,
        total_rounds=total_rounds,
    )
    toolbar_tournament_label = _build_toolbar_tournament_label(
        tournament=tournament, dirty=dirty
    )

    return MainWindowUiState(
        tournament_exists=tournament_exists,
        pairings_generated=pairings_generated,
        results_recorded=results_recorded,
        total_rounds=total_rounds,
        tournament_started=tournament_started,
        tournament_finished=tournament_finished,
        can_start=can_start,
        can_prepare=can_prepare,
        can_record=can_record,
        can_undo=can_undo,
        can_save=tournament_exists,
        can_export_standings=tournament_exists and results_recorded > 0,
        can_import_players=tournament_exists and not tournament_started,
        can_export_players=tournament_exists and player_count > 0,
        can_add_player=not tournament_started,
        can_open_settings=tournament_exists,
        window_title=window_title,
        status_message=status_message,
        toolbar_tournament_label=toolbar_tournament_label,
    )


def _build_window_title(
    *,
    tournament: Tournament | None,
    dirty: bool,
    current_filepath: str | None,
    app_name: str,
) -> str:
    title = app_name
    if tournament:
        base_name = tournament.name
        if dirty:
            base_name += "*"

        if current_filepath:
            title = f"{base_name} - {_file_name(current_filepath)} - {app_name}"
        else:
            title = f"{base_name} - {app_name}"
    elif current_filepath:
        title = f"{_file_name(current_filepath)} - {app_name}"
    return title


def _build_status_message(
    *,
    tournament: Tournament | None,
    tournament_exists: bool,
    tournament_started: bool,
    tournament_finished: bool,
    can_record: bool,
    can_prepare: bool,
    results_recorded: int,
    total_rounds: int,
) -> str:
    if not tournament_exists or tournament is None:
        return "Ready - Create New or Load Tournament."

    if not tournament_started:
        return (
            f"Tournament '{tournament.name}': Add players, then Start. "
            f"{len(tournament.players)} players registered."
        )
    if can_record:
        return (
            f"Round {results_recorded + 1} pairings ready for "
            f"'{tournament.name}'. Please enter results."
        )
    if can_prepare:
        return (
            f"Round {results_recorded} results recorded for '{tournament.name}'. "
            f"Prepare Round {results_recorded + 1}."
        )
    if tournament_finished:
        return (
            f"Tournament '{tournament.name}' finished. "
            "Final standings are available."
        )
    return (
        f"Tournament '{tournament.name}' in progress. "
        f"Completed rounds: {results_recorded}/{total_rounds}."
    )


def _build_toolbar_tournament_label(
    *, tournament: Tournament | None, dirty: bool
) -> str:
    if not tournament:
        return "No Tournament Loaded"
    label = tournament.name
    if dirty:
        label += " *"
    return label


def _file_name(filepath: str) -> str:
    return Path(filepath).name
