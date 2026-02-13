"""Type hints used in Gambit Pairing."""

from typing import List, Literal, Optional, Tuple

# Chess color string constants (for runtime use)
WHITE = "White"
BLACK = "Black"

# Chess color type aliases (for type hints)
W = Literal["White"]
B = Literal["Black"]
# Basically, white or black
Colour = Literal["White", "Black"]

# Outcome type literals (for type hints)
OutcomeType = Literal["normal", "forfeit_win", "forfeit_loss", "double_forfeit", "bye"]

# Result type literals (for UI display)
ResultDisplay = Literal[
    "1-0",
    "0.5-0.5",
    "0-1",
    "1-0 FF",
    "0-1 FF",
    "0-0 FF",
    "Bye (1.0)",
    "Bye (0.5)",
    "Bye (0.0)",
]


# List of players
Players = List["Player"]
# Tuple of player indices in Players
MatchPairing = Tuple[int, int]
# All pairings for one round
RoundSchedule = Tuple[MatchPairing, ...]
# A Tuple containing
Pairings = Tuple[List[Tuple["Player", "Player"]], Optional["Player"]]
MaybePlayer = Optional["Player"]

#  LocalWords:  MatchPairing RoundSchedule
