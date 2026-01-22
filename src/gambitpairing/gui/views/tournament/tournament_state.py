# Gambit Pairing
# Copyright (C) 2025  Gambit Pairing developers
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Tournament state management.

This module provides data structures for tracking and computing tournament state,
including what actions are available at any given point in the tournament lifecycle.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from gambitpairing.tournament import Tournament


class TournamentPhase(Enum):
    """
    Represents the current phase of a tournament.

    Used to determine which UI elements and actions should be available.
    """

    NO_TOURNAMENT = auto()  # No tournament loaded
    NOT_STARTED = auto()  # Tournament exists but hasn't started
    AWAITING_RESULTS = auto()  # Pairings generated, waiting for results
    AWAITING_NEXT_ROUND = auto()  # Results recorded, ready for next round
    FINISHED = auto()  # All rounds completed


@dataclass
class TournamentState:
    """
    Encapsulates the computed state of a tournament.

    This class centralizes all state calculations to avoid duplicating
    this logic throughout the UI code. It determines what actions are
    currently available based on tournament progress.

    Attributes
    ----------
    tournament_exists : bool
        Whether a tournament object is loaded
    tournament_started : bool
        Whether pairings have been generated for at least one round
    tournament_finished : bool
        Whether all rounds have been completed
    pairings_generated : int
        Number of rounds that have pairings generated
    results_recorded : int
        Number of rounds with recorded results (current_round_index)
    total_rounds : int
        Total number of rounds in the tournament
    num_players : int
        Number of players in the tournament
    phase : TournamentPhase
        Current phase of the tournament
    can_start : bool
        Whether the tournament can be started
    can_prepare : bool
        Whether the next round can be prepared
    can_record : bool
        Whether results can be recorded for the current round
    can_undo : bool
        Whether the last round's results can be undone
    has_pairings : bool
        Whether current round has pairings to display
    """

    tournament_exists: bool
    tournament_started: bool
    tournament_finished: bool
    pairings_generated: int
    results_recorded: int
    total_rounds: int
    num_players: int
    phase: TournamentPhase
    can_start: bool
    can_prepare: bool
    can_record: bool
    can_undo: bool
    has_pairings: bool

    @classmethod
    def compute(
        cls, tournament: Optional["Tournament"], current_round_index: int
    ) -> "TournamentState":
        """
        Compute the current tournament state.

        Parameters
        ----------
        tournament : Tournament or None
            The tournament object, or None if no tournament is loaded
        current_round_index : int
            The current round index (0-based, represents next round to play)

        Returns
        -------
        TournamentState
            The computed state object with all derived properties
        """
        tournament_exists = tournament is not None

        if not tournament_exists:
            return cls(
                tournament_exists=False,
                tournament_started=False,
                tournament_finished=False,
                pairings_generated=0,
                results_recorded=0,
                total_rounds=0,
                num_players=0,
                phase=TournamentPhase.NO_TOURNAMENT,
                can_start=False,
                can_prepare=False,
                can_record=False,
                can_undo=False,
                has_pairings=False,
            )

        pairings_generated = len(tournament.rounds_pairings_ids)
        results_recorded = current_round_index
        total_rounds = tournament.num_rounds
        num_players = len(tournament.players)
        tournament_started = pairings_generated > 0
        tournament_finished = results_recorded >= total_rounds and total_rounds > 0

        # Determine phase
        if tournament_finished:
            phase = TournamentPhase.FINISHED
        elif not tournament_started:
            phase = TournamentPhase.NOT_STARTED
        elif pairings_generated > results_recorded:
            phase = TournamentPhase.AWAITING_RESULTS
        else:
            phase = TournamentPhase.AWAITING_NEXT_ROUND

        # Determine available actions
        can_start = not tournament_started
        can_prepare = (
            tournament_started
            and pairings_generated == results_recorded
            and pairings_generated < total_rounds
        )
        can_record = tournament_started and pairings_generated > results_recorded
        can_undo = results_recorded > 0

        # Check if current round has pairings
        has_pairings = (
            current_round_index < len(tournament.rounds_pairings_ids)
            and len(tournament.rounds_pairings_ids[current_round_index]) > 0
        )

        return cls(
            tournament_exists=tournament_exists,
            tournament_started=tournament_started,
            tournament_finished=tournament_finished,
            pairings_generated=pairings_generated,
            results_recorded=results_recorded,
            total_rounds=total_rounds,
            num_players=num_players,
            phase=phase,
            can_start=can_start,
            can_prepare=can_prepare,
            can_record=can_record,
            can_undo=can_undo,
            has_pairings=has_pairings,
        )

    @property
    def display_round_number(self) -> int:
        """Get the human-readable round number (1-based)."""
        return self.results_recorded + 1

    @property
    def status_message(self) -> str:
        """
        Get a human-readable status message for the current state.

        For the AWAITING_RESULTS state, use get_status_message() instead
        to include the number of pairings.

        Returns
        -------
        str
            A message describing what the user should do next
        """
        return self.get_status_message()

    def get_status_message(self, num_pairings: int = 0) -> str:
        """
        Get a human-readable status message for the current state.

        Parameters
        ----------
        num_pairings : int, optional
            Number of pairings in the current round (used in AWAITING_RESULTS phase)

        Returns
        -------
        str
            A message describing what the user should do next
        """
        if self.phase == TournamentPhase.NO_TOURNAMENT:
            return "No tournament loaded. Create or load a tournament to begin."
        elif self.phase == TournamentPhase.FINISHED:
            return (
                f"🏆 Tournament complete! All {self.total_rounds} rounds have been played. "
                f"View the Standings tab for final results."
            )
        elif self.phase == TournamentPhase.NOT_STARTED:
            return (
                f"Tournament ready with {self.num_players} players and {self.total_rounds} rounds. "
                f"Click 'Start Tournament' to generate Round 1 pairings."
            )
        elif self.phase == TournamentPhase.AWAITING_RESULTS:
            games_text = (
                f"all {num_pairings} game(s)" if num_pairings > 0 else "all games"
            )
            return (
                f"Round {self.display_round_number} of {self.total_rounds}: "
                f"Enter results for {games_text} below, then click 'Record Results & Advance'."
            )
        elif self.phase == TournamentPhase.AWAITING_NEXT_ROUND:
            return (
                f"Round {self.results_recorded} complete. "
                f"Click 'Prepare Next Round' to generate Round {self.display_round_number} pairings."
            )
        return ""

    @property
    def status_state(self) -> str:
        """
        Get the CSS state property value for styling.

        Returns
        -------
        str
            One of: 'default', 'ready', 'recording', 'prepare', 'finished'
        """
        if self.phase == TournamentPhase.FINISHED:
            return "finished"
        elif self.phase == TournamentPhase.NOT_STARTED:
            return "ready"
        elif self.phase == TournamentPhase.AWAITING_RESULTS:
            return "recording"
        elif self.phase == TournamentPhase.AWAITING_NEXT_ROUND:
            return "prepare"
        return "default"

    @property
    def primary_button_text(self) -> str:
        """Get the text for the primary action button."""
        if self.phase == TournamentPhase.FINISHED:
            return "✓ Tournament Complete"
        elif self.phase == TournamentPhase.NOT_STARTED:
            return "Start Tournament"
        elif self.phase == TournamentPhase.AWAITING_RESULTS:
            return "Record Results & Advance"
        elif self.phase == TournamentPhase.AWAITING_NEXT_ROUND:
            return "Prepare Next Round"
        return "No Action Available"

    @property
    def primary_button_icon_name(self) -> str:
        """Get the icon name for the primary action button."""
        if self.phase == TournamentPhase.FINISHED:
            return ""
        elif self.phase == TournamentPhase.NOT_STARTED:
            return "play.svg"
        elif self.phase == TournamentPhase.AWAITING_RESULTS:
            return "arrow-right.svg"
        elif self.phase == TournamentPhase.AWAITING_NEXT_ROUND:
            return "refresh.svg"
        return ""

    @property
    def primary_button_enabled(self) -> bool:
        """Check if the primary action button should be enabled."""
        return self.can_start or self.can_record or self.can_prepare

    @property
    def primary_button_tooltip(self) -> str:
        """Get the tooltip for the primary action button."""
        if self.phase == TournamentPhase.FINISHED:
            return "All rounds have been completed"
        elif self.phase == TournamentPhase.NOT_STARTED:
            return "Start the tournament and generate first round pairings"
        elif self.phase == TournamentPhase.AWAITING_RESULTS:
            return "Record results for all pairings and advance to next round"
        elif self.phase == TournamentPhase.AWAITING_NEXT_ROUND:
            return f"Generate pairings for Round {self.display_round_number}"
        return ""
