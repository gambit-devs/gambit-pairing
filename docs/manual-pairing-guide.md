# Manual Pairing Dialog Guide

The Manual Pairing Dialog provides a powerful and flexible interface for creating, editing, and managing tournament pairings. This guide explains how to use its features to efficiently manage your tournament rounds.

## The Interface

The dialog is divided into three main sections:

1.  **Player Pool (Left, Fixed)**: This panel lists all players who are not yet paired for the current round. You can search, filter, and select players from this list.
2.  **Pairings Panel (Right)**: This is where you build the pairings for the round. It includes a toolbar for common actions and a table displaying the current pairings.
3.  **Bye Player Area (Bottom of Player Pool)**: A dedicated spot to assign a bye to a player for the round.
---

## Core Features

### Creating Pairings with Selection

The Player Pool is selection-only. Select a player, then click an empty **White**
or **Black** cell in the Pairings Table to place them. An empty row will be
created if needed.

You can drag players already in the Pairings Table between cells or pairings to
change assignments. Dragging a paired player back to the Player Pool removes
that assignment.

### Auto-Pairing

-   **Auto-Pair a Single Player**: Double-clicking a player in the Player Pool will automatically find the best available opponent for them based on the pairing algorithm and create a new pairing.
-   **Auto-Pair All Remaining Players**: Click the **"Auto Pair"** button in the toolbar (or press `Ctrl+A`) to automatically pair all players remaining in the Player Pool using the Dutch Swiss pairing algorithm.

### Managing Pairings

-   **Edit a Pairing**: Drag a player from one column to another (e.g., White to Black) within the same pairing to swap their colors. Drag a player from one pairing to another to change their opponent.
-   **Delete a Pairing**:
    -   Right-click the pairing in the table and select **"Delete Pairing"**.
    -   Select the row of the pairing and press the `Delete` key.
    -   Drag both players from the pairing back to the Player Pool.
-   **Clear All Pairings**: Click the **"Clear All"** button to remove all current pairings and return all players to the Player Pool.

### Assigning a Bye

If there is an odd number of players, one player must be given a bye for the round.

1.  Right-click a player in the Player Pool and select **"Set as bye player"**.
2.  To remove the bye, drag the player from the Bye Player area back into the Player Pool.

### Undo

Made a mistake? Click the **"Undo"** button in the toolbar to reverse the last action you took, such as creating a pairing, deleting a pairing, or assigning a bye.

---

## Toolbar and Other Actions

-   **Search/Filter**: Use the search box above the Player Pool to filter the list by name or rating. This is useful in large tournaments.
-   **Export Pairings**: Click **"Export"** to save the current set of pairings and the bye player to a JSON file. This can be useful for saving a draft or for auditing purposes.
-   **Import Pairings**: Click **"Import"** to load a set of pairings from a previously exported JSON file.

---

## Validation

The dialog provides real-time feedback on the validity of the pairings.

-   **Repeat Pairings**: If you create a pairing between two players who have already played each other in the tournament, a warning message will appear in the validation panel at the bottom.
-   **Statistics**: The panel below the pairings table shows statistics, such as the number of paired players and remaining players, to help you ensure everyone is accounted for.

---

## Keyboard Shortcuts

-   `Ctrl+A`: Auto-pair all remaining players.
-   `Delete`: Delete the currently selected pairing in the table.
