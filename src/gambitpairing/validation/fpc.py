"""FIDE Pairing Checker (FPC) - Internal validation system for Dutch pairings.

This module provides validation of pairings against FIDE requirements as
specified in the FIDE Handbook C.04.3 (effective from 1 February 2026).
"""

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

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterable, List, Optional, Set, Tuple

from gambitpairing.constants import BYE_SCORE, DRAW_SCORE, LOSS_SCORE, WIN_SCORE
from gambitpairing.player import Player
from gambitpairing.type_hints import BLACK, WHITE
from gambitpairing.utils import setup_logger

logger = setup_logger(__name__)

PairingList = List[Tuple[Player, Player]]
Pairings = PairingList


class CriterionStatus(Enum):
    """Status of FIDE criterion validation."""

    COMPLIANT = "COMPLIANT"
    VIOLATION = "VIOLATION"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ViolationType(Enum):
    """Types of FIDE criterion violations."""

    ABSOLUTE = "ABSOLUTE"  # C1-C3: Must not violate
    QUALITY = "QUALITY"  # C4-C21: Should minimize
    WARNING = "WARNING"  # Non-critical issues


class FloatDirection(Enum):
    """Float direction for previous rounds."""

    FLOAT_DOWN = "DOWN"
    FLOAT_UP = "UP"
    FLOAT_NONE = "NONE"


@dataclass
class CriterionResult:
    """Result of validating a single FIDE criterion."""

    criterion: str
    status: CriterionStatus
    violation_type: Optional[ViolationType] = None
    description: str = ""
    details: Dict[str, object] = field(default_factory=dict)

    def __post_init__(self):
        if self.details is None:
            self.details = {}

    @property
    def criterion_id(self) -> str:
        """Extract criterion ID from criterion string."""
        return self.criterion.split(":")[0].strip()

    @property
    def message(self) -> str:
        """Get the violation message."""
        return self.description


@dataclass
class ValidationReport:
    """Complete validation report for pairings."""

    total_criteria: int
    compliant_count: int
    violations: List[CriterionResult]
    overall_status: CriterionStatus
    summary: str
    quality_warnings: List[CriterionResult] = field(default_factory=list)
    criteria_results: List[CriterionResult] = field(default_factory=list)

    @property
    def compliance_percentage(self) -> float:
        """Calculate compliance percentage."""
        if self.total_criteria == 0:
            return 100.0
        return (self.compliant_count / self.total_criteria) * 100.0


@dataclass
class RoundContext:
    """Precomputed round context for quality criteria evaluation."""

    pairings: PairingList
    bye_player: Optional[Player]
    players: List[Player]
    current_round: int
    total_rounds: int
    previous_matches: Set[frozenset]
    assigned_colors: Dict[str, Optional[str]]
    downfloaters: List[Player]
    upfloaters: List[Player]
    mdp_opponents: List[Player]
    eligible_bye_players: List[Player]


def _color_history(player: Player) -> List[str]:
    return [c for c in getattr(player, "color_history", []) if c is not None]


def _color_difference(player: Player, assigned_color: Optional[str] = None) -> int:
    history = _color_history(player)
    if assigned_color:
        history.append(assigned_color)
    white_games = history.count(WHITE)
    black_games = history.count(BLACK)
    return white_games - black_games


def _has_three_consecutive_colors(
    player: Player, assigned_color: Optional[str] = None
) -> bool:
    history = _color_history(player)
    if assigned_color:
        history.append(assigned_color)
    if len(history) < 3:
        return False
    last_three = history[-3:]
    return all(color == last_three[0] for color in last_three)


def _get_color_preference(player: Player) -> Optional[str]:
    history = _color_history(player)
    if not history:
        return None
    white_games = history.count(WHITE)
    black_games = history.count(BLACK)
    color_diff = white_games - black_games

    if color_diff > 1:
        return BLACK
    if color_diff < -1:
        return WHITE

    if len(history) >= 2 and history[-1] == history[-2]:
        return BLACK if history[-1] == WHITE else WHITE

    if color_diff == 1:
        return BLACK
    if color_diff == -1:
        return WHITE

    last_color = history[-1]
    return BLACK if last_color == WHITE else WHITE


def _has_absolute_preference(player: Player) -> bool:
    history = _color_history(player)
    if not history:
        return False
    color_diff = history.count(WHITE) - history.count(BLACK)
    if abs(color_diff) > 1:
        return True
    return len(history) >= 2 and history[-1] == history[-2]


def _has_strong_preference(player: Player) -> bool:
    if _has_absolute_preference(player):
        return False
    history = _color_history(player)
    if not history:
        return False
    color_diff = history.count(WHITE) - history.count(BLACK)
    return abs(color_diff) == 1


def _has_mild_preference(player: Player) -> bool:
    if _has_absolute_preference(player) or _has_strong_preference(player):
        return False
    return bool(_color_history(player))


def _is_topscorer(player: Player, current_round: int, total_rounds: int) -> bool:
    if current_round != total_rounds or total_rounds <= 0:
        return False
    max_possible_score = current_round - 1
    return player.score > (max_possible_score * 0.5)


def _count_played_games(player: Player) -> int:
    return len([opp_id for opp_id in getattr(player, "opponent_ids", []) if opp_id])


