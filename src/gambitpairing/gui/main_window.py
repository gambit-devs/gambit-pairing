"""Compatibility import for the active Qt main window.

The MVC refactor started a new ``main_window.py`` shell before the controller
stack was complete. Keep this module importable while the working window lives
in ``mainwindow.py``.
"""

from .mainwindow import GambitPairingMainWindow
