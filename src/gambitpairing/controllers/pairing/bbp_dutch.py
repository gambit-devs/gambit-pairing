"""Production adapter for the BBP Pairings Dutch Swiss engine."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Iterable, List, Optional, Protocol, Tuple, Union

from gambitpairing.compatibility.bbp import (
    build_bbp_pairing_trf,
    ensure_bbp_pairing_numbers,
    parse_bbp_pairing_output,
)
from gambitpairing.models.player import Player
from gambitpairing.utils import setup_logger

logger = setup_logger(__name__)

PathLike = Union[str, os.PathLike[str]]


class BBPPairingError(RuntimeError):
    """Base error for an unavailable or unsuccessful BBP pairing request."""


class BBPUnavailableError(BBPPairingError):
    """Raised when no usable BBP executable is installed."""


class BBPExecutionError(BBPPairingError):
    """Raised when BBP rejects a request or cannot complete it."""


class BBPPairingBackend(Protocol):
    """Structural interface used by the round controller and its tests."""

    def generate_pairings(
        self,
        active_players: Iterable[Player],
        current_round: int,
        total_rounds: int,
        all_players: Optional[Iterable[Player]] = None,
    ) -> Tuple[List[Tuple[Player, Player]], Optional[Player]]:
        """Generate one Dutch Swiss round."""
        ...


class BBPPairingEngine:
    """Run the upstream BBP Dutch engine and translate its result to Gambit.

    The application prefers this engine for Dutch Swiss rounds.  The native
    implementation remains the caller's fallback, so a missing executable or
    a malformed/unsupported tournament state does not strand a tournament.
    """

    EXECUTABLE_ENV = "GAMBIT_BBP_EXECUTABLE"
    BACKEND_ENV = "GAMBIT_PAIRING_ENGINE"
    INITIAL_COLOR_ENV = "GAMBIT_BBP_INITIAL_COLOR"
    DEFAULT_TIMEOUT_SECONDS = 120.0

    def __init__(
        self,
        executable: Optional[PathLike] = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        initial_color: Optional[str] = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

        self.timeout_seconds = float(timeout_seconds)
        self.initial_color = (
            initial_color or os.environ.get(self.INITIAL_COLOR_ENV) or "white1"
        )
        self.executable = self.resolve_executable(executable)

    @property
    def enabled(self) -> bool:
        """Whether BBP is preferred over the native engine."""
        return os.environ.get(self.BACKEND_ENV, "bbp").strip().lower() != "native"

    @property
    def available(self) -> bool:
        """Whether a BBP executable was found during initialization."""
        return self.executable is not None

    @classmethod
    def resolve_executable(cls, executable: Optional[PathLike] = None) -> Optional[str]:
        """Resolve an explicit, packaged, or PATH-provided BBP executable."""
        explicit = executable or os.environ.get(cls.EXECUTABLE_ENV)
        if explicit:
            resolved = cls._resolve_candidate(os.fspath(explicit))
            if resolved is None:
                logger.warning("Configured BBP executable was not found: %s", explicit)
            return resolved

        for command_name in ("bbpPairings", "bbpPairings.exe"):
            resolved = shutil.which(command_name)
            if resolved:
                return resolved

        package_root = Path(__file__).resolve().parents[2]
        search_roots = [
            package_root / "resources" / "bin",
            Path.cwd(),
        ]
        if getattr(sys, "frozen", False):
            search_roots.insert(0, Path(sys.executable).resolve().parent)
        bundle_root = getattr(sys, "_MEIPASS", None)
        if bundle_root:
            search_roots.insert(0, Path(bundle_root))

        for root in search_roots:
            for filename in ("bbpPairings", "bbpPairings.exe"):
                resolved = cls._resolve_candidate(root / filename)
                if resolved is not None:
                    return resolved
        return None

    @staticmethod
    def _resolve_candidate(candidate: PathLike) -> Optional[str]:
        candidate_path = Path(candidate)
        if candidate_path.is_file() and os.access(candidate_path, os.X_OK):
            return str(candidate_path.resolve())
        return shutil.which(os.fspath(candidate))

    def generate_pairings(
        self,
        active_players: Iterable[Player],
        current_round: int,
        total_rounds: int,
        all_players: Optional[Iterable[Player]] = None,
    ) -> Tuple[List[Tuple[Player, Player]], Optional[Player]]:
        """Generate one round of BBP Dutch pairings.

        ``all_players`` preserves withdrawn players and their past results in
        the TRF input.  Only ``active_players`` may appear in the returned
        pairings; inactive roster entries are represented with a future bye.
        """
        if not self.enabled:
            raise BBPUnavailableError("BBP backend disabled by configuration")
        if self.executable is None:
            raise BBPUnavailableError(
                "BBP executable not found; set GAMBIT_BBP_EXECUTABLE or install "
                "bbpPairings on PATH"
            )

        active = list(active_players)
        roster = list(all_players) if all_players is not None else list(active)
        roster_by_id = {player.id: player for player in roster}
        if len(roster_by_id) != len(roster):
            raise BBPExecutionError("BBP roster contains duplicate player IDs")
        if any(player.id not in roster_by_id for player in active):
            raise BBPExecutionError("Every active player must be in the BBP roster")
        if len({player.id for player in active}) != len(active):
            raise BBPExecutionError("Active players contain duplicate IDs")

        active_ids = {player.id for player in active}
        inactive = [player for player in roster if player.id not in active_ids]

        try:
            ensure_bbp_pairing_numbers(roster)
            trf_content = build_bbp_pairing_trf(
                roster,
                total_rounds=total_rounds,
                current_round=current_round,
                initial_color=self.initial_color,
                inactive_players=inactive,
            )
        except (TypeError, ValueError) as error:
            raise BBPExecutionError(f"Unable to build BBP input: {error}") from error

        with tempfile.TemporaryDirectory(prefix="gambit-bbp-") as temporary_directory:
            input_path = Path(temporary_directory) / "pairing.trf"
            input_path.write_text(trf_content, encoding="utf-8")
            command = [str(self.executable), "--dutch", str(input_path), "-p"]

            try:
                completed = subprocess.run(
                    command,
                    cwd=temporary_directory,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    check=False,
                    timeout=self.timeout_seconds,
                )
            except FileNotFoundError as error:
                raise BBPUnavailableError(
                    f"BBP executable could not be started: {self.executable}"
                ) from error
            except subprocess.TimeoutExpired as error:
                raise BBPExecutionError(
                    f"BBP pairing exceeded the {self.timeout_seconds:g}-second timeout"
                ) from error
            except OSError as error:
                raise BBPExecutionError(
                    f"Unable to run BBP Pairings: {error}"
                ) from error

        if completed.returncode != 0:
            details = completed.stderr.strip() or completed.stdout.strip()
            raise BBPExecutionError(
                f"BBP Pairings exited with status {completed.returncode}"
                + (f": {details}" if details else "")
            )

        try:
            pairings, bye_player = parse_bbp_pairing_output(
                completed.stdout,
                roster,
            )
        except ValueError as error:
            raise BBPExecutionError(f"Invalid BBP pairing output: {error}") from error

        paired_ids = {player.id for pair in pairings for player in pair}
        if bye_player is not None:
            paired_ids.add(bye_player.id)
        if paired_ids - active_ids:
            raise BBPExecutionError("BBP paired a withdrawn player")
        if len(paired_ids) != len(active):
            raise BBPExecutionError(
                "BBP returned an incomplete round: "
                f"{len(paired_ids)} of {len(active)} active players assigned"
            )
        if len(active) % 2 == 0 and bye_player is not None:
            raise BBPExecutionError("BBP returned a bye for an even active roster")
        if len(active) % 2 == 1 and bye_player is None:
            raise BBPExecutionError("BBP did not return a bye for an odd active roster")

        return pairings, bye_player
