"""Player controller for managing players."""


def import_players_from_csv() -> List[Players] | None:
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
    List[Players] | None
        The added players

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
    added_players_count = 0
    players: Players | None = None
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

            self.tournament.players[player.id] = player
            added_players_count += 1

    return (added_players_count, players)


def export_players_to_csv(players: Players, file_path: Path) -> None:
    """Export all players to a CSV file at file_path.

    Writes one row per player sorted alphabetically by name, with
    columns: Name, Rating, Gender, Date of Birth, Phone, Email, Club,
    Federation, Active, ID.

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
