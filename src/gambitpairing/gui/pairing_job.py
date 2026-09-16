"""Qt adapter for isolated pairing generation with responsive cancellation."""

import multiprocessing
import os
import shutil
import signal
import subprocess

from PyQt6 import QtCore, QtWidgets

from gambitpairing.controllers.tournament.pairing_job import run_pairing_process
from gambitpairing.utils import setup_logger

logger = setup_logger(__name__)


def generate_with_progress(parent, document, round_index):
    round_number = round_index + 1
    context = multiprocessing.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(
        target=run_pairing_process, args=(sender, document, round_index)
    )
    progress = QtWidgets.QProgressDialog("Generating pairings…", "Cancel", 0, 0, parent)
    progress.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)
    progress.setMinimumDuration(0)
    result = {}
    timer = QtCore.QTimer(progress)

    def poll():
        if receiver.poll():
            try:
                result.update(receiver.recv())
            except EOFError:
                logger.exception(
                    "Pairing generation worker closed its pipe without a result: "
                    "round=%s",
                    round_number,
                )
                result["error"] = "Pairing process exited without a result"
            if result.get("error"):
                logger.error(
                    "Pairing generation worker reported failure: round=%s; "
                    "see worker traceback for the original exception",
                    round_number,
                )
            progress.accept()
        elif not process.is_alive():
            logger.error(
                "Pairing generation worker exited without a result: round=%s "
                "exit_code=%s",
                round_number,
                process.exitcode,
            )
            result["error"] = "Pairing process exited without a result"
            progress.accept()

    timer.timeout.connect(poll)
    process.start()
    sender.close()
    timer.start(25)
    try:
        progress.exec()
    finally:
        timer.stop()
        if process.is_alive():
            if os.name == "posix" and process.pid is not None:
                try:
                    # Only signal a process group actually owned by this job.
                    if os.getpgid(process.pid) == process.pid:
                        os.killpg(process.pid, signal.SIGTERM)
                    else:
                        process.terminate()
                except ProcessLookupError:
                    pass
            elif (
                os.name == "nt" and process.pid is not None and shutil.which("taskkill")
            ):
                try:
                    subprocess.run(
                        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                        capture_output=True,
                        timeout=5,
                        check=False,
                    )
                except (OSError, subprocess.SubprocessError):
                    process.terminate()
            else:
                process.terminate()
        process.join(timeout=1)
        if process.is_alive():
            process.kill()
            process.join(timeout=1)
        receiver.close()
        progress.deleteLater()
    return result or {"cancelled": True}
