"""Restart the Gambit Pairing program, to reload changes."""

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
import subprocess
import sys
import time

from PyQt6.QtWidgets import QApplication

from gambitpairing.utils.logging import setup_logger


def restart_application() -> bool:
    """Restart the entire application to ensure clean state reload.

    Raises
    ------
    an exception if one is raised when trying to restart
    """
    # Get the current application instance
    app = QApplication.instance()
    if app is None:
        logging.error("app is None in restart_application")
        return False

    # Get command line arguments for restart
    args = sys.argv[:]

    # Close all windows and quit the application
    app.closeAllWindows()
    app.quit()

    # Small delay to ensure cleanup
    time.sleep(0.1)

    # Restart the application
    try:
        if sys.platform == "win32":
            subprocess.Popen([sys.executable] + args)
        else:
            # For Linux/Unix systems, use os.execv for cleaner restart
            os.execv(sys.executable, [sys.executable] + args)
        return True
    except Exception as e:
        log = setup_logger(__name__)
        log.error(f"Failed to restart application: {e}")
        raise e
