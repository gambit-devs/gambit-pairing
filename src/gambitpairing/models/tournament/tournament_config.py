"""TournamentConfig data class, contains tournament "settings"."""

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

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from gambitpairing.constants import (
    DEFAULT_FIDE_TIEBREAK_ORDER,
    DEFAULT_MODE,
    DEFAULT_USCF_TIEBREAK_ORDER,
    MODE_FIDE,
    TB_BUCHHOLZ,
    TB_BUCHHOLZ_CUT_1,
    TB_BUCHHOLZ_MEDIAN_1,
    TB_SONNENBORN_BERGER,
    TB_DIRECT_ENCOUNTER,
    TB_HEAD_TO_HEAD,
)


@dataclass(frozen=False)
class TournamentConfig:
    """Tournament configuration settings.

    Attributes
    ----------
    name : str
        Tournament name.
    num_rounds : int
        Number of rounds in the tournament.
    pairing_system : str
        Pairing system used for generating pairings.
    use_experimental_dutch : bool
        Use Gambit's native Dutch engine instead of the primary BBP engine.
    tiebreak_order : list of str
        Ordered list of tiebreak criteria in priority order.
    tournament_over : bool
        Indicates whether the tournament is complete.
    """

    name: str
    num_rounds: int
    pairing_system: str = "dutch_swiss"
    tournament_mode: str = DEFAULT_MODE
    fide_strict: bool = False
    tiebreak_order: Optional[List[str]] = None
    # Is the tournament complete?
    tournament_over: bool = False
    use_experimental_dutch: bool = False
    rules_version: str = "2026"
    unresolved_ties: str = "shared"

    def __post_init__(self) -> None:
        """Choose federation defaults without sharing mutable lists."""
        if self.rules_version not in {"2026", "legacy-unspecified"}:
            raise ValueError("Unsupported rules version")
        if self.unresolved_ties != "shared":
            raise ValueError("Only shared unresolved standings ranks are supported")
        # ``bbp_dutch`` was briefly exposed as a separate pairing-system ID.
        # Normalize it at the model boundary so the rest of the application
        # has one Dutch format and one explicit engine-selection flag.
        if self.pairing_system == "bbp_dutch":
            self.pairing_system = "dutch_swiss"
            self.use_experimental_dutch = False
        self.use_experimental_dutch = bool(self.use_experimental_dutch)

        if self.tiebreak_order is None:
            defaults = (
                DEFAULT_FIDE_TIEBREAK_ORDER
                if self.tournament_mode == MODE_FIDE
                else DEFAULT_USCF_TIEBREAK_ORDER
            )
            self.tiebreak_order = list(defaults)
            if self.pairing_system == "round_robin":
                self.tiebreak_order = [
                    TB_SONNENBORN_BERGER,
                    (
                        TB_DIRECT_ENCOUNTER
                        if self.tournament_mode == MODE_FIDE
                        else TB_HEAD_TO_HEAD
                    ),
                ]
        else:
            self.tiebreak_order = list(self.tiebreak_order or [])

        if self.tournament_mode == MODE_FIDE and self.pairing_system == "round_robin":
            self.tiebreak_order = [
                key
                for key in self.tiebreak_order
                if key not in {TB_BUCHHOLZ, TB_BUCHHOLZ_CUT_1, TB_BUCHHOLZ_MEDIAN_1}
            ]

    @property
    def fide_strict_mode(self) -> bool:
        """Legacy alias retained for older saved documents and callers."""
        return self.fide_strict

    @fide_strict_mode.setter
    def fide_strict_mode(self, value: bool) -> None:
        self.fide_strict = bool(value)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize configuration to dictionary."""
        return {
            "name": self.name,
            "num_rounds": self.num_rounds,
            "pairing_system": self.pairing_system,
            "use_experimental_dutch": self.use_experimental_dutch,
            "tournament_mode": self.tournament_mode,
            "fide_strict": self.fide_strict,
            "fide_strict_mode": self.fide_strict,
            "tiebreak_order": list(self.tiebreak_order or []),
            "tournament_over": self.tournament_over,
            "rules_version": self.rules_version,
            "unresolved_ties": self.unresolved_ties,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TournamentConfig":
        """Deserialize configuration from dictionary."""
        fide_strict = data.get("fide_strict", data.get("fide_strict_mode", False))
        pairing_system = data.get("pairing_system", "dutch_swiss")
        if pairing_system == "bbp_dutch":
            # Documents written by the first BBP integration used a separate
            # pairing-system ID. Preserve their primary-BBP behavior.
            pairing_system = "dutch_swiss"
            use_experimental_dutch = False
        else:
            # Before the engine choice was persisted, ``dutch_swiss`` meant
            # Gambit's native implementation. Preserve that behavior for
            # older documents while new documents always include the flag.
            use_experimental_dutch = data.get(
                "use_experimental_dutch", pairing_system == "dutch_swiss"
            )
        return cls(
            name=data.get("name", "Untitled Tournament"),
            num_rounds=data["num_rounds"],
            pairing_system=pairing_system,
            use_experimental_dutch=use_experimental_dutch,
            tournament_mode=data.get("tournament_mode", DEFAULT_MODE),
            fide_strict=fide_strict,
            tiebreak_order=(
                list(data["tiebreak_order"]) if "tiebreak_order" in data else None
            ),
            tournament_over=data.get("tournament_over", False),
            rules_version=data.get("rules_version", "legacy-unspecified"),
            unresolved_ties=data.get("unresolved_ties", "shared"),
        )


#  LocalWords:  TournamentConfig PairingSystemABC
