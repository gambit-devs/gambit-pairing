"""A base chess player in a tournament. This is a base class."""

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

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from dateutil.relativedelta import relativedelta

from gambitpairing.club import Club
from gambitpairing.type_hints import BLACK, WHITE, Colour
from gambitpairing.utils import generate_id, setup_logger
from gambitpairing.utils.validation import validate_email, validate_phone

logger = setup_logger(__name__)


class Player:
    """Represents a player in the tournament.

    This class provides the core functionality for managing player data
    in chess tournaments, including history tracking, color balance,
    and tiebreak calculations.

    Attributes:
        id: Unique identifier for the player
        name: Player's full name
        rating: Player's chess rating
        phone: Contact phone number (validated)
        email: Contact email address (validated)
        club: Chess club affiliation
        gender: Player's gender
        dob: Date of birth
        federation: Chess federation
        is_active: Whether player is actively participating
        score: Current tournament score
        color_history: List of colors played (W, B, or None for bye)
        opponent_ids: List of opponent IDs played against
        results: List of game results (1.0=win, 0.5=draw, 0.0=loss)
        running_scores: Cumulative scores after each round
        has_received_bye: Whether player has received a bye
        num_black_games: Count of games played as Black
        float_history: Rounds where player floated down
        match_history: Detailed match information
        tiebreakers: Calculated tiebreak values
    """

    def __init__(
        self,
        name: str,
        rating: Optional[int] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        club: Optional[Club] = None,
        gender: Optional[str] = None,
        date_of_birth: Optional[date] = None,
        federation: Optional[str] = None,
        **kwargs,  # Accept additional arguments for flexibility
    ) -> None:
        # Generate unique ID for internal use
        self.id: str = generate_id(self.__class__.__name__)

        # Core attributes
        self.name: str = name
        self.rating: int = rating if rating is not None else 0

        # Validated contact information
        self.phone: Optional[str] = self._validate_and_set_phone(phone)
        self.email: Optional[str] = self._validate_and_set_email(email)

        # Additional information
        self.club: Optional[Club] = club
        self.gender: Optional[str] = gender
        self.dob: Optional[date] = date_of_birth
        self.federation: Optional[str] = federation

        # Tournament participation status
        self.is_active: bool = True

        # Game history - initialized as empty lists
        self.score: float = 0.0
        self.color_history: List[Optional[Colour]] = []
        self.opponent_ids: List[Optional[str]] = []
        self.results: List[Optional[float]] = []
        self.running_scores: List[float] = []
        self.has_received_bye: bool = False
        self.num_black_games: int = 0
        self.float_history: List[int] = []
        self.match_history: List[Optional[Dict[str, Any]]] = []

        # Tiebreakers (calculated externally)
        self.tiebreakers: Dict[str, float] = {}

        # Runtime cache for performance
        self._opponents_played_cache: List[Optional["Player"]] = []

    def _validate_and_set_phone(self, phone: Optional[str]) -> Optional[str]:
        """Validate and set phone number using validation utility.

        Args:
            phone: Phone number to validate

        Returns:
            Sanitized phone number or None
        """
        if phone is None:
            logger.debug("No phone given for: %s", self.name)
            return None

        result = validate_phone(phone)
        if result.is_valid:
            return result.sanitized_value
        else:
            logger.warning(
                "Invalid phone number for %s: %s - %s",
                self.name,
                phone,
                result.error_message,
            )
            return None

    def _validate_and_set_email(self, email: Optional[str]) -> Optional[str]:
        """Validate and set email address using validation utility.

        Args:
            email: Email address to validate

        Returns:
            Sanitized email or None
        """
        if email is None:
            logger.debug("No email given for: %s", self.name)
            return None

        result = validate_email(email)
        if result.is_valid:
            return result.sanitized_value
        else:
            logger.warning(
                "Invalid email for %s: %s - %s", self.name, email, result.error_message
            )
            return None

    @property
    def age(self) -> Optional[int]:
        """Calculate age from date of birth.

        Returns:
            Player's age in years, or None if date of birth is unknown
        """
        if self.dob:
            # Handle case where dob might be a string (defensive programming)
            dob = self.dob
            if isinstance(dob, str):
                try:
                    dob = date.fromisoformat(dob)
                    # Update the instance variable to be a proper date object
                    self.dob = dob
                except (ValueError, AttributeError):
                    logger.warning("Invalid date format for %s: %s", self.name, dob)
                    return None

            today = date.today()
            age = relativedelta(today, dob)
            return age.years

        logger.debug("%s has no date of birth set", self.name)
        return None

    @property
    def date_of_birth(self) -> Optional[date]:
        """Get the player's date of birth.

        Returns:
            Date of birth, or None if unknown
        """
        return self.dob

    @date_of_birth.setter
    def date_of_birth(self, value: Optional[date]) -> None:
        """Set the player's date of birth.

        Args:
            value: Date of birth to set
        """
        self.dob = value

    def get_opponent_objects(
        self, players_dict: Dict[str, "Player"]
    ) -> List[Optional["Player"]]:
        """Resolve opponent IDs to Player objects using cached lookup.

        Uses an internal cache to avoid repeated lookups for performance.

        Args:
            players_dict: Dictionary mapping player IDs to Player objects

        Returns:
            List of opponent Player objects (None for byes)
        """
        if len(self._opponents_played_cache) != len(self.opponent_ids):
            self._opponents_played_cache = [
                players_dict.get(opp_id) if opp_id else None
                for opp_id in self.opponent_ids
            ]
        return self._opponents_played_cache

    def get_last_two_colors(self) -> Tuple[Optional[Colour], Optional[Colour]]:
        """Get the colors of the last two non-bye games played.

        Returns:
            Tuple of (last_color, second_last_color), with None if not enough games
        """
        valid_colors = [c for c in self.color_history if c is not None]
        if len(valid_colors) >= 2:
            # type: ignore | this confuses my type checker
            return valid_colors[-1], valid_colors[-2]
        elif len(valid_colors) == 1:
            return valid_colors[-1], None  # type: ignore
        else:
            return None, None

    def get_color_preference(self) -> Optional[Colour]:
        """Determine color preference based on FIDE/US-CF pairing rules.

        Rules:
        1. Absolute: If last two games had same color, MUST get the opposite
        2. Preference: If colors are unbalanced, prefer the color for balance
        3. None: Perfectly balanced or insufficient history

        Returns:
            "White", "Black", or None if no preference
        """
        played_colors = [c for c in self.color_history if c is not None]

        # Rule 1: Absolute color preference (two same colors in a row)
        if len(played_colors) >= 2:
            last_color = played_colors[-1]
            second_last_color = played_colors[-2]
            if last_color == second_last_color:
                return BLACK if last_color == WHITE else WHITE  # type: ignore

        # Rule 2: Color balance preference
        white_games_played = sum(1 for c in played_colors if c == WHITE)
        black_games_played = sum(1 for c in played_colors if c == BLACK)

        if white_games_played > black_games_played:
            return BLACK
        elif black_games_played > white_games_played:
            return WHITE

        return None

    def add_round_result(
        self, opponent: Optional["Player"], result: float, color: Optional[str]
    ) -> None:
        """Record the outcome of a round for this player.

        This method updates both players' histories when a game is played,
        including scores, colors, and match details.

        Args:
            opponent: Opponent player object (None for bye)
            result: Game result (1.0=win, 0.5=draw, 0.0=loss, 1.0 for bye)
            color: Color played ("White", "Black", or None for bye)

        Side Effects:
            - Updates score, results, and history for both players
            - Invalidates opponent cache
            - Sets bye flag if opponent is None
        """
        opponent_id = opponent.id if opponent else None
        self.opponent_ids.append(opponent_id)
        self.results.append(result)

        # Record match details before updating scores
        player_score_before = self.score
        opponent_score_before = opponent.score if opponent else 0.0

        self.match_history.append(
            {
                "opponent_id": opponent_id,
                "player_score": player_score_before,
                "opponent_score": opponent_score_before,
            }
        )

        if opponent:
            opponent.match_history.append(
                {
                    "opponent_id": self.id,
                    "player_score": opponent_score_before,
                    "opponent_score": player_score_before,
                }
            )

        # Update scores
        self.score += result
        self.running_scores.append(self.score)

        # Track colors
        self.color_history.append(color)  # type: ignore | color can be None for bye
        if color == "Black":
            self.num_black_games += 1

        # Handle bye
        if opponent is None:
            self.has_received_bye = True
            logger.debug("Player %s received a bye in this round", self.name)

        # Invalidate cache
        self._opponents_played_cache = []

    def to_dict(self) -> Dict[str, Any]:
        """Serialize player data to dictionary format.

        Converts all public attributes to a dictionary suitable for JSON
        serialization or database storage. Date objects are converted to
        ISO format strings.

        Returns:
            Dictionary containing all player data (excludes private attributes)
        """
        data = {}
        for k, v in self.__dict__.items():
            if not k.startswith("_"):
                # Convert date objects to ISO format strings for JSON serialization
                if isinstance(v, date):
                    data[k] = v.isoformat()
                else:
                    data[k] = v
        return data

    @classmethod
    def from_dict(cls, player_data: Dict[str, Any]) -> "Player":
        """Create a Player instance from serialized dictionary data.

        This method handles backward compatibility and automatically creates
        FidePlayer instances when FIDE-specific data is present.

        Args:
            player_data: Dictionary containing player data

        Returns:
            Player or FidePlayer instance with restored state

        Note:
            Handles backward compatibility for older save formats including:
            - sex/gender field consolidation
            - Missing list attributes
            - Missing boolean flags
        """
        # Auto-detect and create FidePlayer if FIDE data present
        if cls.__name__ == "Player" and player_data.get("fide_id") is not None:
            from gambitpairing.player.fide_player import FidePlayer

            return FidePlayer.from_dict(player_data)

        # Handle backward compatibility for sex/gender field
        gender = player_data.get("gender") or player_data.get("sex")

        # Parse date_of_birth if it's a string
        dob_value = player_data.get("dob") or player_data.get("date_of_birth")
        date_of_birth = None
        if dob_value:
            if isinstance(dob_value, str):
                try:
                    # Try parsing ISO format: YYYY-MM-DD
                    date_of_birth = date.fromisoformat(dob_value)
                except (ValueError, AttributeError):
                    date_of_birth = None
            elif isinstance(dob_value, date):
                date_of_birth = dob_value

        # Create base player with core attributes
        player = cls(
            name=player_data["name"],
            rating=player_data.get("rating"),
            phone=player_data.get("phone"),
            email=player_data.get("email"),
            club=player_data.get("club"),
            gender=gender,
            date_of_birth=date_of_birth,
            federation=player_data.get("federation"),
        )

        # Restore all saved attributes
        for key, value in player_data.items():
            if hasattr(player, key) and not key.startswith("_"):
                setattr(player, key, value)

        # Ensure essential list attributes exist (backward compatibility)
        cls._ensure_list_attributes(player)

        # Ensure boolean flags exist (backward compatibility)
        cls._ensure_boolean_attributes(player)

        # Ensure tiebreakers dict exists
        if not hasattr(player, "tiebreakers") or player.tiebreakers is None:
            player.tiebreakers = {}

        return player

    @staticmethod
    def _ensure_list_attributes(player: "Player") -> None:
        """Ensure all list attributes exist for backward compatibility.

        Args:
            player: Player instance to update
        """
        list_attributes = [
            "color_history",
            "opponent_ids",
            "results",
            "running_scores",
            "float_history",
            "match_history",
        ]

        for attr_name in list_attributes:
            if not hasattr(player, attr_name) or getattr(player, attr_name) is None:
                setattr(player, attr_name, [])

    @staticmethod
    def _ensure_boolean_attributes(player: "Player") -> None:
        """Ensure all boolean attributes exist for backward compatibility.

        Args:
            player: Player instance to update
        """
        if not hasattr(player, "has_received_bye"):
            player.has_received_bye = (
                None in player.opponent_ids if player.opponent_ids else False
            )

        if not hasattr(player, "num_black_games"):
            player.num_black_games = (
                player.color_history.count("Black") if player.color_history else 0
            )

        if not hasattr(player, "is_active"):
            player.is_active = True

    def __repr__(self) -> str:
        """Return string representation for debugging.

        Returns:
            String representation showing name and rating
        """
        return f"Player(name='{self.name}', rating={self.rating}, id='{self.id}')"

    def __str__(self) -> str:
        """Return human-readable string representation.

        Returns:
            Player name and rating
        """
        return f"{self.name} ({self.rating})"
