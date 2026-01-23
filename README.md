```
                                  $$\       $$\   $$\
                                  $$ |      \__|  $$ |
 $$$$$$\   $$$$$$\  $$$$$$\$$$$\  $$$$$$$\  $$\ $$$$$$\
$$  __$$\  \____$$\ $$  _$$  _$$\ $$  __$$\ $$ |\_$$  _|
$$ /  $$ | $$$$$$$ |$$ / $$ / $$ |$$ |  $$ |$$ |  $$ |
$$ |  $$ |$$  __$$ |$$ | $$ | $$ |$$ |  $$ |$$ |  $$ |$$\
\$$$$$$$ |\$$$$$$$ |$$ | $$ | $$ |$$$$$$$  |$$ |  \$$$$  |
 \____$$ | \_______|\__| \__| \__|\_______/ \__|   \____/
$$\   $$ |
\$$$$$$  |
 \______/
                    $$\           $$\
                    \__|          \__|
 $$$$$$\   $$$$$$\  $$\  $$$$$$\  $$\ $$$$$$$\   $$$$$$\
$$  __$$\  \____$$\ $$ |$$  __$$\ $$ |$$  __$$\ $$  __$$\
$$ /  $$ | $$$$$$$ |$$ |$$ |  \__|$$ |$$ |  $$ |$$ /  $$ |
$$ |  $$ |$$  __$$ |$$ |$$ |      $$ |$$ |  $$ |$$ |  $$ |
$$$$$$$  |\$$$$$$$ |$$ |$$ |      $$ |$$ |  $$ |\$$$$$$$ |
$$  ____/  \_______|\__|\__|      \__|\__|  \__| \____$$ |
$$ |                                            $$\   $$ |
$$ |                                            \$$$$$$  |
\__|                                             \______/
                      ___  _____                     
                     / _ \|___  |                    
 _____ _____ _____  | | | |  / /   _____ _____ _____ 
|_____|_____|_____| | |_| | / /   |_____|_____|_____|
                     \___(_)_/                       
```

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python Version](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/PyQt6-Used-green.svg)](https://riverbankcomputing.com/software/pyqt/intro)
[![Discord](https://img.shields.io/badge/Discord-Join%20Chat-blue.svg)](https://discord.gg/eEnnetMDfr)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/Chickaboo/gambit-pairing)

**Important:** Gambit Pairing is in alpha development. Features and stability are not guaranteed.

[Join our Discord](https://discord.gg/eEnnetMDfr)

Gambit Pairing is a desktop application for managing Swiss-system chess tournaments. It provides a modern graphical user interface (GUI) built with PyQt6, supporting USCF-style pairings, tiebreaks, and tournament management.

## Features

- **Modern User Interface**

  - Polished, high-contrast, accessible UI with custom style-sheets.
  - Tabbed interface: Players, Tournament Control, Standings, Cross-Table, History Log.
  - Tooltips, context menus, and responsive layouts.
  - Print preview dialogs for pairings and standings.

- **Player Management**

  - Add, edit, withdraw/reactivate, and remove players.
  - Manage detailed player info: name, rating, gender, date of birth, phone, email, club, federation.
  - Import/export player lists/details from/to CSV or text files.

- **Tournament Setup**

  - Configure number of rounds and tiebreak order (Median, Solkoff, Cumulative, etc.).
  - Save/load tournaments to/from disk (`.json` files, JSON format).
  - Full tiebreaker configuration with drag-and-drop order in settings.

- **Swiss Pairings**

  - Automated pairings for each round, avoiding rematches and balancing colours.
  - Manual adjustment of pairings before results are entered (with dialog).
  - Bye assignment according to USCF rules, including handling of inactive/withdrawn players.

- **Results Entry**

  - Enter round results via an interactive table with quick result buttons.
  - Auto-set results for inactive players.
  - Undo last round's results.

- **Standings & Tiebreaks**

  - Standings table with configurable tiebreak columns.
  - Cross-table view showing all results.
  - Tiebreaker legend in printouts.
  - Support for Median, Solkoff, Cumulative, Sonnenborn-Berger, Most Blacks, and more.

- **Print & Export**

  - Print pairings, standings, or player lists directly from the application.
  - Print preview and printer selection supported.
  - Export standings and player lists to CSV or text.

- **History & Logging**

  - Detailed history log of actions, pairings, and results.
  - Exportable log.
  - Logging to file and console for debugging.

- **Update Checker**
  - Built-in update checker for packaged releases.
  - Modern dialogs for update prompts and progress.
  - Automatic and manual update checks.

## Documentation

- [Program Structure](docs/program-structure.md)
- [Installation Guide](docs/installing.md)
- [Before you commit](docs/before_you_commit.md)
- [Developer Hacking Guide](docs/HACKING.md)
- [Manual Pairing Guide](docs/manual-pairing-guide.md)
- [GitHub Actions Build System](docs/github-actions-build-system.md)

## Downloads

### Automatic Releases
Pre-built executables and installers are automatically created for each release:

- **Windows MSI Installer** - Full installation with Start Menu shortcuts
- **Windows Portable** - Single-file executable, run directly
- **Windows Directory** - Faster startup, extract and run
- **Linux** - Executable for Linux x64 systems  
- **macOS** - App bundle for macOS x64 systems

Visit the [Releases page](https://github.com/gambit-devs/gambit-pairing/releases) to download the latest version.

### Build Status
[![Build Windows Release](https://github.com/gambit-devs/gambit-pairing/actions/workflows/build-release.yml/badge.svg)](https://github.com/gambit-devs/gambit-pairing/actions/workflows/build-release.yml)
## Requirements

To install with pip, there is a helper sh script, ensure-all-dependancies.sh

it will parse the pyproject.toml and install all the runtime and development dependancies.

## Usage

1. Install the application:

- see: [installing.md](docs/installing.md)

2. **Create or Load a Tournament:**

   - Use "File > New Tournament..." or "File > Load Tournament..." to start.
   - Configure rounds and tiebreaks in "Settings".

3. **Add Players:**
   - Enter player details (name, rating, gender, etc.) and click "Add New Player...".
   - Import players from CSV via "File > Import Players from CSV...".
   - Edit, withdraw/reactivate, or remove players via right-click context menu.
4. **Start Tournament:**
   - Click "Start Tournament" when ready.
   - No further player additions/removals after starting.
5. **Pairings and Results:**
   - Prepare next round and enter results in the pairings table.
   - Use quick result buttons or select from the dropdown.
   - Manually adjust pairings if needed (right-click pairing row).
   - Undo last round's results if necessary.
6. **Standings & Cross-Table:**
   - View current standings and tiebreaks in the Standings tab.
   - View all results in the Cross-Table tab.
7. **Print:**
   - Print pairings, standings, or player lists via the "File > Print..." menu.
   - Use print preview and select your printer before printing.
8. **Export & Save:**
   - Export standings or player lists via the File menu.
   - Save or load tournaments at any time.
9. **History:**
   - Review all actions and results in the History Log tab.
10. **Check for Updates:**

    - Use "Help > Check for Updates..." to check for new versions (packaged releases only).

    ## Notes

- The pairing algorithm follows USCF-style Swiss rules, including color balancing and bye assignment.
- Tiebreak order is fully configurable and reflected in the standings and printouts.
- Manual pairing adjustments are logged and cannot be undone automatically.
- Tournament data is saved in `.json` files (JSON format).
- This is still an alpha; please report bugs or suggestions via [Discord](https://discord.gg/eEnnetMDfr) or make an [issue on Github](https://github.com/Chickaboo/gambit-pairing/issues)

## License

This project is open source and available under the GPL-3.0-or-later
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

## Screenshots

> _Below are some example screenshots of Gambit Pairing in action._

**About Dialog**
![About Dialog](docs/screenshots/app.png)

**Tournament Control Tab**
![Main Tournament Control](docs/screenshots/tournament.png)

**Player Manager Tab**
![Player Tab](docs/screenshots/player.png)

**Standings Tab**
![Standings Tab](docs/screenshots/standings.png)

**Cross-Table Tab**
![Cross-Table Tab](docs/screenshots/crosstable.png)

**History Log Tab**
![History Log Tab](docs/screenshots/history_log.png)

**Print Dialog**
![Print Dialog](docs/screenshots/print_dialog.png)

**Manual Pairing Dialog**
![Manual Pairing Dialog](docs/screenshots/manual.png)

```
                                                                 ↑↑↑↑↑↑↑    ↑↑↑↑↑↑↑↑
                                                          ↑↑↑↑↑↑↑↑↑↑↑↑↑↑  ↑↑↑↑↑↑↑↑↑↑↑
                                                       ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑  ↑↑↑↑↑↑↑↑↑↑↑↑↑
                                                    ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑  ↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                                                  ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑  ↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                                                ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑  ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                                               ↑↑↑↑↑↑↑↑↑↑↑↑↑↑         ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                                              ↑↑↑↑↑↑↑↑↑↑↑↑   ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                                             ↑↑↑↑↑↑↑↑↑↑↑   ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                                             ↑↑↑↑↑↑↑↑↑↑  ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                                            ↑↑↑↑↑↑↑↑↑↑  ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                                            ↑↑↑↑↑↑↑↑↑  ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                                           ↑↑↑↑↑↑↑↑↑↑  ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                                           ↑↑↑↑↑↑↑↑↑↑  ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                                           ↑↑↑↑↑↑↑↑↑↑  ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑  ↑↑↑↑↑↑↑↑↑↑↑
                                           ↑↑↑↑↑↑↑↑↑↑  ↑↑↑↑↑↑↑↑↑↑↑  ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑   ↑↑↑↑↑↑↑↑↑
                                           ↑↑↑↑↑↑↑↑↑↑  ↑↑↑↑↑↑↑↑↑↑↑  ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                                           ↑↑↑↑↑↑↑↑↑↑  ↑↑↑↑↑↑↑↑↑↑↑↑  ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                                           ↑↑↑↑↑↑↑↑↑↑  ↑↑↑↑↑↑↑↑↑↑↑↑↑  ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                                           ↑↑↑↑↑↑↑↑↑↑  ↑↑↑↑↑↑↑↑↑↑↑↑↑↑    ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                                           ↑↑↑↑↑↑↑↑↑↑  ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑     ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                                                       ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑    ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                                                        ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑  ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                                                           ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑  ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                                                              ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑  ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                                    ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑  ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                                ↑↑↑↑                            ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑  ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                              ↑↑↑                               ↑↑  ↑↑↑↑↑↑↑↑↑↑↑↑   ↑↑↑↑↑↑↑↑↑↑↑
                           ↑↑↑↑           ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑      ↑↑    ↑↑↑↑↑↑↑↑↑↑↑↑
                         ↑↑↑↑↑       ↑↑↑↑↑↑↑↑                   ↑↑    ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                       ↑↑↑↑↑↑       ↑↑↑                         ↑↑      ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                     ↑↑↑↑↑↑↑↑      ↑↑↑                          ↑        ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                    ↑↑↑↑↑↑↑↑↑      ↑↑        ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑         ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                   ↑↑↑↑↑↑↑↑↑↑      ↑↑      ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑           ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                   ↑↑↑↑↑↑↑↑↑↑      ↑↑      ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑              ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                  ↑↑↑↑↑↑↑↑↑↑↑      ↑↑      ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑                 ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                  ↑↑↑↑↑↑↑↑↑↑↑      ↑↑      ↑↑↑↑↑↑↑↑↑↑↑↑↑                    ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                  ↑↑↑↑↑↑↑↑↑↑↑      ↑↑      ↑↑        ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑        ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                  ↑↑↑↑↑↑↑↑↑↑↑      ↑↑      ↑↑      ↑↑↑              ↑↑
                  ↑↑↑↑↑↑↑↑↑↑↑      ↑↑      ↑↑    ↑↑↑↑↑              ↑↑      ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                  ↑↑↑↑↑↑↑↑↑↑↑      ↑↑      ↑↑  ↑↑↑↑↑↑↑              ↑↑      ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                  ↑↑↑↑↑↑↑↑↑↑↑      ↑↑      ↑↑↑↑↑↑↑↑↑↑↑      ↑↑      ↑↑      ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                  ↑↑↑↑↑↑↑↑↑↑↑      ↑↑      ↑↑↑↑↑↑↑↑↑↑↑      ↑↑      ↑↑      ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                  ↑↑↑↑↑↑↑↑↑↑↑      ↑↑      ↑↑↑↑↑↑↑↑↑↑↑      ↑↑      ↑↑           ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                  ↑↑↑↑↑↑↑↑↑↑↑      ↑↑       ↑↑↑↑↑↑↑↑↑↑      ↑↑      ↑↑     ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                  ↑↑↑↑↑↑↑↑↑↑↑      ↑↑↑                      ↑↑      ↑↑     ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                  ↑↑↑↑↑↑↑↑↑↑↑       ↑↑↑                     ↑↑      ↑↑    ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                  ↑↑↑↑↑↑↑↑↑↑↑↑       ↑↑↑↑↑↑                 ↑↑      ↑↑   ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                  ↑↑↑↑↑↑↑↑↑↑↑↑↑          ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑      ↑↑
                   ↑↑↑↑↑↑↑↑↑↑↑↑↑↑                                   ↑↑
                   ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑                                 ↑↑
                    ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                     ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                      ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                        ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
                           ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
```
