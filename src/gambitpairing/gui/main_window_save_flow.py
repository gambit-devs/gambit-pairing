"""Pure helpers for MainWindow dirty-save prompt decisions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


SavePromptChoice = Literal["save", "discard", "cancel"]


@dataclass(frozen=True)
class UnsavedChangesPrompt:
    title: str
    message: str
    save_label: str
    discard_label: str
    cancel_label: str


def build_unsaved_changes_prompt() -> UnsavedChangesPrompt:
    return UnsavedChangesPrompt(
        title="Unsaved Changes",
        message="You have unsaved changes. Do you want to save them?",
        save_label="Save",
        discard_label="Close without Saving",
        cancel_label="Cancel",
    )


def should_prompt_for_unsaved_changes(is_dirty: bool) -> bool:
    return is_dirty


def should_continue_after_save_prompt(
    choice: SavePromptChoice, save_succeeded: bool
) -> bool:
    if choice == "save":
        return save_succeeded
    if choice == "discard":
        return True
    return False
