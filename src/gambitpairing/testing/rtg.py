"""Random Tournament Generator (RTG) - Internal testing system for FIDE Dutch pairings.

This module generates realistic tournaments for validating the Dutch system engine.
It models BBP Pairings behavior and FIDE handbook requirements.
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

import argparse
import math
import random
import tempfile
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from gambitpairing.compatibility.bbp import (
    build_bbp_pairing_trf,
    parse_bbp_pairing_output,
)
from gambitpairing.constants import BYE_SCORE, DRAW_SCORE, LOSS_SCORE, WIN_SCORE
from gambitpairing.pairing.dutch_swiss import create_dutch_swiss_pairings
from gambitpairing.player import Player
from gambitpairing.tournament.models import PairingHistory
from gambitpairing.type_hints import BLACK, WHITE
from gambitpairing.utils import setup_logger
from gambitpairing.utils.command_runner import check_command_exists, run_command
from gambitpairing.validation.fpc import create_fpc_validator

logger = setup_logger(__name__)


class RatingDistribution(Enum):
    """Rating distribution patterns for realistic tournaments."""

    UNIFORM = "uniform"
    NORMAL = "normal"
    SKEWED = "skewed"
    ELITE = "elite"
    CLUB = "club"
    FIDE = "fide"


class ResultPattern(Enum):
    """Result generation patterns for tournaments."""

    REALISTIC = "realistic"
    BALANCED = "balanced"
    UPSET_FRIENDLY = "upset_friendly"
    PREDICTABLE = "predictable"
    RANDOM = "random"


@dataclass
class RTGConfig:
    """Configuration for Random Tournament Generator."""

    num_players: int
    num_rounds: int
    rating_distribution: RatingDistribution = RatingDistribution.NORMAL
    rating_range: Tuple[int, int] = (800, 2800)
    result_pattern: ResultPattern = ResultPattern.REALISTIC
    seed: Optional[int] = None
    federation_bias: Optional[str] = None
    point_system: str = "standard"
    acceleration: bool = False
    initial_color: Optional[str] = None
    forfeit_rate: float = 20.0
    retired_rate: float = 1000.0
    half_point_bye_rate: float = 1000.0
    draw_percentage: int = 30
    pairing_system: str = "dutch_swiss"
    bbp_executable: Optional[str] = None
    bbp_initial_color: str = "white1"
    bbp_workdir: Optional[str] = None
    bbp_keep_files: bool = False
    validate_with_fpc: bool = True
    fide_strict: bool = False


@dataclass
class ByeSchedule:
    """Scheduled non-pairing byes for players."""

    zero_point_byes: Dict[str, List[int]] = field(default_factory=dict)
    half_point_byes: Dict[str, List[int]] = field(default_factory=dict)


class PlayerFactory:
    """Factory for creating realistic tournament players."""

    def __init__(self, config: RTGConfig):
        self.config = config
        self.random = (
            random.Random(config.seed) if config.seed is not None else random.Random()
        )

    def create_players(self) -> List[Player]:
        """Create players based on configuration."""
        players = []

        for i in range(self.config.num_players):
            rating = self._generate_rating()
            name = self._generate_name(i + 1, rating)
            player = Player(
                name=name,
                rating=rating,
                date_of_birth=self._generate_birth_year(rating),
            )
            player.pairing_number = i + 1
            players.append(player)

        logger.info(
            "Created %s players with %s distribution",
            len(players),
            self.config.rating_distribution.value,
        )
        return players

    def _generate_rating(self) -> int:
        min_rating, max_rating = self.config.rating_range
        if self.config.rating_distribution == RatingDistribution.UNIFORM:
            return self.random.randint(min_rating, max_rating)
        if self.config.rating_distribution == RatingDistribution.NORMAL:
            mean = (min_rating + max_rating) / 2
            std_dev = (max_rating - min_rating) / 6
            rating = int(self.random.gauss(mean, std_dev))
            return max(min_rating, min(max_rating, rating))
        if self.config.rating_distribution == RatingDistribution.SKEWED:
            if self.random.random() < 0.7:
                return self.random.randint(min_rating, (min_rating + max_rating) // 2)
            return self.random.randint((min_rating + max_rating) // 2, max_rating)
        if self.config.rating_distribution == RatingDistribution.ELITE:
            if self.random.random() < 0.1:
                return self.random.randint(max_rating - 200, max_rating)
            return self.random.randint(min_rating, max_rating - 200)
        if self.config.rating_distribution == RatingDistribution.CLUB:
            base_ratings = [1000, 1200, 1400, 1600, 1800]
            base = self.random.choice(base_ratings)
            return self.random.randint(base - 100, base + 100)
        if self.config.rating_distribution == RatingDistribution.FIDE:
            fide_bands = [
                (1000, 1200, 0.3),
                (1201, 1400, 0.4),
                (1401, 1600, 0.2),
                (1601, 2800, 0.1),
            ]
            band = self.random.choices(
                fide_bands, weights=[band[2] for band in fide_bands]
            )[0]
            return self.random.randint(band[0], band[1])
        return self.random.randint(min_rating, max_rating)

    def _generate_name(self, number: int, rating: int) -> str:
        if self.config.federation_bias:
            return f"{self.config.federation_bias}-{number:03d}"
        if rating < 1200:
            prefix = "Novice"
        elif rating < 1400:
            prefix = "ClassC"
        elif rating < 1600:
            prefix = "ClassB"
        elif rating < 1800:
            prefix = "ClassA"
        else:
            prefix = "Expert"
        return f"{prefix}-{number:03d}"

    def _generate_birth_year(self, rating: int) -> Optional[date]:
        if rating > 2000:
            year = self.random.choice([1995, 1998, 2000, 2002, 2005])
        elif rating > 1600:
            year = self.random.choice([1990, 1992, 1994, 1996, 1998])
        else:
            year = self.random.choice([1970, 1975, 1980, 1985, 1990])
        return date(year, 1, 1)


class ResultSimulator:
    """Simulates realistic game results for tournaments."""

    def __init__(self, config: RTGConfig):
        self.config = config
        self.random = (
            random.Random(config.seed) if config.seed is not None else random.Random()
        )

    def simulate_pairing_result(
        self, white: Player, black: Player, round_number: int
    ) -> Tuple[float, float, bool]:
        """Return white score, black score, and forfeit flag."""
        white_forfeit = self._forfeit_occurs()
        black_forfeit = self._forfeit_occurs()
        if white_forfeit or black_forfeit:
            if white_forfeit and black_forfeit:
                return LOSS_SCORE, LOSS_SCORE, True
            if white_forfeit:
                return LOSS_SCORE, WIN_SCORE, True
            return WIN_SCORE, LOSS_SCORE, True

        if self.config.result_pattern == ResultPattern.RANDOM:
            white_score = self.random.choice([WIN_SCORE, DRAW_SCORE, LOSS_SCORE])
            return white_score, WIN_SCORE - white_score, False

        if self.config.result_pattern == ResultPattern.BALANCED:
            white_score = self._balanced_result(white, black)
            return white_score, WIN_SCORE - white_score, False
        if self.config.result_pattern == ResultPattern.UPSET_FRIENDLY:
            white_score = self._upset_friendly_result(white, black)
            return white_score, WIN_SCORE - white_score, False
        if self.config.result_pattern == ResultPattern.PREDICTABLE:
            white_score = self._predictable_result(white, black)
            return white_score, WIN_SCORE - white_score, False
        white_score = self._bbp_realistic_result(white, black)
        return white_score, WIN_SCORE - white_score, False

    def _forfeit_occurs(self) -> bool:
        if self.config.forfeit_rate <= 1:
            return False
        non_forfeit_probability = math.sqrt(1.0 - 1.0 / self.config.forfeit_rate)
        return self.random.random() >= non_forfeit_probability

    def _bbp_realistic_result(self, white: Player, black: Player) -> float:
        if white.rating == black.rating:
            stronger_color = WHITE
        else:
            stronger_color = WHITE if white.rating > black.rating else BLACK

        rating_diff = abs(white.rating - black.rating)
        expected_value = math.erfc(rating_diff * (-7.0 / math.sqrt(2.0) / 2000.0)) / 2.0
        draw_probability = min(
            self.config.draw_percentage / 100.0, 2.0 - expected_value * 2.0
        )

        random_value = self.random.random()
        if random_value < draw_probability:
            return DRAW_SCORE

        threshold = expected_value + draw_probability / 2.0
        white_wins = random_value < threshold
        if stronger_color == BLACK:
            white_wins = not white_wins
        return WIN_SCORE if white_wins else LOSS_SCORE

    def _balanced_result(self, white: Player, black: Player) -> float:
        rating_diff = white.rating - black.rating
        win_prob = max(0.05, min(0.95, 0.5 + rating_diff / 1000))
        draw_prob = 0.1
        total_prob = win_prob + draw_prob
        win_prob /= total_prob
        draw_prob /= total_prob
        rand = self.random.random()
        if rand < win_prob:
            return WIN_SCORE
        if rand < win_prob + draw_prob:
            return DRAW_SCORE
        return LOSS_SCORE

    def _upset_friendly_result(self, white: Player, black: Player) -> float:
        rating_diff = white.rating - black.rating
        win_prob = max(0.05, min(0.95, 0.5 - rating_diff / 1000))
        draw_prob = 0.15
        total_prob = win_prob + draw_prob
        win_prob /= total_prob
        draw_prob /= total_prob
        rand = self.random.random()
        if rand < win_prob:
            return WIN_SCORE
        if rand < win_prob + draw_prob:
            return DRAW_SCORE
        return LOSS_SCORE

    def _predictable_result(self, white: Player, black: Player) -> float:
        rating_diff = white.rating - black.rating
        win_prob = min(0.95, 0.5 + rating_diff / 200)
        draw_prob = 0.05
        total_prob = win_prob + draw_prob
        win_prob /= total_prob
        draw_prob /= total_prob
        rand = self.random.random()
        if rand < win_prob:
            return WIN_SCORE
        if rand < win_prob + draw_prob:
            return DRAW_SCORE
        return LOSS_SCORE


class BBPPairingEngine:
    """Adapter for running BBP Pairings on RTG state."""

    def __init__(self, config: RTGConfig):
        self.config = config
        self.executable = self._resolve_executable(config.bbp_executable)

    def _resolve_executable(self, executable: Optional[str]) -> str:
        if not executable:
            raise ValueError("BBP executable is required for BBP pairing runs")
        exe_path = Path(executable)
        if exe_path.exists():
            return str(exe_path)
        if check_command_exists(executable):
            return executable
        raise FileNotFoundError(f"BBP executable not found: {executable}")

    def generate_pairings(
        self,
        players: List[Player],
        current_round: int,
        total_rounds: int,
    ) -> Tuple[List[Tuple[Player, Player]], Optional[Player]]:
        trf_content = build_bbp_pairing_trf(
            players,
            total_rounds=total_rounds,
            current_round=current_round,
            initial_color=self.config.bbp_initial_color,
        )

        workdir = Path(self.config.bbp_workdir) if self.config.bbp_workdir else None
        if self.config.bbp_keep_files and workdir:
            workdir.mkdir(parents=True, exist_ok=True)
            return self._run_bbp_pairings(trf_content, players, workdir, current_round)

        with tempfile.TemporaryDirectory() as temp_dir:
            return self._run_bbp_pairings(
                trf_content,
                players,
                Path(temp_dir),
                current_round,
            )

    def _run_bbp_pairings(
        self,
        trf_content: str,
        players: List[Player],
        workdir: Path,
        current_round: int,
    ) -> Tuple[List[Tuple[Player, Player]], Optional[Player]]:
        input_path = workdir / f"bbp_round_{current_round:02d}.trf"
        output_path = workdir / f"bbp_round_{current_round:02d}.out"
        input_path.write_text(trf_content, encoding="utf-8")

        cmd = [
            self.executable,
            "--dutch",
            str(input_path),
            "-p",
            str(output_path),
        ]
        result = run_command(
            cmd,
            description=f"BBP pairing round {current_round}",
            check=False,
            capture_output=True,
            verbose=False,
        )
        if result.returncode != 0:
            if not output_path.exists() or output_path.stat().st_size == 0:
                error_text = result.stderr.strip() or result.stdout.strip()
                raise RuntimeError(
                    "BBP pairing failed for round "
                    f"{current_round}: {error_text or 'unknown error'}"
                )
            # Log warning but continue if output exists
            logger.warning(
                f"BBP pairing had errors for round {current_round}: "
                f"{result.stderr.strip() or result.stdout.strip()}"
            )

        if not output_path.exists():
            raise FileNotFoundError(f"BBP output not found: {output_path}")

        output_text = output_path.read_text(encoding="utf-8")
        return parse_bbp_pairing_output(output_text, players)


class RandomTournamentGenerator:
    """Main tournament generator orchestrating player creation and results."""

    def __init__(self, config: RTGConfig):
        self.config = config
        self.player_factory = PlayerFactory(config)
        self.result_simulator = ResultSimulator(config)
        self.random = (
            random.Random(config.seed) if config.seed is not None else random.Random()
        )
        self.pairing_history = PairingHistory()
        self.bbp_engine = (
            BBPPairingEngine(config)
            if config.pairing_system in {"bbp_dutch", "dual"}
            else None
        )

    def generate_complete_tournament(self) -> Dict:
        """Generate a complete tournament with players and round results."""
        if self.config.pairing_system not in {"dutch_swiss", "bbp_dutch", "dual"}:
            raise ValueError(
                "Unsupported pairing system: " f"{self.config.pairing_system}"
            )
        logger.info(
            "Generating tournament: %s players, %s rounds",
            self.config.num_players,
            self.config.num_rounds,
        )

        players = self.player_factory.create_players()
        bye_schedule = self._build_bye_schedule(players)

        tournament_data = {
            "config": self.config,
            "players": players,
            "rounds": [],
        }

        for round_num in range(1, self.config.num_rounds + 1):
            round_data = self._simulate_round(players, round_num, bye_schedule)
            tournament_data["rounds"].append(round_data)

        if self.config.validate_with_fpc and self.config.pairing_system in {
            "dutch_swiss",
            "dual",
        }:
            validation_players = [
                {
                    "id": player.id,
                    "name": player.name,
                    "rating": player.rating,
                    "pairing_number": player.pairing_number,
                    "federation": player.federation,
                }
                for player in players
            ]
            validator = create_fpc_validator()
            report = validator.validate_tournament_compliance(
                {
                    "config": {"num_rounds": self.config.num_rounds},
                    "players": validation_players,
                    "rounds": [
                        {
                            "round_number": round_data["round_number"],
                            "pairings": [
                                (white.id, black.id)
                                for white, black in round_data["pairings"]
                            ],
                            "bye_player_id": round_data.get("bye_player_id"),
                            "scheduled_byes": round_data.get("scheduled_byes", {}),
                            "results": round_data.get("results", []),
                        }
                        for round_data in tournament_data["rounds"]
                    ],
                }
            )
            tournament_data["fpc_report"] = {
                "summary": report.summary,
                "compliance_percentage": report.compliance_percentage,
                "warnings": summarize_fpc_warnings(report),
                "absolute_violations": [v.criterion for v in report.violations],
            }

        logger.info("Tournament generation complete")
        return tournament_data

    def _simulate_round(
        self, players: List[Player], round_number: int, bye_schedule: ByeSchedule
    ) -> Dict:
        """Simulate a single round with FIDE-compliant pairings and results."""
        scheduled_zero = [
            player
            for player in players
            if round_number in bye_schedule.zero_point_byes.get(player.id, [])
        ]
        scheduled_half = [
            player
            for player in players
            if round_number in bye_schedule.half_point_byes.get(player.id, [])
        ]
        excluded_ids = {p.id for p in scheduled_zero + scheduled_half}
        active_players = [
            player
            for player in players
            if player.is_active and player.id not in excluded_ids
        ]

        if self.config.pairing_system in {"bbp_dutch", "dual"} and excluded_ids:
            logger.warning(
                "Scheduled byes are not represented in BBP pairing input; "
                "results may diverge"
            )

        gambit_pairings = None
        gambit_bye = None
        bbp_pairings = None
        bbp_bye = None
        gambit_time_ms = 0.0
        bbp_time_ms = 0.0

        if self.config.pairing_system in {"dutch_swiss", "dual"}:
            import time

            start_time = time.perf_counter()
            gambit_pairings, gambit_bye, _, _ = create_dutch_swiss_pairings(
                active_players,
                round_number,
                self.pairing_history.previous_matches,
                self._select_pab_candidate,
                total_rounds=self.config.num_rounds,
                initial_color=self.config.initial_color or WHITE,
                fide_strict=self.config.fide_strict,
            )
            gambit_time_ms = (time.perf_counter() - start_time) * 1000

        if self.config.pairing_system in {"bbp_dutch", "dual"}:
            if not self.bbp_engine:
                raise RuntimeError("BBP engine requested but not configured")
            import time

            start_time = time.perf_counter()
            try:
                bbp_pairings, bbp_bye = self.bbp_engine.generate_pairings(
                    active_players,
                    round_number,
                    self.config.num_rounds,
                )
                bbp_time_ms = (time.perf_counter() - start_time) * 1000
            except RuntimeError as exc:
                logger.warning(
                    "BBP pairing failed for round %s: %s",
                    round_number,
                    exc,
                )
                bbp_pairings = None
                bbp_bye = None

        if self.config.pairing_system == "bbp_dutch":
            pairings = bbp_pairings or []
            bye_player = bbp_bye
        else:
            pairings = gambit_pairings or []
            bye_player = gambit_bye

        results = []
        for white_player, black_player in pairings:
            white_score, black_score, forfeit = (
                self.result_simulator.simulate_pairing_result(
                    white_player, black_player, round_number
                )
            )
            results.append(
                (
                    white_player.id,
                    black_player.id,
                    white_score,
                    black_score,
                    forfeit,
                )
            )
            white_player.add_round_result(black_player, white_score, WHITE)
            black_player.add_round_result(white_player, black_score, BLACK)
            self.pairing_history.add_pairing(white_player.id, black_player.id)

        if bye_player is not None:
            bye_player.add_round_result(None, BYE_SCORE, None)

        for player in scheduled_half:
            player.add_round_result(None, DRAW_SCORE, None)

        for player in scheduled_zero:
            player.add_round_result(None, LOSS_SCORE, None)

        round_payload = {
            "round_number": round_number,
            "pairings": pairings,
            "bye_player_id": bye_player.id if bye_player else None,
            "scheduled_byes": {
                "half_point": [p.id for p in scheduled_half],
                "zero_point": [p.id for p in scheduled_zero],
            },
            "results": results,
        }
        if gambit_pairings is not None:
            round_payload["gambit_pairings"] = gambit_pairings
            round_payload["gambit_bye_player_id"] = (
                gambit_bye.id if gambit_bye else None
            )
            round_payload["gambit_time_ms"] = gambit_time_ms
        if bbp_pairings is not None:
            round_payload["bbp_pairings"] = bbp_pairings
            round_payload["bbp_bye_player_id"] = bbp_bye.id if bbp_bye else None
            round_payload["bbp_time_ms"] = bbp_time_ms

        if gambit_pairings is not None and bbp_pairings is not None:
            round_payload["pairing_comparison"] = self._compare_pairings(
                gambit_pairings, bbp_pairings
            )

        return round_payload

    def _select_pab_candidate(self, players: List[Player]) -> Optional[Player]:
        def has_full_point_unplayed(player: Player) -> bool:
            for opponent_id, result in zip(player.opponent_ids, player.results):
                if opponent_id is None and result is not None and result >= WIN_SCORE:
                    return True
            return False

        eligible = [
            p
            for p in players
            if not p.has_received_bye and not has_full_point_unplayed(p)
        ]
        if not eligible:
            return None
        min_score = min(player.score for player in eligible)
        candidates = [p for p in eligible if p.score == min_score]

        current_round = max(len(player.results) for player in candidates) + 1
        unplayed_counts = {
            player.id: (
                current_round - 1 - len([opp for opp in player.opponent_ids if opp])
            )
            for player in candidates
        }
        min_unplayed = min(unplayed_counts.values())
        candidates = [
            player
            for player in candidates
            if unplayed_counts.get(player.id, 0) == min_unplayed
        ]
        return sorted(candidates, key=lambda p: p.pairing_number)[0]

    def _build_bye_schedule(self, players: List[Player]) -> ByeSchedule:
        player_ids = [player.id for player in players]
        zero_byes = self._assign_byes(
            player_ids,
            self._apply_rate(len(players), self.config.retired_rate),
            allow_last_round=True,
        )
        half_byes = self._assign_byes(
            player_ids,
            self._apply_rate(len(players), self.config.half_point_bye_rate),
            allow_last_round=False,
        )
        return ByeSchedule(zero_point_byes=zero_byes, half_point_byes=half_byes)

    def _apply_rate(self, player_count: int, rate: float) -> int:
        if rate <= 0:
            return 0
        return max(0, min(player_count, int(player_count / rate)))

    def _assign_byes(
        self, player_ids: List[str], bye_count: int, allow_last_round: bool
    ) -> Dict[str, List[int]]:
        schedule = {player_id: [] for player_id in player_ids}
        if bye_count <= 0:
            return schedule

        rounds = (
            list(range(1, self.config.num_rounds + 1))
            if allow_last_round
            else list(range(1, max(2, self.config.num_rounds)))
        )

        attempts = 0
        while bye_count > 0 and attempts < bye_count * 10:
            player_id = self.random.choice(player_ids)
            round_number = self.random.choice(rounds)
            if round_number not in schedule[player_id]:
                schedule[player_id].append(round_number)
                bye_count -= 1
            attempts += 1

        return schedule

    def _compare_pairings(
        self,
        gambit_pairings: List[Tuple[Player, Player]],
        bbp_pairings: List[Tuple[Player, Player]],
    ) -> Dict[str, int]:
        def pairing_keys(pairings: List[Tuple[Player, Player]]) -> set:
            return {tuple(sorted((white.id, black.id))) for white, black in pairings}

        gambit_set = pairing_keys(gambit_pairings)
        bbp_set = pairing_keys(bbp_pairings)
        return {
            "matching_pairs": len(gambit_set & bbp_set),
            "gambit_only_pairs": len(gambit_set - bbp_set),
            "bbp_only_pairs": len(bbp_set - gambit_set),
        }

    def export_json_format(self, tournament_data: Dict) -> str:
        import json

        def serialize_pairings(
            pairings: List[Tuple[Player, Player]],
        ) -> List[Tuple[str, str]]:
            return [(white.id, black.id) for white, black in pairings]

        serialized_rounds = []
        for round_data in tournament_data["rounds"]:
            round_payload = {
                "round_number": round_data["round_number"],
                "pairings": serialize_pairings(round_data["pairings"]),
                "bye_player_id": round_data.get("bye_player_id"),
                "scheduled_byes": round_data.get("scheduled_byes", {}),
                "results": round_data.get("results", []),
            }
            if "gambit_pairings" in round_data:
                round_payload["gambit_pairings"] = serialize_pairings(
                    round_data["gambit_pairings"]
                )
                round_payload["gambit_bye_player_id"] = round_data.get(
                    "gambit_bye_player_id"
                )
            if "bbp_pairings" in round_data:
                round_payload["bbp_pairings"] = serialize_pairings(
                    round_data["bbp_pairings"]
                )
                round_payload["bbp_bye_player_id"] = round_data.get("bbp_bye_player_id")
            if "pairing_comparison" in round_data:
                round_payload["pairing_comparison"] = round_data["pairing_comparison"]
            serialized_rounds.append(round_payload)

        export_data = {
            "tournament_config": {
                "num_players": self.config.num_players,
                "num_rounds": self.config.num_rounds,
                "rating_distribution": self.config.rating_distribution.value,
                "result_pattern": self.config.result_pattern.value,
                "seed": self.config.seed,
                "draw_percentage": self.config.draw_percentage,
                "forfeit_rate": self.config.forfeit_rate,
            },
            "players": [
                {
                    "id": player.id,
                    "pairing_number": player.pairing_number,
                    "name": player.name,
                    "rating": player.rating,
                    "federation": self.config.federation_bias,
                }
                for player in tournament_data["players"]
            ],
            "rounds": serialized_rounds,
        }

        return json.dumps(export_data, indent=2)

    def export_trf_format(self, tournament_data: Dict) -> str:
        lines = []
        lines.append(f"012 {self.config.num_players:03d}")
        lines.append(f"013 {self.config.num_rounds:03d}")
        lines.append(f"001 {self.config.seed or 0:010d}")

        for i, player in enumerate(tournament_data["players"]):
            lines.append(
                f"001 {i+1:04d} {player.name:20s} {player.rating or 0:04d} 0 0 0"
            )

        for round_data in tournament_data["rounds"]:
            round_num = round_data["round_number"]
            for white, black in round_data["pairings"]:
                lines.append(
                    f"022 {round_num:03d} {white.pairing_number:04d} {black.pairing_number:04d}"
                )
            for white_id, black_id, result, _forfeit in round_data["results"]:
                lines.append(f"096 {round_num:03d} {white_id} {black_id} {result:.1f}")

        return "\n".join(lines) + "\n"


def summarize_fpc_warnings(report) -> Dict[str, int]:
    """Summarize FPC quality warnings by criterion."""
    from collections import Counter

    return dict(Counter([warning.criterion for warning in report.quality_warnings]))


def create_r_tg_generator(config: RTGConfig) -> RandomTournamentGenerator:
    """Create RTG tournament generator with given configuration."""
    return RandomTournamentGenerator(config)


def create_small_tournament(
    num_players: int = 8, seed: Optional[int] = None
) -> RandomTournamentGenerator:
    """Create small tournament for testing."""
    config = RTGConfig(
        num_players=num_players,
        num_rounds=max(3, num_players - 1),
        rating_distribution=RatingDistribution.NORMAL,
        result_pattern=ResultPattern.REALISTIC,
        seed=seed,
    )
    return create_r_tg_generator(config)


def create_normal_tournament(
    num_players: int = 24, seed: Optional[int] = None
) -> RandomTournamentGenerator:
    """Create standard tournament for development testing."""
    config = RTGConfig(
        num_players=num_players,
        num_rounds=min(7, max(3, num_players // 4)),
        rating_distribution=RatingDistribution.NORMAL,
        result_pattern=ResultPattern.REALISTIC,
        seed=seed,
    )
    return create_r_tg_generator(config)


def create_large_tournament(
    num_players: int = 64, seed: Optional[int] = None
) -> RandomTournamentGenerator:
    """Create large tournament for performance testing."""
    config = RTGConfig(
        num_players=num_players,
        num_rounds=min(11, num_players // 6),
        rating_distribution=RatingDistribution.NORMAL,
        result_pattern=ResultPattern.REALISTIC,
        seed=seed,
    )
    return create_r_tg_generator(config)


def create_fide_style_tournament(
    num_players: int = 32, seed: Optional[int] = None
) -> RandomTournamentGenerator:
    """Create FIDE-style tournament for validation."""
    config = RTGConfig(
        num_players=num_players,
        num_rounds=min(5, num_players // 5),
        rating_distribution=RatingDistribution.FIDE,
        result_pattern=ResultPattern.REALISTIC,
        federation_bias="FIDE",
        seed=seed,
        fide_strict=True,
    )
    return create_r_tg_generator(config)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Random Tournament Generator (RTG)")
    parser.add_argument(
        "--players",
        type=int,
        default=16,
        help="Number of players in the tournament (default: 16)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )
    parser.add_argument(
        "--type",
        choices=["fide", "normal", "small"],
        default="fide",
        help="Tournament type: fide (FIDE-style), normal (standard), small (minimal rounds)",
    )
    parser.add_argument(
        "--pairing-system",
        choices=["dutch_swiss", "bbp_dutch", "dual"],
        default="dutch_swiss",
        help="Pairing system: dutch_swiss, bbp_dutch, or dual",
    )
    parser.add_argument(
        "--initial-color",
        choices=["white", "black"],
        default=None,
        help="Initial color for Gambit Dutch pairings",
    )
    parser.add_argument(
        "--bbp-exe",
        dest="bbp_executable",
        default=None,
        help="Path to bbpPairings executable for BBP runs",
    )
    parser.add_argument(
        "--bbp-initial-color",
        choices=["white1", "black1"],
        default="white1",
        help="Initial color for BBP pairing (white1 or black1)",
    )
    parser.add_argument(
        "--bbp-workdir",
        default=None,
        help="Directory for BBP input/output files",
    )
    parser.add_argument(
        "--bbp-keep-files",
        action="store_true",
        help="Keep BBP pairing input/output files",
    )
    parser.add_argument(
        "--fide-strict",
        action="store_true",
        help="Enable strict FIDE compliance search (slower)",
    )
    args = parser.parse_args()

    if args.type == "fide":
        generator = create_fide_style_tournament(args.players, seed=args.seed)
    elif args.type == "normal":
        generator = create_normal_tournament(args.players, seed=args.seed)
    elif args.type == "small":
        generator = create_small_tournament(args.players, seed=args.seed)
    else:
        raise ValueError(f"Unknown tournament type: {args.type}")

    generator.config.pairing_system = args.pairing_system
    generator.config.bbp_executable = args.bbp_executable
    generator.config.bbp_initial_color = args.bbp_initial_color
    if args.initial_color:
        generator.config.initial_color = (
            WHITE if args.initial_color == "white" else BLACK
        )
    generator.config.bbp_workdir = args.bbp_workdir
    generator.config.bbp_keep_files = args.bbp_keep_files
    if args.fide_strict:
        generator.config.fide_strict = True
    if generator.config.pairing_system in {"bbp_dutch", "dual"}:
        generator.bbp_engine = BBPPairingEngine(generator.config)
    else:
        generator.bbp_engine = None

    tournament = generator.generate_complete_tournament()
    print("Generated Tournament:")
    print(f"Players: {len(tournament['players'])}")
    print(f"Rounds: {len(tournament['rounds'])}")

    validator = create_fpc_validator()
    report = validator.validate_tournament_compliance(
        {
            "config": {"num_rounds": generator.config.num_rounds},
            "players": tournament["players"],
            "rounds": [
                {
                    "round_number": round_data["round_number"],
                    "pairings": [
                        (white.id, black.id) for white, black in round_data["pairings"]
                    ],
                    "bye_player_id": round_data["bye_player_id"],
                    "results": round_data["results"],
                }
                for round_data in tournament["rounds"]
            ],
        }
    )
    print(report.summary)
    warnings = summarize_fpc_warnings(report)
    if warnings:
        print("Quality warnings by criterion:")
        for criterion, count in sorted(warnings.items()):
            print(f"  {criterion}: {count}")
