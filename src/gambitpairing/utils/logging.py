"""Logging setup utilities."""

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


import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys
import tempfile

LOG_FMT = (
    "LVL: %(levelname)s | FILE: %(pathname)s | "
    "FUNC: %(funcName)s | LN:%(lineno)d | %(message)s"
)

LOG_FILE_NAME = "gambit-pairing.log"
MAX_BYTES = 5 * 1024 * 1024
BACKUP_COUNT = 5


def _get_log_dir() -> str:
    """Return a writable directory for logs, or None if unavailable."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA", tempfile.gettempdir())
    elif sys.platform == "darwin":
        base = str(Path.home() / "Library" / "Logs")
    else:
        base = os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local" / "state"))
    log_dir = os.path.join(base, "gambit-pairing", "logs")
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


def _file_handler(formatter: logging.Formatter) -> logging.Handler:
    """Create a rotating file handler if possible."""
    try:
        log_dir = _get_log_dir()
        log_path = os.path.join(log_dir, LOG_FILE_NAME)
        handler = RotatingFileHandler(
            log_path,
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
        handler.setFormatter(formatter)
        return handler
    except (OSError, RuntimeError):
        return logging.NullHandler()


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Create or configure a logger with console + optional file logging."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # SETUP for logging to file and console n' crap
    formatter = logging.Formatter(LOG_FMT)
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    console.setLevel(level)
    logger.addHandler(console)
    file_handler = _file_handler(formatter)
    if file_handler:
        logger.addHandler(file_handler)

    logger.debug("Logger %s initialized", name)
    return logger
