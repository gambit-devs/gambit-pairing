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

# --- Constants ---
SAVE_FILE_EXTENSION = ".json"
SAVE_FILE_FILTER = f"Gambit Pairing Files (*{SAVE_FILE_EXTENSION});;All Files (*)"
CSV_FILTER = "CSV Files (*.csv);;Text Files (*.txt)"

# Game outcome scores
WIN_SCORE = 1.0
DRAW_SCORE = 0.5
LOSS_SCORE = 0.0

# Bye scores (configurable per tournament)
FULL_POINT_BYE_SCORE = 1.0
HALF_POINT_BYE_SCORE = 0.5
ZERO_POINT_BYE_SCORE = 0.0
BYE_SCORE = FULL_POINT_BYE_SCORE  # Default for backward compatibility

# Result type constants (for display and serialization)
RESULT_WHITE_WIN = "1-0"
RESULT_DRAW = "0.5-0.5"
RESULT_BLACK_WIN = "0-1"
RESULT_WHITE_FORFEIT_WIN = "1-0 FF"  # White wins by forfeit (black didn't show)
RESULT_BLACK_FORFEIT_WIN = "0-1 FF"  # Black wins by forfeit (white didn't show)
RESULT_DOUBLE_FORFEIT = "0-0 FF"  # Both players forfeited
RESULT_BYE_FULL = "Bye (1.0)"
RESULT_BYE_HALF = "Bye (0.5)"
RESULT_BYE_ZERO = "Bye (0.0)"

# Outcome type categories (for internal logic)
OUTCOME_NORMAL_GAME = "normal"  # Regular over-the-board game
OUTCOME_FORFEIT_WIN = "forfeit_win"  # Win by opponent forfeit
OUTCOME_FORFEIT_LOSS = "forfeit_loss"  # Loss by own forfeit
OUTCOME_DOUBLE_FORFEIT = "double_forfeit"  # Both players forfeited
OUTCOME_BYE = "bye"  # Pairing-allocated bye

# Chess Federations
MODE_USCF = "USCF"
MODE_FIDE = "FIDE"
DEFAULT_MODE = MODE_USCF

# Tiebreaker Keys - USCF
TB_MEDIAN = "median"
TB_SOLKOFF = "solkoff"
TB_CUMULATIVE = "cumulative"
TB_CUMULATIVE_OPP = "cumulative_opp"
TB_SONNENBORN_BERGER = "sb"
TB_MOST_BLACKS = "most_blacks"
TB_HEAD_TO_HEAD = "h2h"  # Internal comparison key

# Tiebreaker Keys - FIDE
TB_BUCHHOLZ = "buchholz"  # Same as Solkoff, but FIDE terminology
TB_BUCHHOLZ_CUT_1 = "buchholz_cut1"
TB_BUCHHOLZ_MEDIAN_1 = "buchholz_median1"
TB_PROGRESSIVE = "progressive"  # Same as Cumulative, FIDE terminology
TB_DIRECT_ENCOUNTER = "direct_encounter"  # Head-to-head for FIDE
TB_WINS = "wins"  # FIDE 7.1: Number of rounds with win points
TB_GAMES_WON = "games_won"  # FIDE 7.2: Number of games won OTB
TB_BLACK_GAMES = "black_games"  # FIDE 7.3: Games played with black
TB_BLACK_WINS = "black_wins"  # FIDE 7.4: Games won with black
TB_ARO = "aro"  # Average Rating of Opponents

# Default display names for tiebreaks
TIEBREAK_NAMES = {
    # USCF Tiebreakers
    TB_MEDIAN: "Median",
    TB_SOLKOFF: "Solkoff",
    TB_CUMULATIVE: "Cumulative",
    TB_CUMULATIVE_OPP: "Cumulative Opp",
    TB_SONNENBORN_BERGER: "Sonnenborn-Berger",
    TB_MOST_BLACKS: "Most Blacks",
    # FIDE Tiebreakers
    TB_BUCHHOLZ: "Buchholz",
    TB_BUCHHOLZ_CUT_1: "Buchholz Cut-1",
    TB_BUCHHOLZ_MEDIAN_1: "Buchholz Median-1",
    TB_PROGRESSIVE: "Progressive",
    TB_DIRECT_ENCOUNTER: "Direct Encounter",
    TB_WINS: "Number of Wins",
    TB_GAMES_WON: "Games Won",
    TB_BLACK_GAMES: "Games with Black",
    TB_BLACK_WINS: "Wins with Black",
    TB_ARO: "Avg Rating of Opp",
}

# Default order used for sorting if not configured otherwise
DEFAULT_USCF_TIEBREAK_ORDER = [
    TB_MEDIAN,
    TB_SOLKOFF,
    TB_CUMULATIVE,
    TB_CUMULATIVE_OPP,
    TB_SONNENBORN_BERGER,
    TB_MOST_BLACKS,
]

DEFAULT_FIDE_TIEBREAK_ORDER = [
    TB_BUCHHOLZ_CUT_1,
    TB_BUCHHOLZ,
    TB_PROGRESSIVE,
    TB_SONNENBORN_BERGER,
    TB_WINS,
    TB_BLACK_WINS,
]

# Backward compatibility
DEFAULT_TIEBREAK_SORT_ORDER = DEFAULT_USCF_TIEBREAK_ORDER

UPDATE_URL = "https://api.github.com/repos/gambit-devs/Gambit-Pairing/releases/latest"
