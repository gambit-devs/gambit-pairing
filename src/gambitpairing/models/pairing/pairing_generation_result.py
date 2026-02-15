@dataclass
class PairingGenerationResult:
    """Result of a pairing generation operation."""

    success: bool
    pairings: List[Tuple["Player", "Player"]]
    bye_player: Optional["Player"]
    error_message: Optional[str] = None
