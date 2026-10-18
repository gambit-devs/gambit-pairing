"""Background checks and downloads for the locally kept player lists.

One :class:`PlayerListUpdater` serves the whole app, so the startup trigger,
the Add Player dialog and the Player Lists dialog share one queue and never
check the same list twice at once. The work runs in a ``QThread``; callers
only connect to its signals.
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

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from typing import Optional

from PyQt6 import QtCore, QtWidgets
import httpx

from gambitpairing.player_lists.catalog import PlayerListSpec, get_player_list
from gambitpairing.player_lists.store import PlayerListStore, utc_now
from gambitpairing.player_lists import updates
from gambitpairing.player_lists.updates import (
    CheckOutcome,
    check_and_update,
    format_progress,
)
from gambitpairing.utils import setup_logger

logger = setup_logger(__name__)

# How long shutdown waits for a running download to stop.
SHUTDOWN_WAIT_MS = 5000


class PlayerListUpdateWorker(QtCore.QObject):
    """Check (and when needed download) a batch of lists in a worker thread."""

    status = QtCore.pyqtSignal(str, str)  # (list key, status text)
    list_done = QtCore.pyqtSignal(object)  # CheckOutcome
    finished = QtCore.pyqtSignal()

    def __init__(
        self,
        store: PlayerListStore,
        specs: Sequence[PlayerListSpec],
        force: bool,
        client_factory: Callable[[], httpx.Client],
    ) -> None:
        super().__init__()
        self._store = store
        self._specs = tuple(specs)
        self._force = force
        self._client_factory = client_factory
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def is_cancelled(self) -> bool:
        return self._cancelled

    @QtCore.pyqtSlot()
    def run(self) -> None:
        try:
            with self._client_factory() as client:
                for spec in self._specs:
                    if self._cancelled:
                        break
                    self.status.emit(spec.key, f"{spec.name}: starting")
                    outcome = check_and_update(
                        self._store,
                        spec,
                        client,
                        force=self._force,
                        progress=lambda done, total, spec=spec: self.status.emit(
                            spec.key, format_progress(spec, done, total)
                        ),
                        cancelled=self.is_cancelled,
                        status=lambda text, spec=spec: self.status.emit(spec.key, text),
                    )
                    self.list_done.emit(outcome)
        except Exception:  # never let a worker exception escape the thread
            logger.exception("Player list update failed")
        finally:
            self.finished.emit()


class PlayerListUpdater(QtCore.QObject):
    """App-wide queue for player list checks."""

    busy_changed = QtCore.pyqtSignal(bool)
    status = QtCore.pyqtSignal(str, str)  # (list key, status text)
    list_updated = QtCore.pyqtSignal(object)  # CheckOutcome

    def __init__(
        self,
        store: Optional[PlayerListStore] = None,
        client_factory: Optional[Callable[[], httpx.Client]] = None,
        parent: Optional[QtCore.QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.store = store or PlayerListStore()
        self._client_factory = client_factory
        self._thread: Optional[QtCore.QThread] = None
        self._worker: Optional[PlayerListUpdateWorker] = None
        self._running: set[str] = set()
        self._pending: dict[str, bool] = {}  # key -> forced
        self._shutting_down = False

    @property
    def is_busy(self) -> bool:
        return self._thread is not None

    def is_active(self, key: str) -> bool:
        return key in self._running or key in self._pending

    def run_scheduled_checks(self) -> list[str]:
        """Trigger: check the selected lists whose 24-hour interval has passed.

        Returns the keys queued. Nothing happens when no list is selected.
        """
        if not self.store.selected_keys():
            return []
        due = [
            spec.key
            for spec in self.store.due_for_check(utc_now())
            if not self.is_active(spec.key)
        ]
        self._enqueue(due, force=False)
        return due

    def update_now(self, keys: Iterable[str]) -> list[str]:
        """Check the given lists now, ignoring the 24-hour interval."""
        keys = [key for key in keys if key not in self._running]
        self._enqueue(keys, force=True)
        return keys

    def shutdown(self) -> None:
        """Cancel queued work and stop the running download."""
        self._shutting_down = True
        self._pending.clear()
        thread, worker = self._thread, self._worker
        if worker:
            worker.cancel()
        if thread and thread.isRunning():
            thread.quit()
            if not thread.wait(SHUTDOWN_WAIT_MS):
                # A request is stuck; stale temporary files are removed on
                # the next check.
                thread.terminate()
                thread.wait(200)

    def _enqueue(self, keys: Sequence[str], force: bool) -> None:
        if self._shutting_down:
            return
        for key in keys:
            self._pending[key] = self._pending.get(key, False) or force
        self._start_next()

    def _start_next(self) -> None:
        if self._thread is not None or not self._pending or self._shutting_down:
            return
        force = any(self._pending.values())
        keys = [key for key, forced in self._pending.items() if forced == force]
        for key in keys:
            del self._pending[key]
        specs = [get_player_list(key) for key in keys]
        self._running = set(keys)

        worker = PlayerListUpdateWorker(
            self.store,
            specs,
            force,
            self._client_factory or updates.create_http_client,
        )
        thread = QtCore.QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.status.connect(self.status)
        worker.list_done.connect(self._on_list_done)
        worker.finished.connect(thread.quit)
        thread.finished.connect(self._on_thread_finished)
        self._thread, self._worker = thread, worker
        self.busy_changed.emit(True)
        thread.start()

    @QtCore.pyqtSlot(object)
    def _on_list_done(self, outcome: CheckOutcome) -> None:
        self._running.discard(outcome.key)
        self.list_updated.emit(outcome)

    @QtCore.pyqtSlot()
    def _on_thread_finished(self) -> None:
        if self._worker:
            self._worker.deleteLater()
        if self._thread:
            self._thread.deleteLater()
        self._thread = None
        self._worker = None
        self._running.clear()
        if self._pending and not self._shutting_down:
            self._start_next()
        else:
            self.busy_changed.emit(False)


_UPDATER: Optional[PlayerListUpdater] = None


def player_list_updater() -> PlayerListUpdater:
    """Return the app-wide updater, creating it on first use."""
    global _UPDATER
    if _UPDATER is None:
        app = QtWidgets.QApplication.instance()
        _UPDATER = PlayerListUpdater(parent=app)
        if app is not None:
            app.aboutToQuit.connect(_UPDATER.shutdown)
    return _UPDATER
