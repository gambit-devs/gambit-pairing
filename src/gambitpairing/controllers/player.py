"""Player controller for managing chess players."""

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


def import_players_from_csv() -> Players | None:
    """Import players from a CSV file chosen via a file dialog.

    Expects a CSV with at minimum a ``Name`` column. Optionally reads
    ``Rating``, ``Gender``, ``Date of Birth``, ``Phone``, ``Email``,
    ``Club``, and ``Federation`` columns. Skips rows with empty names
    or names that already exist in the tournament. Uses
    ``create_player`` to construct each player object.

    Emits ``dirty`` and calls ``refresh_player_list`` if at least one
    player was added. Shows a success notification via
    ``show_notification`` if available, otherwise falls back to a
    ``QMessageBox``.

    Returns
    -------
    tuple(int, Players)
        tuple of the number of players found and Players found.

    Raises
    ------
    FileNotFoundError
        File Not Found, The file was not found.
    PermissionError
        Cannot read this file.
    UnicodeDecodeError:
        Encoding error
    CsvError
        Malformed CSV file.
    OSError
        File Error
    """
    player_count = 0
    players: Players = []
    with open(filename, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("Name")
            if not name or any(
                p.name == name for p in self.tournament.players.values()
            ):
                continue  # Skip empty names or duplicates
            rating_str = row.get("Rating")
            rating = int(rating_str) if rating_str and rating_str.isdigit() else None

            # Use factory to create player
            player = create_player(
                name=name,
                rating=rating,
                gender=row.get("Gender"),
                date_of_birth=row.get("Date of Birth"),
                phone=row.get("Phone"),
                email=row.get("Email"),
                federation=row.get("Federation"),
            )

            players.append(player)
            player_count += 1

    return (player_count, players)


def export_players_to_csv(players: Players, file_path: Path) -> None:
    """Export all players to a CSV file at file_path.

    Writes one row per player sorted alphabetically by name, with
    columns: Name, Rating, Gender, Date of Birth, Phone, Email, Club,
    Federation, Active, ID.

    Parameters
    ----------
    players : Players
        An iterable of players to export
    file_path : Path
        The path to write csv file

    Raises
    ------
    FileNotFoundError
        File Not Found, The file was not found.
    PermissionError
        Cannot read this file.
    UnicodeDecodeError:
        Encoding error
    CsvError
        Malformed CSV file.
    OSError
        File Error
    RuntimeError
        if ether players or file_path are not provided.
    """
    if not filename:
        raise RuntimeError("export_players_csv(...) needs a filename.")
    if not players:
        raise RuntimeError("export_players_csv(...) needs a players.")

    with open(filename, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "Name",
                "Rating",
                "Gender",
                "Date of Birth",
                "Phone",
                "Email",
                "Federation",
                "Active",
                "ID",
            ]
        )
        for player in sorted(
            list(self.tournament.players.values()), key=lambda p: p.name
        ):
            writer.writerow(
                [
                    player.name,
                    player.rating if player.rating is not None else "",
                    player.gender or "",
                    player.dob or "",
                    player.phone or "",
                    player.email or "",
                    player.federation or "",
                    "Yes" if player.is_active else "No",
                    player.id,
                ]
            )