def _has_full_point_bye(player: Player) -> bool:
    for opponent_id, result in zip(player.opponent_ids, player.results):
        if opponent_id is None and result is not None and result >= WIN_SCORE:
            return True
    return False


def _float_type(player: Player, rounds_back: int, current_round: int) -> FloatDirection:
    if rounds_back >= current_round or rounds_back < 1:
        return FloatDirection.FLOAT_NONE

    match_index = current_round - rounds_back - 1
    if match_index < 0 or match_index >= len(player.match_history):
        return FloatDirection.FLOAT_NONE

    match_info = player.match_history[match_index]
    if not match_info or not match_info.get("opponent_id"):
        result = None
        if match_index < len(player.results):
            result = player.results[match_index]
        if result is not None and result > 0:
            return FloatDirection.FLOAT_DOWN
        return FloatDirection.FLOAT_NONE

    player_score = match_info.get("player_score") or 0.0
    opponent_score = match_info.get("opponent_score") or 0.0
    if player_score > opponent_score:
        return FloatDirection.FLOAT_DOWN
    if player_score < opponent_score:
        return FloatDirection.FLOAT_UP
    return FloatDirection.FLOAT_NONE


def _assigned_color_map(
    pairings: Pairings, bye_player: Optional[Player]
) -> Dict[str, Optional[str]]:
    assigned: Dict[str, Optional[str]] = {white.id: WHITE for white, _ in pairings}
    assigned.update({black.id: BLACK for _, black in pairings})
    if bye_player is not None:
        assigned[bye_player.id] = None
    return assigned


def _identify_floaters(
    pairings: Pairings, bye_player: Optional[Player]
) -> Tuple[List[Player], List[Player], List[Player]]:
    downfloaters: List[Player] = []
    upfloaters: List[Player] = []
    mdp_opponents: List[Player] = []

    for white, black in pairings:
        if white.score > black.score:
            downfloaters.append(white)
            upfloaters.append(black)
            mdp_opponents.append(black)
        elif black.score > white.score:
            downfloaters.append(black)
            upfloaters.append(white)
            mdp_opponents.append(white)

    if bye_player is not None:
        downfloaters.append(bye_player)

    return downfloaters, upfloaters, mdp_opponents


def _eligible_for_bye(player: Player) -> bool:
    return not getattr(player, "has_received_bye", False) and not _has_full_point_bye(
        player
    )


class AbsoluteCriteriaChecker:
    """Validates FIDE absolute criteria (C1-C3)."""

    def check_c1_no_repeats(
        self, pairings: Pairings, previous_matches: Set[frozenset]
    ) -> CriterionResult:
        """C1: Players shall not play against each other more than once."""
        for white, black in pairings:
            match_id = frozenset({white.id, black.id})
            if match_id in previous_matches:
                return CriterionResult(
                    criterion="C1",
                    status=CriterionStatus.VIOLATION,
                    violation_type=ViolationType.ABSOLUTE,
                    description=f"Repeat pairing: {white.name} vs {black.name}",
                    details={"players": [white.id, black.id]},
                )
        return CriterionResult(
            criterion="C1",
            status=CriterionStatus.COMPLIANT,
            description="No repeat pairings found",
        )

    def check_c2_no_repeat_bye(
        self,
        bye_player: Optional[Player],
        player_bye_history: Dict[str, int],
    ) -> CriterionResult:
        """C2: No repeat bye assignment."""
        if bye_player is None:
            return CriterionResult(
                criterion="C2",
                status=CriterionStatus.NOT_APPLICABLE,
                description="No bye assigned in this round",
            )

        bye_count = player_bye_history.get(bye_player.id, 0)
        if bye_count > 0 or _has_full_point_bye(bye_player):
            return CriterionResult(
                criterion="C2",
                status=CriterionStatus.VIOLATION,
                violation_type=ViolationType.ABSOLUTE,
                description=f"Repeat bye: {bye_player.name}",
                details={"player_id": bye_player.id, "bye_count": bye_count},
            )

        return CriterionResult(
            criterion="C2",
            status=CriterionStatus.COMPLIANT,
            description=f"Bye assignment valid: {bye_player.name}",
        )

    def check_c3_no_absolute_preference_conflicts(
        self, pairings: Pairings, current_round: int, total_rounds: int
    ) -> CriterionResult:
        """C3: Non-topscorers with same absolute preference shall not meet."""
        if current_round != total_rounds:
            return CriterionResult(
                criterion="C3",
                status=CriterionStatus.NOT_APPLICABLE,
                description="C3 only applies in final round",
            )

        violations = []
        for white, black in pairings:
            if _is_topscorer(white, current_round, total_rounds) or _is_topscorer(
                black, current_round, total_rounds
            ):
                continue

            if _has_absolute_preference(white) and _has_absolute_preference(black):
                white_pref = _get_color_preference(white)
                black_pref = _get_color_preference(black)
                if white_pref and white_pref == black_pref:
                    violations.append(
                        {
                            "players": [white.name, black.name],
                            "preference": white_pref,
                        }
                    )

        if violations:
            return CriterionResult(
                criterion="C3",
                status=CriterionStatus.VIOLATION,
                violation_type=ViolationType.ABSOLUTE,
                description=f"Absolute preference conflicts found: {len(violations)}",
                details={"violations": violations},
            )

        return CriterionResult(
            criterion="C3",
            status=CriterionStatus.COMPLIANT,
            description="No absolute preference conflicts",
        )


