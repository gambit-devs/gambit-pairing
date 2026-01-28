"""Directory management utilities for BBP file handling.

This module provides utilities for creating and managing directories for
BBP pairing files during comparison operations.
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

import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from gambitpairing.utils import setup_logger

logger = setup_logger(__name__)


def ensure_bbp_directory(base_path: Optional[str] = None) -> Path:
    """Create and return BBP pairings directory.

    If no base_path is specified, creates a timestamped directory under
    src/gambitpairing/testing/bbp_pairings/

    Args:
        base_path: Optional base path for BBP files

    Returns:
        Path to BBP directory
    """
    if base_path:
        bbp_dir = Path(base_path)
    else:
        # Default: src/gambitpairing/testing/bbp_pairings/[timestamp]_comparison/
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        bbp_dir = (
            Path("src")
            / "gambitpairing"
            / "testing"
            / "bbp_pairings"
            / f"{timestamp}_comparison"
        )

    # Create directory structure
    bbp_dir.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    (bbp_dir / "tournaments").mkdir(exist_ok=True)
    (bbp_dir / "bbp_executable_files").mkdir(exist_ok=True)
    (bbp_dir / "reports").mkdir(exist_ok=True)

    logger.info("Created BBP directory: %s", bbp_dir)

    return bbp_dir


def ensure_comparison_reports_directory(base_path: str = "testing") -> Path:
    """Create and return comparison reports directory.

    Args:
        base_path: Base path for testing directory

    Returns:
        Path to comparison reports directory
    """
    reports_dir = Path(base_path) / "comparison_reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Created comparison reports directory: %s", reports_dir)

    return reports_dir


def cleanup_bbp_files(
    directory: Path,
    keep_reports: bool = True,
    keep_tournaments: bool = False,
) -> None:
    """Clean up temporary BBP files.

    Args:
        directory: Directory to clean
        keep_reports: Whether to keep report files
        keep_tournaments: Whether to keep tournament data files
    """
    if not directory.exists():
        logger.warning("Directory does not exist: %s", directory)
        return

    # Clean BBP executable files (always safe to remove)
    bbp_files_dir = directory / "bbp_executable_files"
    if bbp_files_dir.exists():
        try:
            shutil.rmtree(bbp_files_dir)
            logger.info("Cleaned BBP executable files from: %s", bbp_files_dir)
        except Exception as e:
            logger.error("Failed to clean BBP files: %s", e)

    # Clean tournament files if not keeping
    if not keep_tournaments:
        tournaments_dir = directory / "tournaments"
        if tournaments_dir.exists():
            try:
                shutil.rmtree(tournaments_dir)
                logger.info("Cleaned tournament files from: %s", tournaments_dir)
            except Exception as e:
                logger.error("Failed to clean tournament files: %s", e)

    # Clean reports if not keeping
    if not keep_reports:
        reports_dir = directory / "reports"
        if reports_dir.exists():
            try:
                shutil.rmtree(reports_dir)
                logger.info("Cleaned report files from: %s", reports_dir)
            except Exception as e:
                logger.error("Failed to clean report files: %s", e)


def get_latest_comparison_directory(
    base_path: str = "src/gambitpairing/testing/bbp_pairings",
) -> Optional[Path]:
    """Get the most recently created comparison directory.

    Args:
        base_path: Base path to search for comparison directories

    Returns:
        Path to latest comparison directory or None
    """
    base = Path(base_path)

    if not base.exists():
        return None

    # Find all comparison directories (format: YYYYMMDD_HHMMSS_comparison)
    comparison_dirs = [
        d for d in base.iterdir() if d.is_dir() and d.name.endswith("_comparison")
    ]

    if not comparison_dirs:
        return None

    # Sort by modification time (most recent first)
    comparison_dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)

    latest = comparison_dirs[0]
    logger.info("Latest comparison directory: %s", latest)

    return latest


def archive_comparison_results(
    source_dir: Path,
    archive_base: str = "src/gambitpairing/testing/comparison_archives",
) -> Path:
    """Archive a comparison results directory.

    Args:
        source_dir: Directory to archive
        archive_base: Base directory for archives

    Returns:
        Path to archived directory
    """
    archive_dir = Path(archive_base)
    archive_dir.mkdir(parents=True, exist_ok=True)

    # Create archive name based on source directory
    archive_name = source_dir.name
    archive_path = archive_dir / archive_name

    # If archive already exists, add suffix
    counter = 1
    while archive_path.exists():
        archive_path = archive_dir / f"{archive_name}_{counter}"
        counter += 1

    try:
        shutil.copytree(source_dir, archive_path)
        logger.info("Archived comparison results to: %s", archive_path)
        return archive_path
    except Exception as e:
        logger.error("Failed to archive comparison results: %s", e)
        raise


def create_comparison_session(
    session_name: Optional[str] = None,
    base_path: str = "src/gambitpairing/testing/bbp_pairings",
) -> Path:
    """Create a new comparison session directory.

    Args:
        session_name: Optional custom name for session
        base_path: Base path for comparison directories

    Returns:
        Path to session directory
    """
    if session_name:
        session_dir = Path(base_path) / session_name
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = Path(base_path) / f"{timestamp}_comparison"

    # Create directory structure
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "tournaments").mkdir(exist_ok=True)
    (session_dir / "bbp_executable_files").mkdir(exist_ok=True)
    (session_dir / "reports").mkdir(exist_ok=True)

    # Create a session metadata file
    metadata = {
        "created": datetime.now().isoformat(),
        "session_name": session_name or f"{timestamp}_comparison",
    }

    import json

    metadata_file = session_dir / "session_metadata.json"
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    logger.info("Created comparison session: %s", session_dir)

    return session_dir
