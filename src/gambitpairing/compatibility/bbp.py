"""BBP (BieremaBoyzProgramming Pairings) compatibility layer for Gambit-Pairing.

This module provides compatibility with BBP pairings file formats and functionality,
enabling data exchange and validation between Gambit-Pairing and BBP reference implementation.
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

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterable, List, Optional, Tuple, Union

from gambitpairing.constants import BYE_SCORE, DRAW_SCORE, LOSS_SCORE, WIN_SCORE
from gambitpairing.player import Player
from gambitpairing.tournament.models import TournamentConfig
from gambitpairing.type_hints import BLACK, WHITE, Pairings
from gambitpairing.utils import setup_logger

logger = setup_logger(__name__)


class PointSystem(Enum):
    """Point system types supported by BBP."""

    STANDARD = "standard"  # 1-0-0.5 system
    THREE_POINT = "three_point"  # 3-1-0 system
    TWO_POINT = "two_point"  # 2-1-0 system
    CUSTOM = "custom"  # User-defined values


class TRFRecordType(Enum):
    """TRF record types in BBP format."""

    PLAYER = "001"
    RATING = "002"
    TIEBREAK_ORDER = "003"
    PARTICIPATION = "004"
    START_DATE = "005"
    ARBITER = "006"
    ROUND_RESULT = "007"
    PAIRING = "022"
    COLOR_PREFERENCE = "032"
    CHECKLIST = "033"


@dataclass
class BBPTournamentConfig:
    """BBP-compatible tournament configuration."""

    name: str
    point_system: PointSystem = PointSystem.STANDARD
    points_for_win: float = 1.0
    points_for_draw: float = 0.5
    points_for_played_loss: float = 0.0
    points_for_forfeit_loss: float = 0.0
    points_for_pairing_allocated_bye: float = 1.0
    acceleration_type: Optional[str] = None
    initial_color: Optional[str] = None
    fide_title_number: Optional[str] = None
    federation: Optional[str] = None


@dataclass
class TRFPlayerRecord:
    """Player record in TRF format."""

    starting_rank: int = 0
    name: str = ""
    rating: int = 0
    federation: Optional[str] = None
    title_numbers: Optional[str] = None
    birth_date: Optional[str] = None
    sex: Optional[str] = None
    fide_id: Optional[str] = None
    pairings_assigned: int = 0
    score: float = 0.0
    color_preference: Optional[str] = None
    float_direction: List[str] = field(default_factory=list)

    def __post_init__(self):
        # Convert rating to integer if needed
        if isinstance(self.rating, str):
            # Handle rating strings like "2000K"
            if self.rating.endswith("K"):
                self.rating = int(float(self.rating[:-1]) * 1000)
            else:
                self.rating = int(self.rating)
        elif self.rating is None:
            self.rating = 0

    def to_gambit_player(self) -> Player:
        """Convert to Gambit Player object."""
        player = Player(
            name=self.name,
            rating=self.rating,
            federation=self.federation,
            date_of_birth=self._parse_birth_date() if self.birth_date else None,
        )

        # Set pairing number
        player.pairing_number = self.starting_rank

        # Copy additional attributes
        if hasattr(self, "score"):
            player.score = self.score
        if hasattr(self, "color_preference"):
            # Convert color preference to history format
            if self.color_preference:
                player.color_history = [self.color_preference]

        return player

    def _parse_birth_date(self):
        """Parse birth date from TRF format (YYMMDD)."""
        if not self.birth_date or len(self.birth_date) != 8:
            return None

        try:
            year = int(self.birth_date[0:2])
            month = int(self.birth_date[2:4])
            day = int(self.birth_date[4:6])
            from datetime import date

            return date(year, month, day)
        except ValueError:
            logger.warning(f"Invalid birth date format: {self.birth_date}")
            return None


class TRFImporter:
    """Import TRF files with BBP extensions."""

    def __init__(self):
        self.reset_state()

    def reset_state(self):
        """Reset importer state for new file."""
        self.players: List[TRFPlayerRecord] = []
        self.tournaments: Dict = {}
        self.current_round = 0
        self.current_tournament_name = None

    def import_trf_file(
        self, file_path: str
    ) -> Tuple[List[TRFPlayerRecord], Optional[BBPTournamentConfig]]:
        """Import TRF file with BBP extensions."""
        logger.info(f"Importing TRF file: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Split records by empty lines and trim
            records = [line.strip() for line in content.split("\n") if line.strip()]

            return self._parse_trf_content(records)

        except FileNotFoundError:
            logger.error(f"TRF file not found: {file_path}")
            raise FileNotFoundError(f"TRF file not found: {file_path}")
        except Exception as e:
            logger.error(f"Error importing TRF file: {e}")
            raise

    def _parse_trf_content(
        self, records: List[str]
    ) -> Tuple[List[TRFPlayerRecord], Optional[BBPTournamentConfig]]:
        """Parse TRF content with BBP extensions."""
        players = []
        tournament_config = None

        for record in records:
            if not record:
                continue

            record_code = record[:3]
            record_data = record[4:].strip()

            if record_code == "001":  # Player record
                player = self._parse_player_record(record_data)
                if player:
                    players.append(player)

            elif record_code == "012":  # Tournament name
                self.current_tournament_name = record_data

            elif record_code == "013":  # Tiebreak order
                if tournament_config:
                    tournament_config.fide_title_number = record_data

            elif record_code == "037":  # Round data (simplified for BBP)
                # Format: 037 RRR SSSS... (pairings)
                round_info = self._parse_round_record(record_data)
                if round_info:
                    self.current_round = round_info["round"]
                    logger.info(f"Processing round {round_info['round']}")

            elif record_code.startswith("BB"):  # BBP extension
                self._parse_bbp_extension(
                    record_code, record_data, players, tournament_config
                )

        return players, tournament_config

    def _parse_player_record(self, data: str) -> Optional[TRFPlayerRecord]:
        """Parse player record (001) from TRF."""
        try:
            # Standard TRF format: 001 SSSS RRR VVV YYYYMMDD FIDE_ID TITLE_SEX ...
            parts = data.split()
            if len(parts) < 4:
                return None

            player = TRFPlayerRecord()
            player.starting_rank = int(parts[0])
            player.name = parts[1].strip() if len(parts) > 1 else "Unknown"

            # Parse remaining fields
            idx = 2
            while idx < len(parts):
                part = parts[idx].strip() if idx < len(parts) else ""

                if idx == 2 and part.isdigit():  # Rating
                    player.rating = int(part)
                elif idx == 3 and len(part) == 8:  # Birth date (YYMMDD)
                    player.birth_date = part
                elif idx == 4:  # Federation
                    player.federation = part if part else None
                elif idx == 5:  # FIDE ID
                    player.fide_id = part if part else None
                elif idx == 6:  # Title numbers
                    player.title_numbers = part if part else None
                elif idx == 7:  # Sex
                    player.sex = part if part else None
                elif idx == 8 and len(part) == 1:  # Color preference
                    player.color_preference = part

                idx += 1

            return player

        except Exception as e:
            logger.warning(f"Failed to parse player record: {data}, error: {e}")
            return None

    def _parse_round_record(self, data: str) -> Optional[Dict]:
        """Parse round record (037) from TRF."""
        try:
            parts = data.split()
            if len(parts) < 4:
                return None

            return {
                "round": int(parts[1]) if parts[1].isdigit() else 0,
                "pairings": parts[2].strip() if len(parts) > 2 else "",
            }
        except Exception as e:
            logger.warning(f"Failed to parse round record: {data}, error: {e}")
            return None

    def _parse_bbp_extension(
        self,
        code: str,
        data: str,
        players: List[TRFPlayerRecord],
        config: Optional[BBPTournamentConfig],
    ):
        """Parse BBP extension records."""
        if not config:
            return

        try:
            if code == "BBW":  # Points for win
                config.points_for_win = float(data)
            elif code == "BBD":  # Points for draw
                config.points_for_draw = float(data)
            elif code == "BBL":  # Points for played loss
                config.points_for_played_loss = float(data)
            elif code == "BBZ":  # Points for zero-point bye
                config.points_for_forfeit_loss = float(data)
            elif code == "BBF":  # Points for forfeit loss
                config.points_for_forfeit_loss = float(data)
            elif code == "BBU":  # Points for pairing-allocated bye
                config.points_for_pairing_allocated_bye = float(data)
            elif code == "XXA":  # Acceleration parameters
                # Format: XXA round_type parameter value
                # Example: XXA 1.5 for round 1
                parts = data.split()
                if len(parts) >= 2:
                    config.acceleration_type = parts[0] + " " + parts[1]
            elif code == "C02":  # Initial color assignment
                config.initial_color = data.strip() if data.strip() else None

        except Exception as e:
            logger.warning(f"Failed to parse BBP extension {code}: {data}, error: {e}")


class TRFExporter:
    """Export TRF files with BBP extensions."""

    def __init__(self):
        pass

    def export_tournament(
        self,
        players: List[Player],
        config: TournamentConfig,
        rounds_data: List[Dict],
        bbp_config: Optional[BBPTournamentConfig] = None,
    ):
        """Export tournament to TRF format with BBP extensions."""
        logger.info("Exporting tournament to TRF format")

        lines = []

        # Tournament header records
        lines.extend(
            [
                f"012 {config.name}",
                f"013 {','.join(config.tiebreak_order)}",
                "014 20250101"  # Date (placeholder)
                "015",  # City (placeholder)
                "016",  # Federation (placeholder)
                "017",  # Chief Arbiter (placeholder)
                "018",  # Deputy (placeholder)
            ]
        )

        # Determine point system from BBP config or tournament results
        if bbp_config:
            point_system = bbp_config.point_system
        else:
            # Infer from actual results
            results_with_draws = any(
                result == 0.5
                for player in players
                for result in getattr(player, "results", [])
                if result is not None
            )
            point_system = (
                PointSystem.THREE_POINT if results_with_draws else PointSystem.STANDARD
            )

        # Point system definition record
        lines.extend(
            [
                f"BBW {self._get_point_value(point_system, 'win')}",
                f"BBD {self._get_point_value(point_system, 'draw')}",
                f"BBL {self._get_point_value(point_system, 'played_loss')}",
                f"BBZ {self._get_point_value(point_system, 'zero_bye')}",
                f"BBF {self._get_point_value(point_system, 'forfeit_loss')}",
                f"BBU {self._get_point_value(point_system, 'pairing_bye')}",
            ]
        )

        # Player records
        for i, player in enumerate(players, 1):
            trf_record = self._create_player_record(player, i, point_system, bbp_config)
            if trf_record:
                lines.append(trf_record)

        # Round records
        for round_data in rounds_data:
            round_num = round_data.get("round", 0)
            round_line = self._create_round_record(
                round_num, round_data.get("pairings", [])
            )
            if round_line:
                lines.append(round_line)

        return "\\n".join(lines) + "\\n"

    def _get_point_value(self, system: PointSystem, result_type: str) -> str:
        """Get point value for TRF export."""
        values = {
            PointSystem.STANDARD: {"win": "1.0", "draw": ".5", "played_loss": "0.0"},
            PointSystem.THREE_POINT: {
                "win": "1.0",
                "draw": "0.0",
                "played_loss": "0.0",
            },
            PointSystem.TWO_POINT: {"win": "2.0", "draw": "1.0", "played_loss": "0.0"},
        }

        return values.get(system, {}).get(result_type, "1.0")

    def _create_player_record(
        self,
        player: Player,
        rank: int,
        point_system: PointSystem,
        bbp_config: Optional[BBPTournamentConfig],
    ) -> str:
        """Create TRF player record."""
        parts = [
            f"{rank:04d}",
            player.name[:20],  # Truncate to 20 characters
            str(player.rating if player.rating else 0),
            player.federation or "",
            bbp_config.fide_title_number if bbp_config else "",
            player.sex or "",
            self._format_date(player.date_of_birth) if player.date_of_birth else "",
            player.fide_id or "",
            getattr(player, "title_numbers", "") or "",
            str(player.score),
            str(len([op for op in player.opponent_ids if op]) - 1),  # Pairings assigned
            self._get_color_preference_code(player) or "",
        ]

        # Add float directions if available
        if hasattr(player, "float_history"):
            float_str = ",".join(str(value) for value in player.float_history)
            if float_str:
                parts.append(f"C12{float_str}")

        return "001 " + " ".join(parts)

    def _get_color_preference_code(self, player: Player) -> str:
        """Get color preference code for TRF export."""
        if not player.color_history:
            return ""

        # Convert color history to preference codes
        # This is simplified - full implementation would be more complex
        last_color = player.color_history[-1] if player.color_history else None
        if last_color == "white":
            return (
                "white"
                if len([c for c in player.color_history if c == "white"])
                < len([c for c in player.color_history if c == "black"])
                else "black"
            )
        elif last_color == "black":
            return (
                "black"
                if len([c for c in player.color_history if c == "black"])
                < len([c for c in player.color_history if c == "white"])
                else "white"
            )

        return ""

    def _format_date(self, date) -> str:
        """Format date for TRF export (YYMMDD)."""
        if not date:
            return ""

        return date.strftime("%y%m%d")

    def _create_round_record(
        self, round_num: int, pairings: List[Tuple[Player, Player]]
    ) -> str:
        """Create TRF round record (037)."""
        if not pairings:
            return ""

        pairing_strs = []
        for white, black in pairings:
            pairing_str = f"{white.pairing_number:04d}-{black.pairing_number:04d}"
            pairing_strs.append(pairing_str)

        # BBP format: 037 RRR SSSS... (S = space-separated pairings)
        all_pairings = " ".join(pairing_strs)

        # Ensure proper spacing (total length 79 characters after record code)
        padding = " " * (79 - (12 + len(all_pairings)))
        return f"037 {round_num:03d} {all_pairings}{padding}"


def import_bbp_trf(file_path: str) -> Tuple[List[Player], Optional[TournamentConfig]]:
    """Import BBP-compatible TRF file."""
    importer = TRFImporter()
    players, bbp_config = importer.import_trf_file(file_path)

    # Convert TRF players to Gambit players
    gambit_players = [player.to_gambit_player() for player in importer.players]

    # Convert BBP config to Gambit tournament config
    tournament_config = None
    if bbp_config:
        tournament_config = TournamentConfig(
            name=importer.current_tournament_name or "Imported Tournament",
            num_rounds=0,  # Would need to infer from data
            pairing_system="dutch_swiss",
            tiebreak_order=(
                bbp_config.fide_title_number.split(",")
                if bbp_config.fide_title_number
                else []
            ),
        )

    return gambit_players, tournament_config


def export_bbp_trf(
    players: List[Player],
    config: TournamentConfig,
    rounds_data: List[Dict],
    file_path: str,
    bbp_config: Optional[BBPTournamentConfig] = None,
):
    """Export tournament to BBP-compatible TRF file."""
    exporter = TRFExporter()
    content = exporter.export_tournament(players, config, rounds_data, bbp_config)

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Successfully exported to {file_path}")
    except Exception as e:
        logger.error(f"Failed to export TRF file: {e}")
        raise


def create_bbp_compatibility_layer() -> Tuple[TRFImporter, TRFExporter]:
    """Create BBP compatibility layer components."""
    return TRFImporter(), TRFExporter()


# Convenience functions
def convert_gambit_to_bbp_config(
    config: TournamentConfig,
) -> Optional[BBPTournamentConfig]:
    """Convert Gambit tournament config to BBP format."""
    # This is a simplified conversion
    # A full implementation would be more comprehensive
    return BBPTournamentConfig(
        name=config.name,
        point_system=PointSystem.STANDARD,
        fide_title_number=(
            ",".join(config.tiebreak_order) if config.tiebreak_order else ""
        ),
    )


def build_bbp_pairing_trf(
    players: List[Player],
    total_rounds: int,
    current_round: int,
    initial_color: str = "white1",
) -> str:
    """Build a BBP-compatible TRF string for pairing the next round."""
    if current_round < 1:
        raise ValueError("current_round must be >= 1")
    rounds_to_include = max(0, current_round - 1)
    if initial_color not in {"white1", "black1"}:
        raise ValueError("initial_color must be 'white1' or 'black1'")

    id_to_number = {
        player.id: int(player.pairing_number or idx)
        for idx, player in enumerate(players, 1)
    }
    scores = {
        player.id: _compute_score(player, rounds_to_include) for player in players
    }
    ranks = _compute_ranks(players, scores)

    lines = [f"XXC {initial_color}"]
    if total_rounds:
        lines.append(f"XXR {total_rounds}")

    for idx, player in enumerate(
        sorted(players, key=lambda p: p.pairing_number or 0), 1
    ):
        player_number = int(player.pairing_number or idx)
        rating = min(max(player.rating or 0, 0), 9999)
        score = scores.get(player.id, 0.0)
        rank = int(ranks.get(player.id, player_number))
        matches = _format_match_history(player, id_to_number, rounds_to_include)
        lines.append(_format_player_line(player_number, rating, score, rank, matches))

    return "\n".join(lines) + "\n"


def parse_bbp_pairing_output(
    output_text: str, players: Iterable[Player]
) -> Tuple[List[Tuple[Player, Player]], Optional[Player]]:
    """Parse BBP pairings output into Gambit players."""
    player_map = {player.pairing_number: player for player in players}
    lines = [line.strip() for line in output_text.splitlines() if line.strip()]
    if not lines:
        raise ValueError("BBP output was empty")

    pairings: List[Tuple[Player, Player]] = []
    bye_player = None
    for line in lines[1:]:
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            white_num = int(parts[0])
            black_num = int(parts[1])
        except ValueError:
            continue

        white_player = player_map.get(white_num)
        if not white_player:
            continue
        if black_num == 0 or black_num == white_num:
            bye_player = white_player
            continue
        black_player = player_map.get(black_num)
        if not black_player:
            continue
        pairings.append((white_player, black_player))

    return pairings, bye_player


def _compute_score(player: Player, rounds_to_include: int) -> float:
    results = getattr(player, "results", [])[:rounds_to_include]
    return float(sum(result for result in results if result is not None))


def _compute_ranks(
    players: Iterable[Player], scores: Dict[str, float]
) -> Dict[str, int]:
    ordered = sorted(
        players,
        key=lambda p: (-scores.get(p.id, 0.0), p.pairing_number),
    )
    return {player.id: idx + 1 for idx, player in enumerate(ordered)}


def _format_player_line(
    player_number: int,
    rating: int,
    score: float,
    rank: int,
    matches: str,
) -> str:
    return (
        f"001 {player_number:>4}"
        f"{'Test':>10}"
        f"{player_number:0>4}"
        " Player"
        f"{player_number:>4}"
        f"{rating:>19}"
        f"{'':>28}"
        f"{score:>4.1f}"
        f"{rank:>5}"
        f"{matches}"
    )


def _format_match_history(
    player: Player,
    id_to_number: Dict[str, int],
    rounds_to_include: int,
) -> str:
    opponent_ids = getattr(player, "opponent_ids", [])
    results = getattr(player, "results", [])
    colors = getattr(player, "color_history", [])
    segments = []
    for round_index in range(rounds_to_include):
        opponent_id = (
            opponent_ids[round_index] if round_index < len(opponent_ids) else None
        )
        result = results[round_index] if round_index < len(results) else None
        color = colors[round_index] if round_index < len(colors) else None
        segments.append(_format_match(opponent_id, result, color, id_to_number))
    return "".join(segments)


def _format_match(
    opponent_id: Optional[str],
    result: Optional[float],
    color: Optional[str],
    id_to_number: Dict[str, int],
) -> str:
    if opponent_id is None:
        if result == BYE_SCORE:
            result_code = "U"
        elif result == DRAW_SCORE:
            result_code = "H"
        elif result == LOSS_SCORE:
            result_code = "Z"
        else:
            result_code = "Z"
        return f"  0000 - {result_code}"

    opponent_number = id_to_number.get(opponent_id, 0)
    color_code = "w" if color == WHITE else "b" if color == BLACK else "-"
    if result is None:
        result_code = "0"
    elif result >= WIN_SCORE:
        result_code = "1"
    elif result == DRAW_SCORE:
        result_code = "="
    else:
        result_code = "0"
    return f"  {opponent_number:04d} {color_code} {result_code}"
