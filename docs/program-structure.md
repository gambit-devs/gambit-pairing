# Program structure of Gambit-Pairing

## Project Structure

.
├── docs
│   ├── before_you_commit.md
│   ├── HACKING.md
│   ├── installing.md
│   ├── manual-pairing-guide.md
│   ├── program-structure.md
│   ├── project_formatting.md
│   └── screenshots
├── Gambit-Pairing.spec
├── install_editable_pip.sh
├── licenses
│   ├── LICENSE
│   └── license.rtf
├── make_executable.py
├── make_executable.sh
├── pyproject.toml
├── README.md
├── resources
│   ├── scripts
│   │   └── format_project.py
│   └── unused_designs
├── src
│   ├── gambitpairing
│   │   ├── core
│   │   │   ├── api_utils.py
│   │   │   ├── constants.py
│   │   │   ├── exceptions.py
│   │   │   ├── **init**.py
│   │   │   ├── pairing_dutch_swiss.py
│   │   │   ├── pairing_round_robin.py
│   │   │   ├── player.py
│   │   │   ├── print_utils.py
│   │   │   ├── tournament.py
│   │   │   ├── updater.py
│   │   │   └── utils.py
│   │   ├── gui
│   │   │   ├── crosstable_tab.py
│   │   │   ├── dialogs
│   │   │   │   ├── about_dialog.py
│   │   │   │   ├── **init**.py
│   │   │   │   ├── manual_pairing_dialog.py
│   │   │   │   ├── new_tournament_dialog.py
│   │   │   │   ├── player_detail_dialog.py
│   │   │   │   ├── player_edit_dialog.py
│   │   │   │   ├── printing.py
│   │   │   │   ├── settings_dialog.py
│   │   │   │   ├── update_dialog.py
│   │   │   │   └── update_prompt_dialog.py
│   │   │   ├── dialogs.py
│   │   │   ├── history_tab.py
│   │   │   ├── **init**.py
│   │   │   ├── mainwindow.py
│   │   │   ├── notournament_placeholder.py
│   │   │   ├── players_tab.py
│   │   │   ├── standings_tab.py
│   │   │   ├── tournament_tab.py
│   │   │   └── update_worker.py
│   │   ├── **init**.py
│   │   ├── **main**.py
│   │   ├── resources
│   │   │   ├── icons
│   │   │   ├── **init**.py
│   │   │   ├── resource_utils.py
│   │   │   ├── scripts
│   │   │   └── styles/
│   │   └── test
│   │   ├── core
│   │   │   └── pairing_round_robin.py
│   │   ├── **init**.py
│   │   └── **main**.py
└── test_data
├── players
│   ├── test_16_rated_players.csv
│   └── test_45_rated_players.csv
└── tournaments
├── test_32_player_tournament.json
├── test_open_2025.json
└── winter_chess_championship_2025.json

43 directories, 198 files
- uses a src layout, see:
  https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/#src-layout-vs-flat-layout

# in the gambitpairing module:

## **main**.py -- entry point

- Creates the main window. Handles various OS'.
- `from gui.mainwindow import GambitPairingMainWindow` imports app

# gui module -- contains the various components and QT widgets

## mainwindow.py -- in charge of the main window

`class GambitPairingMainWindow(QtWidgets.QMainWindow):`

## crosstable_tab.py

`class CrosstableTab(QtWidgets.QWidget):`

## ... This module contains the Qt Widgets

# core module -- contains the business logic

## utils.py -- logging and utility functions

## updater.py -- Handles checking for and applying application updates from GitHub Releases.

## player.py -- Represents a player in the tournament.

`class Player:`

## tournament.py -- Manages the tournament state, pairings, results, and tiebreakers.

`class Tournament:`

## constants.py -- what you think