class QualityCriteriaChecker:
    """Validates FIDE quality criteria (C4-C21)."""

    def check_all_quality_criteria(
        self,
        pairings: Pairings,
        bye_player: Optional[Player],
        players: List[Player],
        current_round: int,
        total_rounds: int,
        previous_matches: Set[frozenset],
    ) -> List[CriterionResult]:
        """Check all quality criteria C4-C21."""
        context = self._build_context(
            pairings,
            bye_player,
            players,
            current_round,
            total_rounds,
            previous_matches,
        )

        results = [
            self._check_c4_completion(context),
            self._check_c5_bye_score(context),
            self._check_c6_downfloaters(context),
            self._check_c7_downfloater_scores(context),
            self._check_c8_next_bracket_compatibility(context),
            self._check_c9_bye_unplayed_games(context),
        ]

        if current_round == total_rounds and total_rounds:
            results.extend(
                [
                    self._check_c10_topscorer_color_diff(context),
                    self._check_c11_topscorer_consecutive_colors(context),
                ]
            )

        results.extend(
            [
                self._check_c12_color_preferences(context),
                self._check_c13_strong_preferences(context),
            ]
        )

        if current_round >= 2:
            results.extend(
                [
                    self._check_c14_repeat_downfloaters(context),
                    self._check_c15_repeat_upfloaters(context),
                ]
            )
        if current_round >= 3:
            results.extend(
                [
                    self._check_c16_two_round_back_downfloaters(context),
                    self._check_c17_two_round_back_upfloaters(context),
                ]
            )
        if current_round >= 2:
            results.extend(
                [
                    self._check_c18_repeat_downfloater_scores(context),
                    self._check_c19_repeat_upfloater_scores(context),
                ]
            )
        if current_round >= 3:
            results.extend(
                [
                    self._check_c20_two_back_downfloater_scores(context),
                    self._check_c21_two_back_upfloater_scores(context),
                ]
            )

        return results

    def _build_context(
        self,
        pairings: Pairings,
        bye_player: Optional[Player],
        players: List[Player],
        current_round: int,
        total_rounds: int,
        previous_matches: Set[frozenset],
    ) -> RoundContext:
        assigned_colors = _assigned_color_map(pairings, bye_player)
        downfloaters, upfloaters, mdp_opponents = _identify_floaters(
            pairings, bye_player
        )
        eligible_bye_players = [p for p in players if _eligible_for_bye(p)]
        return RoundContext(
            pairings=pairings,
            bye_player=bye_player,
            players=players,
            current_round=current_round,
            total_rounds=total_rounds,
            previous_matches=previous_matches,
            assigned_colors=assigned_colors,
            downfloaters=downfloaters,
            upfloaters=upfloaters,
            mdp_opponents=mdp_opponents,
            eligible_bye_players=eligible_bye_players,
        )

    def _check_c4_completion(self, context: RoundContext) -> CriterionResult:
        """C4: A pairing complying with absolute criteria shall always exist."""
        if not context.players:
            return CriterionResult(
                criterion="C4",
                status=CriterionStatus.NOT_APPLICABLE,
                description="No players supplied for completion check",
            )

        paired_ids = set(context.assigned_colors.keys())
        missing = [
            p.name
            for p in context.players
            if getattr(p, "is_active", True) and p.id not in paired_ids
        ]

        if missing:
            # Check if this is because C1-C3 cannot be satisfied
            # If there are unpaired players with no valid opponents (all have been played),
            # this is an ABSOLUTE violation indicating C1-C3 infeasibility
            unpaired_players = [
                p
                for p in context.players
                if getattr(p, "is_active", True) and p.id not in paired_ids
            ]

            # Check if any unpaired player has available opponents
            has_unavoidable_violation = False
            for player in unpaired_players:
                # Count how many valid opponents exist
                valid_opponents = [
                    other
                    for other in context.players
                    if other.id != player.id
                    and getattr(other, "is_active", True)
                    and frozenset({player.id, other.id}) not in context.previous_matches
                ]
                # If a player has no valid opponents left, C1 cannot be satisfied
                if not valid_opponents:
                    has_unavoidable_violation = True
                    break

            violation_type = (
                ViolationType.ABSOLUTE
                if has_unavoidable_violation
                else ViolationType.QUALITY
            )

            description = (
                "Cannot create pairings without violating C1 (no repeat pairings)"
                if has_unavoidable_violation
                else "Some active players were not paired"
            )

            return CriterionResult(
                criterion="C4",
                status=CriterionStatus.VIOLATION,
                violation_type=violation_type,
                description=description,
                details={
                    "unpaired_players": missing,
                    "c1_unavoidable": has_unavoidable_violation,
                },
            )

        return CriterionResult(
            criterion="C4",
            status=CriterionStatus.COMPLIANT,
            description="All active players paired or assigned a bye",
        )

    def _check_c5_bye_score(self, context: RoundContext) -> CriterionResult:
        """C5: Minimize the score of the bye assignee."""
        if context.bye_player is None:
            return CriterionResult(
                criterion="C5",
                status=CriterionStatus.NOT_APPLICABLE,
                description="No bye assigned in this round",
            )

        eligible = context.eligible_bye_players
        if not eligible:
            return CriterionResult(
                criterion="C5",
                status=CriterionStatus.NOT_APPLICABLE,
                description="No eligible bye candidates",
            )

        min_score = min(player.score for player in eligible)
        if context.bye_player.score > min_score:
            return CriterionResult(
                criterion="C5",
                status=CriterionStatus.VIOLATION,
                violation_type=ViolationType.QUALITY,
                description="Bye assignee score not minimal",
                details={
                    "bye_player": context.bye_player.name,
                    "bye_score": context.bye_player.score,
                    "min_score": min_score,
                },
            )

        return CriterionResult(
            criterion="C5",
            status=CriterionStatus.COMPLIANT,
            description="Bye score minimized",
        )

    def _check_c6_downfloaters(self, context: RoundContext) -> CriterionResult:
        """C6: Minimize the number of downfloaters (maximize pairs)."""
        active_count = len(
            [p for p in context.players if getattr(p, "is_active", True)]
        )
        expected_pairs = active_count // 2
        actual_pairs = len(context.pairings)

        if actual_pairs < expected_pairs:
            return CriterionResult(
                criterion="C6",
                status=CriterionStatus.VIOLATION,
                violation_type=ViolationType.QUALITY,
                description="Fewer pairs than maximum possible",
                details={
                    "actual_pairs": actual_pairs,
                    "expected_pairs": expected_pairs,
                },
            )

        return CriterionResult(
            criterion="C6",
            status=CriterionStatus.COMPLIANT,
            description="Maximum number of pairs achieved",
        )

    def _check_c7_downfloater_scores(self, context: RoundContext) -> CriterionResult:
        """C7: Minimize the scores of downfloaters."""
        if not context.downfloaters:
            return CriterionResult(
                criterion="C7",
                status=CriterionStatus.NOT_APPLICABLE,
                description="No downfloaters to evaluate",
            )

        down_scores = [p.score for p in context.downfloaters]
        non_down_scores = [
            p.score
            for p in context.players
            if getattr(p, "is_active", True) and p not in context.downfloaters
        ]
        if non_down_scores and max(down_scores) > min(non_down_scores):
            return CriterionResult(
                criterion="C7",
                status=CriterionStatus.VIOLATION,
                violation_type=ViolationType.QUALITY,
                description="Higher-scoring players floated down",
                details={"downfloater_scores": down_scores},
            )

        return CriterionResult(
            criterion="C7",
            status=CriterionStatus.COMPLIANT,
            description="Downfloater scores minimized",
            details={"downfloater_scores": down_scores},
        )

    def _check_c8_next_bracket_compatibility(
        self, context: RoundContext
    ) -> CriterionResult:
        """C8: Choose downfloaters so next bracket complies with C1-C7."""
        if not context.downfloaters:
            return CriterionResult(
                criterion="C8",
                status=CriterionStatus.NOT_APPLICABLE,
                description="No downfloaters to evaluate",
            )

        incompatible = []
        for downfloater in context.downfloaters:
            candidates = [
                player
                for player in context.players
                if player.id != downfloater.id
                and player.score <= downfloater.score
                and frozenset({player.id, downfloater.id})
                not in context.previous_matches
            ]
            if not candidates:
                incompatible.append(downfloater.name)

        if incompatible:
            return CriterionResult(
                criterion="C8",
                status=CriterionStatus.VIOLATION,
                violation_type=ViolationType.QUALITY,
                description="Downfloaters lack compatible future opponents",
                details={"downfloaters": incompatible},
            )

        return CriterionResult(
            criterion="C8",
            status=CriterionStatus.COMPLIANT,
            description="Downfloaters compatible with next bracket",
        )

    def _check_c9_bye_unplayed_games(self, context: RoundContext) -> CriterionResult:
        """C9: Minimize unplayed games of bye assignee."""
        if context.bye_player is None:
            return CriterionResult(
                criterion="C9",
                status=CriterionStatus.NOT_APPLICABLE,
                description="No bye assigned in this round",
            )

        eligible = context.eligible_bye_players
        if not eligible:
            return CriterionResult(
                criterion="C9",
                status=CriterionStatus.NOT_APPLICABLE,
                description="No eligible bye candidates",
            )

        unplayed_counts = {
            player.id: (context.current_round - 1 - _count_played_games(player))
            for player in eligible
        }
        min_unplayed = min(unplayed_counts.values())
        bye_unplayed = unplayed_counts.get(context.bye_player.id, 0)
        if bye_unplayed > min_unplayed:
            return CriterionResult(
                criterion="C9",
                status=CriterionStatus.VIOLATION,
                violation_type=ViolationType.QUALITY,
                description="Bye assignee has more unplayed games than necessary",
                details={"bye_unplayed": bye_unplayed, "min_unplayed": min_unplayed},
            )

        return CriterionResult(
            criterion="C9",
            status=CriterionStatus.COMPLIANT,
            description="Bye assignee unplayed games minimized",
        )

    def _check_c10_topscorer_color_diff(self, context: RoundContext) -> CriterionResult:
        """C10: Minimize topscorers or opponents with color diff > +/-2."""
        violations = []
        for white, black in context.pairings:
            if not (
                _is_topscorer(white, context.current_round, context.total_rounds)
                or _is_topscorer(black, context.current_round, context.total_rounds)
            ):
                continue

            for player, assigned_color in (
                (white, WHITE),
                (black, BLACK),
            ):
                color_diff = _color_difference(player, assigned_color)
                if abs(color_diff) > 2:
                    violations.append({"player": player.name, "color_diff": color_diff})

        if violations:
            return CriterionResult(
                criterion="C10",
                status=CriterionStatus.VIOLATION,
                violation_type=ViolationType.QUALITY,
                description=f"Topscorer color difference issues: {len(violations)}",
                details={"violations": violations},
            )

        return CriterionResult(
            criterion="C10",
            status=CriterionStatus.COMPLIANT,
            description="No excessive topscorer color differences",
        )

    def _check_c11_topscorer_consecutive_colors(
        self, context: RoundContext
    ) -> CriterionResult:
        """C11: Minimize topscorers or opponents with same color 3x."""
        violations = []
        for white, black in context.pairings:
            if not (
                _is_topscorer(white, context.current_round, context.total_rounds)
                or _is_topscorer(black, context.current_round, context.total_rounds)
            ):
                continue

            if _has_three_consecutive_colors(white, WHITE):
                violations.append({"player": white.name, "color": WHITE})
            if _has_three_consecutive_colors(black, BLACK):
                violations.append({"player": black.name, "color": BLACK})

        if violations:
            return CriterionResult(
                criterion="C11",
                status=CriterionStatus.VIOLATION,
                violation_type=ViolationType.QUALITY,
                description=f"Consecutive color issues: {len(violations)}",
                details={"violations": violations},
            )

        return CriterionResult(
            criterion="C11",
            status=CriterionStatus.COMPLIANT,
            description="No topscorer consecutive color issues",
        )

    def _check_c12_color_preferences(self, context: RoundContext) -> CriterionResult:
        """C12: Minimize players who do not get their color preference."""
        violations = []
        for player in context.players:
            assigned = context.assigned_colors.get(player.id)
            if assigned is None:
                continue
            preference = _get_color_preference(player)
            if preference and assigned != preference:
                violations.append(
                    {"player": player.name, "expected": preference, "actual": assigned}
                )

        if violations:
            return CriterionResult(
                criterion="C12",
                status=CriterionStatus.VIOLATION,
                violation_type=ViolationType.QUALITY,
                description=f"Color preference violations: {len(violations)}",
                details={"violations": violations},
            )

        return CriterionResult(
            criterion="C12",
            status=CriterionStatus.COMPLIANT,
            description="Color preferences satisfied",
        )

    def _check_c13_strong_preferences(self, context: RoundContext) -> CriterionResult:
        """C13: Minimize players who do not get their strong preference."""
        violations = []
        for player in context.players:
            assigned = context.assigned_colors.get(player.id)
            if assigned is None:
                continue
            if _has_strong_preference(player):
                preference = _get_color_preference(player)
                if preference and assigned != preference:
                    violations.append(
                        {
                            "player": player.name,
                            "expected": preference,
                            "actual": assigned,
                        }
                    )

        if violations:
            return CriterionResult(
                criterion="C13",
                status=CriterionStatus.VIOLATION,
                violation_type=ViolationType.QUALITY,
                description=f"Strong preference violations: {len(violations)}",
                details={"violations": violations},
            )

        return CriterionResult(
            criterion="C13",
            status=CriterionStatus.COMPLIANT,
            description="Strong preferences satisfied",
        )

    def _check_c14_repeat_downfloaters(self, context: RoundContext) -> CriterionResult:
        """C14: Minimize resident downfloaters who downfloated previous round."""
        repeaters = [
            player
            for player in context.downfloaters
            if _float_type(player, 1, context.current_round)
            == FloatDirection.FLOAT_DOWN
        ]
        if repeaters:
            return CriterionResult(
                criterion="C14",
                status=CriterionStatus.VIOLATION,
                violation_type=ViolationType.QUALITY,
                description=f"Repeat downfloaters: {len(repeaters)}",
                details={"players": [p.name for p in repeaters]},
            )

        return CriterionResult(
            criterion="C14",
            status=CriterionStatus.COMPLIANT,
            description="Repeat downfloaters minimized",
        )

    def _check_c15_repeat_upfloaters(self, context: RoundContext) -> CriterionResult:
        """C15: Minimize MDP opponents who upfloated previous round."""
        repeaters = [
            player
            for player in context.mdp_opponents
            if _float_type(player, 1, context.current_round) == FloatDirection.FLOAT_UP
        ]
        if repeaters:
            return CriterionResult(
                criterion="C15",
                status=CriterionStatus.VIOLATION,
                violation_type=ViolationType.QUALITY,
                description=f"Repeat upfloaters: {len(repeaters)}",
                details={"players": [p.name for p in repeaters]},
            )

        return CriterionResult(
            criterion="C15",
            status=CriterionStatus.COMPLIANT,
            description="Repeat upfloaters minimized",
        )

    def _check_c16_two_round_back_downfloaters(
        self, context: RoundContext
    ) -> CriterionResult:
        """C16: Minimize downfloaters who downfloated two rounds before."""
        repeaters = [
            player
            for player in context.downfloaters
            if _float_type(player, 2, context.current_round)
            == FloatDirection.FLOAT_DOWN
        ]
        if repeaters:
            return CriterionResult(
                criterion="C16",
                status=CriterionStatus.VIOLATION,
                violation_type=ViolationType.QUALITY,
                description=f"Two-round back downfloaters: {len(repeaters)}",
                details={"players": [p.name for p in repeaters]},
            )

        return CriterionResult(
            criterion="C16",
            status=CriterionStatus.COMPLIANT,
            description="Two-round back downfloaters minimized",
        )

    def _check_c17_two_round_back_upfloaters(
        self, context: RoundContext
    ) -> CriterionResult:
        """C17: Minimize MDP opponents who upfloated two rounds before."""
        repeaters = [
            player
            for player in context.mdp_opponents
            if _float_type(player, 2, context.current_round) == FloatDirection.FLOAT_UP
        ]
        if repeaters:
            return CriterionResult(
                criterion="C17",
                status=CriterionStatus.VIOLATION,
                violation_type=ViolationType.QUALITY,
                description=f"Two-round back upfloaters: {len(repeaters)}",
                details={"players": [p.name for p in repeaters]},
            )

        return CriterionResult(
            criterion="C17",
            status=CriterionStatus.COMPLIANT,
            description="Two-round back upfloaters minimized",
        )

    def _check_c18_repeat_downfloater_scores(
        self, context: RoundContext
    ) -> CriterionResult:
        """C18: Minimize score differences of repeat downfloaters."""
        score_diffs = []
        for white, black in context.pairings:
            if white.score > black.score and (
                _float_type(white, 1, context.current_round)
                == FloatDirection.FLOAT_DOWN
            ):
                score_diffs.append(white.score - black.score)
            if black.score > white.score and (
                _float_type(black, 1, context.current_round)
                == FloatDirection.FLOAT_DOWN
            ):
                score_diffs.append(black.score - white.score)

        if score_diffs:
            return CriterionResult(
                criterion="C18",
                status=CriterionStatus.VIOLATION,
                violation_type=ViolationType.QUALITY,
                description="Repeat downfloater score differences detected",
                details={"score_differences": sorted(score_diffs, reverse=True)},
            )

        return CriterionResult(
            criterion="C18",
            status=CriterionStatus.COMPLIANT,
            description="Repeat downfloater score differences minimized",
        )

    def _check_c19_repeat_upfloater_scores(
        self, context: RoundContext
    ) -> CriterionResult:
        """C19: Minimize score differences of repeat upfloater opponents."""
        score_diffs = []
        for white, black in context.pairings:
            if white.score > black.score and (
                _float_type(black, 1, context.current_round) == FloatDirection.FLOAT_UP
            ):
                score_diffs.append(white.score - black.score)
            if black.score > white.score and (
                _float_type(white, 1, context.current_round) == FloatDirection.FLOAT_UP
            ):
                score_diffs.append(black.score - white.score)

        if score_diffs:
            return CriterionResult(
                criterion="C19",
                status=CriterionStatus.VIOLATION,
                violation_type=ViolationType.QUALITY,
                description="Repeat upfloater opponent score differences detected",
                details={"score_differences": sorted(score_diffs, reverse=True)},
            )

        return CriterionResult(
            criterion="C19",
            status=CriterionStatus.COMPLIANT,
            description="Repeat upfloater opponent score differences minimized",
        )

    def _check_c20_two_back_downfloater_scores(
        self, context: RoundContext
    ) -> CriterionResult:
        """C20: Minimize score differences of downfloaters two rounds back."""
        score_diffs = []
        for white, black in context.pairings:
            if white.score > black.score and (
                _float_type(white, 2, context.current_round)
                == FloatDirection.FLOAT_DOWN
            ):
                score_diffs.append(white.score - black.score)
            if black.score > white.score and (
                _float_type(black, 2, context.current_round)
                == FloatDirection.FLOAT_DOWN
            ):
                score_diffs.append(black.score - white.score)

        if score_diffs:
            return CriterionResult(
                criterion="C20",
                status=CriterionStatus.VIOLATION,
                violation_type=ViolationType.QUALITY,
                description="Two-round back downfloater score differences detected",
                details={"score_differences": sorted(score_diffs, reverse=True)},
            )

        return CriterionResult(
            criterion="C20",
            status=CriterionStatus.COMPLIANT,
            description="Two-round back downfloater score differences minimized",
        )

    def _check_c21_two_back_upfloater_scores(
        self, context: RoundContext
    ) -> CriterionResult:
        """C21: Minimize score differences of upfloater opponents two rounds back."""
        score_diffs = []
        for white, black in context.pairings:
            if white.score > black.score and (
                _float_type(black, 2, context.current_round) == FloatDirection.FLOAT_UP
            ):
                score_diffs.append(white.score - black.score)
            if black.score > white.score and (
                _float_type(white, 2, context.current_round) == FloatDirection.FLOAT_UP
            ):
                score_diffs.append(black.score - white.score)

        if score_diffs:
            return CriterionResult(
                criterion="C21",
                status=CriterionStatus.VIOLATION,
                violation_type=ViolationType.QUALITY,
                description="Two-round back upfloater opponent differences detected",
                details={"score_differences": sorted(score_diffs, reverse=True)},
            )

        return CriterionResult(
            criterion="C21",
            status=CriterionStatus.COMPLIANT,
            description="Two-round back upfloater opponent differences minimized",
        )


