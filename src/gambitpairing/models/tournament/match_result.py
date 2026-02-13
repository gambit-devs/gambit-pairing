
@dataclass
class MatchResult:
    """Represents the result of a single match.

    Attributes:
        white_id: ID of the white player
        black_id: ID of the black player
        white_score: Score for white (1.0 = win, 0.5 = draw, 0.0 = loss)
        black_score: Score for black (computed as 1.0 - white_score)
    """

    white_id: str
    black_id: str
    white_score: float

    @property
    def black_score(self) -> float:
        """Calculate black's score based on white's score."""
        return 1.0 - self.white_score

    def to_dict(self) -> Dict[str, Any]:
        """Serialize match result to dictionary."""
        return {
            "white_id": self.white_id,
            "black_id": self.black_id,
            "white_score": self.white_score,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MatchResult":
        """Deserialize match result from dictionary."""
        return cls(
            white_id=data["white_id"],
            black_id=data["black_id"],
            white_score=data["white_score"],
        )
