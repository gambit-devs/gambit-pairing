"""Core tournament player model."""

from __future__ import annotations

from datetime import date
from importlib import import_module
from typing import Any, Dict, List, Optional, Tuple

from dateutil.relativedelta import relativedelta

from gambitpairing.models.enums import Colour
from gambitpairing.models.player.abc_player import PlayerABC
from gambitpairing.utils import generate_id, setup_logger
from gambitpairing.utils.validation import validate_email, validate_phone

logger = setup_logger(__name__)


class Player(PlayerABC):
    """Mutable chess player entity used by pairing and result systems."""

    def __init__(
        self,
        name: str,
        rating: Optional[int] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        club: Optional[object] = None,
        gender: Optional[str] = None,
        date_of_birth: Optional[date] = None,
        federation: Optional[str] = None,
        **_: Any,
    ) -> None:
        self._id: str = generate_id(self.__class__.__name__)
        self._name: str = name
        self._rating: int = rating if rating is not None else 0
        self._phone: Optional[str] = self._validate_and_set_phone(phone)
        self._email: Optional[str] = self._validate_and_set_email(email)
        self.club: Optional[object] = club
        self.gender: Optional[str] = gender
        self.dob: Optional[date] = date_of_birth
        self._federation: Optional[str] = federation

        self.is_active: bool = True
        self.score: float = 0.0
        self.pairing_number: Optional[int] = None
        self.bsn: Optional[int] = None

        self.color_history: List[Optional[Colour]] = []
        self.opponent_ids: List[Optional[str]] = []
        self.results: List[Optional[float]] = []
        self.running_scores: List[float] = []
        self.has_received_bye: bool = False
        self.num_black_games: int = 0
        self.is_moved_down: bool = False
        self.float_history: List[int] = []
        self.match_history: List[Optional[Dict[str, Any]]] = []
        self.tiebreakers: Dict[str, float] = {}
        self._opponents_played_cache: List[Optional["Player"]] = []

    @property
    def id(self) -> str:
        """Immutable player identifier."""
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value

    @property
    def rating(self) -> int:
        return self._rating

    @rating.setter
    def rating(self, value: Optional[int]) -> None:
        self._rating = value if value is not None else 0

    @property
    def phone(self) -> Optional[str]:
        return self._phone

    @phone.setter
    def phone(self, value: Optional[str]) -> None:
        self._phone = value

    @property
    def email(self) -> Optional[str]:
        return self._email

    @email.setter
    def email(self, value: Optional[str]) -> None:
        self._email = value

    @property
    def federation(self) -> Optional[str]:
        return self._federation

    @federation.setter
    def federation(self, value: Optional[str]) -> None:
        self._federation = value

    @property
    def colour_history(self) -> List[Optional[Colour]]:
        """British spelling compatibility for newer pairing code."""
        return self.color_history

    @colour_history.setter
    def colour_history(self, value: List[Optional[Colour]]) -> None:
        self.color_history = value

    def _validate_and_set_phone(self, phone: Optional[str]) -> Optional[str]:
        if phone is None:
            return None
        result = validate_phone(phone)
        if result.is_valid:
            return result.sanitized_value
        logger.warning("Invalid phone number for %s: %s", self.name, phone)
        return None

    def _validate_and_set_email(self, email: Optional[str]) -> Optional[str]:
        if email is None:
            return None
        result = validate_email(email)
        if result.is_valid:
            return result.sanitized_value
        logger.warning("Invalid email for %s: %s", self.name, email)
        return None

    @property
    def age(self) -> Optional[int]:
        """Calculate age from date of birth."""
        if not self.dob:
            return None
        dob = self.dob
        if isinstance(dob, str):
            try:
                dob = date.fromisoformat(dob)
                self.dob = dob
            except (ValueError, AttributeError):
                return None
        return relativedelta(date.today(), dob).years

    @property
    def date_of_birth(self) -> Optional[date]:
        return self.dob

    @date_of_birth.setter
    def date_of_birth(self, value: Optional[date]) -> None:
        self.dob = value

    def get_opponent_objects(
        self, players_dict: Dict[str, "Player"]
    ) -> List[Optional["Player"]]:
        """Resolve opponent IDs to player objects with a small cache."""
        if len(self._opponents_played_cache) != len(self.opponent_ids):
            self._opponents_played_cache = [
                players_dict.get(opp_id) if opp_id else None
                for opp_id in self.opponent_ids
            ]
        return self._opponents_played_cache

    def get_last_two_colors(self) -> Tuple[Optional[Colour], Optional[Colour]]:
        valid_colors = [c for c in self.color_history if c is not None]
        if len(valid_colors) >= 2:
            return valid_colors[-1], valid_colors[-2]
        if len(valid_colors) == 1:
            return valid_colors[-1], None
        return None, None

    def get_color_preference(self) -> Optional[Colour]:
        """Return the desired color based on simple balance rules."""
        played_colors = [c for c in self.color_history if c is not None]
        if len(played_colors) >= 2 and played_colors[-1] == played_colors[-2]:
            return Colour.BLACK if played_colors[-1] == Colour.WHITE else Colour.WHITE

        white_games = played_colors.count(Colour.WHITE)
        black_games = played_colors.count(Colour.BLACK)
        if white_games > black_games:
            return Colour.BLACK
        if black_games > white_games:
            return Colour.WHITE
        return None

    def add_round_result(
        self, opponent: Optional["Player"], result: float, color: Optional[Colour]
    ) -> None:
        """Record one round from this player's perspective."""
        opponent_id = opponent.id if opponent else None
        self.opponent_ids.append(opponent_id)
        self.results.append(result)

        player_score_before = self.score
        opponent_score_before = opponent.score if opponent else 0.0
        self.match_history.append(
            {
                "opponent_id": opponent_id,
                "player_score": player_score_before,
                "opponent_score": opponent_score_before,
            }
        )

        self.score += result
        self.running_scores.append(self.score)
        self.color_history.append(color)
        if color == Colour.BLACK:
            self.num_black_games += 1
        if opponent is None:
            self.has_received_bye = True
        self._opponents_played_cache = []

    def to_dict(self) -> Dict[str, Any]:
        """Serialize public player state."""
        data: Dict[str, Any] = {
            "name": self.name,
            "rating": self.rating,
            "phone": self.phone,
            "email": self.email,
            "federation": self.federation,
        }
        for key, value in self.__dict__.items():
            if key.startswith("_"):
                continue
            if isinstance(value, date):
                data[key] = value.isoformat()
            elif isinstance(value, list):
                data[key] = [
                    item.value if isinstance(item, Colour) else item for item in value
                ]
            else:
                data[key] = value.value if isinstance(value, Colour) else value
        data["id"] = self.id
        return data

    @classmethod
    def from_dict(cls, player_data: Dict[str, Any]) -> "Player":
        """Create a player from serialized data."""
        if cls.__name__ == "Player" and player_data.get("fide_id") is not None:
            fide_module = import_module("gambitpairing.models.player.fide_player")
            return fide_module.FidePlayer.from_dict(player_data)

        gender = player_data.get("gender") or player_data.get("sex")
        dob_value = player_data.get("dob") or player_data.get("date_of_birth")
        date_of_birth = cls._parse_date(dob_value)

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

        for key, value in player_data.items():
            if key == "id":
                player._id = str(value)
            elif hasattr(player, key) and not key.startswith("_"):
                setattr(player, key, value)

        player.color_history = [
            cls._parse_colour(color) for color in getattr(player, "color_history", [])
        ]
        cls._ensure_list_attributes(player)
        cls._ensure_boolean_attributes(player)
        if not hasattr(player, "tiebreakers") or player.tiebreakers is None:
            player.tiebreakers = {}
        player._opponents_played_cache = []
        return player

    @staticmethod
    def _parse_date(value: Any) -> Optional[date]:
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                return date.fromisoformat(value)
            except ValueError:
                return None
        return None

    @staticmethod
    def _parse_colour(value: Any) -> Optional[Colour]:
        if value is None or isinstance(value, Colour):
            return value
        try:
            return Colour(value)
        except ValueError:
            return None

    @staticmethod
    def _ensure_list_attributes(player: "Player") -> None:
        for attr_name in [
            "color_history",
            "opponent_ids",
            "results",
            "running_scores",
            "float_history",
            "match_history",
        ]:
            if not hasattr(player, attr_name) or getattr(player, attr_name) is None:
                setattr(player, attr_name, [])

    @staticmethod
    def _ensure_boolean_attributes(player: "Player") -> None:
        if not hasattr(player, "has_received_bye"):
            player.has_received_bye = (
                None in player.opponent_ids if player.opponent_ids else False
            )
        if not hasattr(player, "num_black_games"):
            player.num_black_games = player.color_history.count(Colour.BLACK)
        if not hasattr(player, "is_active"):
            player.is_active = True

    def __repr__(self) -> str:
        return f"Player(name='{self.name}', rating={self.rating}, id='{self.id}')"

    def __str__(self) -> str:
        return f"{self.name} ({self.rating})"