class FPCValidator:
    """Main FIDE Pairing Checker validator."""

    def __init__(self):
        self.absolute_checker = AbsoluteCriteriaChecker()
        self.quality_checker = QualityCriteriaChecker()

    def check_tournament_feasibility(
        self, num_players: int, num_rounds: int
    ) -> Optional[CriterionResult]:
        """Check if tournament configuration can satisfy C1 (no repeat pairings).

        With N players, there are at most C(N,2) = N*(N-1)/2 unique pairings.
        With R rounds and N players, we need R * floor(N/2) total pairings.

        If required pairings exceed unique pairings, C1 violations are inevitable.

        Returns:
            CriterionResult if configuration is infeasible, None otherwise.
        """
        if num_players < 2 or num_rounds < 1:
            return None

        max_unique_pairings = num_players * (num_players - 1) // 2
        pairings_per_round = num_players // 2
        total_pairings_needed = num_rounds * pairings_per_round

        if total_pairings_needed > max_unique_pairings:
            min_repeats = total_pairings_needed - max_unique_pairings
            return CriterionResult(
                criterion="C1",
                status=CriterionStatus.VIOLATION,
                violation_type=ViolationType.ABSOLUTE,
                description=(
                    f"Tournament configuration makes C1 compliance impossible: "
                    f"{num_players} players over {num_rounds} rounds requires "
                    f"{total_pairings_needed} pairings, but only {max_unique_pairings} "
                    f"unique pairings exist (minimum {min_repeats} repeat pairings required)"
                ),
                details={
                    "num_players": num_players,
                    "num_rounds": num_rounds,
                    "max_unique_pairings": max_unique_pairings,
                    "total_pairings_needed": total_pairings_needed,
                    "min_repeat_pairings": min_repeats,
                },
            )

        return None

    def validate_round_pairings(
        self,
        pairings: Pairings,
        bye_player: Optional[Player],
        current_round: int,
        total_rounds: int,
        previous_matches: Set[frozenset],
        player_bye_history: Dict[str, int],
        players: Optional[List[Player]] = None,
    ) -> ValidationReport:
        """Validate complete round pairings against all FIDE criteria."""
        logger.info(
            "Starting FPC validation for round %s/%s", current_round, total_rounds
        )

        active_players = players or [
            player for pairing in pairings for player in pairing
        ] + ([bye_player] if bye_player else [])
        active_players = [p for p in active_players if p is not None]

        all_results: List[CriterionResult] = []
        all_results.extend(
            [
                self.absolute_checker.check_c1_no_repeats(pairings, previous_matches),
                self.absolute_checker.check_c2_no_repeat_bye(
                    bye_player, player_bye_history
                ),
                self.absolute_checker.check_c3_no_absolute_preference_conflicts(
                    pairings, current_round, total_rounds
                ),
            ]
        )

        all_results.extend(
            self.quality_checker.check_all_quality_criteria(
                pairings,
                bye_player,
                active_players,
                current_round,
                total_rounds,
                previous_matches,
            )
        )

        compliant_count = sum(
            1 for r in all_results if r.status == CriterionStatus.COMPLIANT
        )
        total_criteria = len(all_results)
        absolute_violations = [
            r
            for r in all_results
            if r.status == CriterionStatus.VIOLATION
            and r.violation_type == ViolationType.ABSOLUTE
        ]
        quality_warnings = [
            r
            for r in all_results
            if r.status == CriterionStatus.VIOLATION
            and r.violation_type == ViolationType.QUALITY
        ]

        overall_status = (
            CriterionStatus.VIOLATION
            if absolute_violations
            else CriterionStatus.COMPLIANT
        )

        if overall_status == CriterionStatus.COMPLIANT:
            summary = (
                f"Absolute criteria satisfied; {len(quality_warnings)} "
                "quality criteria flagged"
            )
        else:
            summary = (
                f"Absolute violations detected - {len(absolute_violations)} "
                f"criteria failed; {len(quality_warnings)} quality warnings"
            )

        logger.info("FPC validation complete: %s", summary)

        return ValidationReport(
            total_criteria=total_criteria,
            compliant_count=compliant_count,
            violations=absolute_violations,
            quality_warnings=quality_warnings,
            overall_status=overall_status,
            summary=summary,
            criteria_results=all_results,
        )

    def validate_tournament_compliance(self, tournament_data: Dict) -> ValidationReport:
        """Validate entire tournament for FIDE compliance."""
        logger.info("Starting tournament-wide FIDE compliance validation")

        players = tournament_data.get("players", [])
        rounds = tournament_data.get("rounds", [])
        if not players or not rounds:
            return ValidationReport(
                total_criteria=0,
                compliant_count=0,
                violations=[],
                overall_status=CriterionStatus.NOT_APPLICABLE,
                summary="No tournament data provided for validation",
            )

        # Check tournament feasibility upfront
        num_players = len(players)
        num_rounds = tournament_data.get("config", {}).get("num_rounds", len(rounds))
        feasibility_result = self.check_tournament_feasibility(num_players, num_rounds)

        if feasibility_result:
            logger.warning(
                "Tournament configuration is infeasible: %s",
                feasibility_result.description,
            )
            return ValidationReport(
                total_criteria=1,
                compliant_count=0,
                violations=[feasibility_result],
                quality_warnings=[],
                overall_status=CriterionStatus.VIOLATION,
                summary=feasibility_result.description,
                criteria_results=[feasibility_result],
            )

        player_map: Dict[str, Player] = {}
        for player in players:
            if isinstance(player, Player):
                player_obj = Player.from_dict(player.to_dict())
            elif isinstance(player, dict):
                player_obj = Player.from_dict(player)
            else:
                continue
            player_map[player_obj.id] = player_obj
        total_criteria = 0
        compliant_count = 0
        violations: List[CriterionResult] = []
        quality_warnings: List[CriterionResult] = []
        previous_matches: Set[frozenset] = set()
        bye_history: Dict[str, int] = {}

        rounds_sorted = sorted(rounds, key=lambda r: r.get("round_number", 0))
        for round_data in rounds_sorted:
            round_number = round_data.get("round_number", 0)
            pairing_ids = round_data.get("pairings", [])
            bye_id = round_data.get("bye_player_id") or round_data.get("bye_player")
            scheduled_byes = round_data.get("scheduled_byes", {})
            scheduled_ids = set(scheduled_byes.get("half_point", [])) | set(
                scheduled_byes.get("zero_point", [])
            )

            pairings: Pairings = [
                (player_map[white_id], player_map[black_id])
                for white_id, black_id in pairing_ids
                if white_id in player_map and black_id in player_map
            ]
            bye_player = player_map.get(bye_id) if bye_id else None

            round_players = [
                player
                for player in player_map.values()
                if player.id not in scheduled_ids
            ]

            report = self.validate_round_pairings(
                pairings=pairings,
                bye_player=bye_player,
                current_round=round_number,
                total_rounds=tournament_data.get("config", {}).get(
                    "num_rounds", round_number
                ),
                previous_matches=previous_matches,
                player_bye_history=bye_history,
                players=round_players,
            )

            total_criteria += report.total_criteria
            compliant_count += report.compliant_count
            for violation in report.violations:
                violation.details["round"] = round_number
                violations.append(violation)
            for warning in report.quality_warnings:
                warning.details["round"] = round_number
                quality_warnings.append(warning)

            for white, black in pairings:
                previous_matches.add(frozenset({white.id, black.id}))

            if bye_player:
                bye_history[bye_player.id] = bye_history.get(bye_player.id, 0) + 1

            results = round_data.get("results", [])
            for result in results:
                if isinstance(result, dict):
                    white_id = result.get("white_id")
                    black_id = result.get("black_id")
                    white_score = result.get("white_score")
                else:
                    white_id, black_id, white_score = result[:3]
                if white_score is None:
                    continue
                white_score = float(white_score)
                if white_id in player_map and black_id in player_map:
                    white_player = player_map[white_id]
                    black_player = player_map[black_id]
                    white_player.add_round_result(black_player, white_score, WHITE)
                    black_player.add_round_result(
                        white_player, 1.0 - white_score, BLACK
                    )

            if bye_player and round_number > len(bye_player.results):
                bye_player.add_round_result(None, BYE_SCORE, None)

            for player_id in scheduled_byes.get("half_point", []):
                player = player_map.get(player_id)
                if player and round_number > len(player.results):
                    player.add_round_result(None, DRAW_SCORE, None)

            for player_id in scheduled_byes.get("zero_point", []):
                player = player_map.get(player_id)
                if player and round_number > len(player.results):
                    player.add_round_result(None, LOSS_SCORE, None)

        overall_status = (
            CriterionStatus.VIOLATION if violations else CriterionStatus.COMPLIANT
        )

        # Check if there are C4 absolute violations (indicating C1-C3 impossibility)
        c4_absolute_violations = [
            v
            for v in violations
            if v.criterion_id == "C4" and v.violation_type == ViolationType.ABSOLUTE
        ]

        if total_criteria:
            if violations or quality_warnings:
                violation_ids = [v.criterion_id for v in violations]
                warning_ids = [w.criterion_id for w in quality_warnings]
                all_ids = violation_ids + warning_ids

                # Add special note if C4 absolute violations indicate C1-C3 impossibility
                c4_note = ""
                if c4_absolute_violations:
                    c4_note = " (C4 violations indicate C1-C3 cannot be satisfied)"

                summary = (
                    f"Tournament validation complete - {len(violations)} "
                    f"absolute violations, {len(quality_warnings)} quality warnings "
                    f"({' '.join(all_ids)}){c4_note}"
                )
            else:
                summary = "Tournament validation complete"
        else:
            summary = "Tournament validation complete"

        return ValidationReport(
            total_criteria=total_criteria,
            compliant_count=compliant_count,
            violations=violations,
            quality_warnings=quality_warnings,
            overall_status=overall_status,
            summary=summary,
            criteria_results=[],
        )


def create_fpc_validator() -> FPCValidator:
    """Create and configure FPC validator instance."""
    return FPCValidator()


def validate_pairings_fide_compliant(pairings: Pairings, **kwargs) -> ValidationReport:
    """Quick validation function for FIDE compliance."""
    validator = create_fpc_validator()
    return validator.validate_round_pairings(pairings, **kwargs)
