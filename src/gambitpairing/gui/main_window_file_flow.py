"""Pure save/load workflow helpers for MainWindow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ConfirmationPrompt:
    title: str
    message: str


@dataclass(frozen=True)
class FileFlowMessage:
    title: str
    message: str


def should_request_save_path(current_filepath: str | None, save_as: bool) -> bool:
    return current_filepath is None or save_as


def build_overwrite_confirmation_prompt() -> ConfirmationPrompt:
    return ConfirmationPrompt(
        title="will overwrite tournament",
        message="Is that what you want?",
    )


def build_save_status(filepath: str) -> str:
    return f"Tournament saved to {filepath}"


def build_save_history(filepath: str) -> str:
    return f"Tournament saved as: {Path(filepath).name}"


def build_save_error_prompt(error: Exception) -> FileFlowMessage:
    return FileFlowMessage(
        title="Save Error",
        message=f"Could not save tournament:\n{error}",
    )


def build_load_success_history(filepath: str) -> str:
    return f"--- Tournament loaded from {Path(filepath).name} ---"


def build_load_success_status(tournament_name: str) -> str:
    return f"Loaded tournament: {tournament_name}"


def build_load_error_prompt(error: Exception) -> FileFlowMessage:
    return FileFlowMessage(
        title="Load Error",
        message=f"Could not load tournament file:\n{error}",
    )
