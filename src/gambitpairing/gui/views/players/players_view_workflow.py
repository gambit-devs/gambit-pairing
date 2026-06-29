"""Pure workflow and projection helpers for PlayersView."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PlayerTableRowProjection:
    name: str
    rating: str
    age: str
    status: str
    tooltip: str
    inactive: bool


@dataclass(frozen=True)
class PlayerPrompt:
    title: str
    message: str


def build_player_tooltip(player: Any) -> str:
    tooltip_parts = [f"ID: {player.id}"]
    if player.gender:
        tooltip_parts.append(f"Gender: {player.gender}")
    if player.dob:
        tooltip_parts.append(f"Date of Birth: {player.dob}")
    if player.phone:
        tooltip_parts.append(f"Phone: {player.phone}")
    if player.email:
        tooltip_parts.append(f"Email: {player.email}")
    if player.federation:
        tooltip_parts.append(f"Federation: {player.federation}")
    if getattr(player, "fide_id", None):
        tooltip_parts.append(f"FIDE ID: {player.fide_id}")
    if getattr(player, "fide_title", None):
        tooltip_parts.append(f"Title: {player.fide_title}")
    if getattr(player, "fide_standard", None) is not None:
        tooltip_parts.append(f"Std: {player.fide_standard}")
    if getattr(player, "fide_rapid", None) is not None:
        tooltip_parts.append(f"Rapid: {player.fide_rapid}")
    if getattr(player, "fide_blitz", None) is not None:
        tooltip_parts.append(f"Blitz: {player.fide_blitz}")
    if getattr(player, "birth_year", None) is not None:
        tooltip_parts.append(f"Birth Year: {player.birth_year}")
    if getattr(player, "gender", None):
        tooltip_parts.append(f"Gender: {player.gender}")
    return "\n".join(tooltip_parts)


def project_player_table_row(player: Any) -> PlayerTableRowProjection:
    age = player.age
    return PlayerTableRowProjection(
        name=player.name,
        rating=str(player.rating or ""),
        age=str(age) if age is not None else "",
        status="Active" if player.is_active else "Inactive",
        tooltip=build_player_tooltip(player),
        inactive=not player.is_active,
    )


def build_remove_player_prompt(player_name: str) -> PlayerPrompt:
    return PlayerPrompt(
        title="Remove Player",
        message=f"Remove player '{player_name}' permanently?",
    )


def build_duplicate_player_prompt(player_name: str) -> PlayerPrompt:
    return PlayerPrompt(
        title="Duplicate Player",
        message=f"Player '{player_name}' already exists.",
    )


def build_import_success_history(added_count: int, file_name: str) -> str:
    return f"Imported {added_count} players from {file_name}."


def build_import_success_notification(added_count: int, file_name: str) -> str:
    return f"Imported {added_count} players from {Path(file_name).name}"


def build_import_empty_prompt() -> PlayerPrompt:
    return PlayerPrompt(
        title="Import Notice",
        message="No new players were imported. Check for empty names or duplicates.",
    )


def build_export_unavailable_prompt() -> PlayerPrompt:
    return PlayerPrompt(
        title="Export Error",
        message="No players available to export.",
    )


def build_export_success_status(filename: str) -> str:
    return f"Players exported to {filename}"
