# Installing and running Gambit Pairing

## Fedora Linux from a source checkout

From a terminal, install the basic tools, create an isolated environment, and
install the project in editable mode:

```bash
sudo dnf install -y git python3 python3-pip qt6-qtbase-gui qt6-qtwayland xcb-util-cursor
git clone https://github.com/gambit-devs/gambit-pairing.git
cd gambit-pairing
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install --editable '.[dev]'
```

With the virtual environment active, launch the application with:

```bash
gambit-pairing
```

The command is installed by the package's `project.gui-scripts` entry point.
If the environment is not active, use `./.venv/bin/gambit-pairing` instead.

Run the test suite with:

```bash
pytest -q
```

For a headless/offscreen test run, useful on CI or when no display is
available:

```bash
QT_QPA_PLATFORM=offscreen pytest -q
```

If the application reports that the Qt `wayland` or `xcb` platform plugin
cannot be initialized, install the desktop Qt runtime dependencies and launch
it again:

```bash
sudo dnf install -y qt6-qtbase-gui qt6-qtwayland xcb-util-cursor
gambit-pairing
```

## Installation with pip

For an already prepared Python environment, install from the repository root:

```bash
python -m pip install --editable .
```

Then run `gambit-pairing` from that same environment.

# installation - pyinstaller executable -- on unixlike system

```bash
./make_executable.sh

cp dist/gambit-pairing ~/.local/bin/
```
now gambit-pairing should be executable from shell
* if ~/.local/bin is on path
