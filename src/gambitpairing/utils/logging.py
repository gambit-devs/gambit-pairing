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
import os
import sys
from logging.handlers import RotatingFileHandler

from PyQt6 import QtCore

LOG_FMT = (
    "LVL: %(levelname)s | FILE: %(pathname)s | "
    "FUNC: %(funcName)s | LN:%(lineno)d | %(message)s"
)

LOG_FILE_NAME = "gambit-pairing.log"
MAX_BYTES = 5 * 1024 * 1024
BACKUP_COUNT = 5


def _get_log_dir() -> str | None:
    """Return a writable directory for logs, or None if unavailable."""
    paths = QtCore.QStandardPaths

    # Prefer AppDataLocation, fall back to Temp Location
    base = paths.writableLocation(paths.StandardLocation.AppDataLocation)
    if not base:
        print("logging to temporary location!")
        base = paths.writableLocation(paths.StandardLocation.TempLocation)
    if not base:
        raise RuntimeError("Could not find a writable log dir.")

    log_dir = os.path.join(base, "logs")
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


def _file_handler(formatter: logging.Formatter) -> logging.Handler:
    """Create a rotating file handler if possible."""
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
