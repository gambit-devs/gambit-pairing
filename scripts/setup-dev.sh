#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
venv_dir="$project_dir/.venv"
# Keep this in sync with requires-python in pyproject.toml.
minimum_python="3.10"
recreate_venv=0
install_system_deps=1
assume_yes=0
require_breeze=0
requested_python=""
python_bin=""
old_python_version=""
package_manager=""
notes=()

usage() {
    cat <<'EOF'
Usage: scripts/setup-dev.sh [options]

Install Gambit's Linux development dependencies and create an editable .venv.
Package managers: apt, dnf/yum, pacman, zypper, apk, and xbps.

  --python PATH      Use this Python interpreter (Python 3.10 or newer).
  --recreate         Remove and recreate the project's ignored .venv directory.
  --skip-system-deps Use system dependencies already installed on this system.
  --require-breeze   Fail if Qt cannot load the optional Breeze Widgets style.
  -y, --yes          Install a missing Python without prompting.
  -h, --help         Show this help.
EOF
}

die() {
    echo "$*" >&2
    exit 1
}

while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --python)
            [[ "$#" -ge 2 && -n "$2" ]] || die "--python needs an interpreter path."
            requested_python="$2"
            shift
            ;;
        --recreate) recreate_venv=1 ;;
        --skip-system-deps) install_system_deps=0 ;;
        --require-breeze) require_breeze=1 ;;
        -y|--yes) assume_yes=1 ;;
        -h|--help) usage; exit 0 ;;
        *) usage >&2; die "Unknown option: $1" ;;
    esac
    shift
done

[[ "$(uname -s)" == Linux ]] || die "This script is for Linux development environments."
cd "$project_dir"
# User site packages and an activated environment's import overrides can hide
# the distro's PyQt6 or expose an unrelated pip installation.
export PYTHONNOUSERSITE=1
unset PYTHONHOME PYTHONPATH

run_as_root() {
    if [[ "$EUID" -eq 0 ]]; then
        "$@"
    elif command -v sudo >/dev/null 2>&1; then
        sudo "$@"
    elif command -v doas >/dev/null 2>&1; then
        doas "$@"
    else
        die "Install system dependencies as root or install sudo/doas, then rerun this script."
    fi
}

detect_package_manager() {
    local distro_id manager
    local distro_ids=()
    if [[ -r /etc/os-release ]]; then
        # shellcheck source=/dev/null
        source /etc/os-release
        read -r -a distro_ids <<< "${ID:-} ${ID_LIKE:-}"
    fi
    for distro_id in "${distro_ids[@]}"; do
        case "$distro_id" in
            debian|ubuntu|linuxmint|pop|neon) manager=apt-get ;;
            fedora|rhel|centos|rocky|almalinux|ol) manager=dnf ;;
            arch|manjaro|endeavouros) manager=pacman ;;
            suse|opensuse|opensuse-*) manager=zypper ;;
            alpine) manager=apk ;;
            void) manager=xbps-install ;;
            *) continue ;;
        esac
        if command -v "$manager" >/dev/null 2>&1; then
            package_manager="$manager"
            return
        fi
    done
    # Derivatives may use an unfamiliar ID or omit os-release entirely.
    for manager in zypper pacman apk xbps-install dnf dnf5 apt-get yum; do
        if command -v "$manager" >/dev/null 2>&1; then
            package_manager="$manager"
            return
        fi
    done
    die "No supported package manager found. Install Python $minimum_python+, pip, venv, PyQt6, QtSvg, make and g++ manually, then use --skip-system-deps."
}

install_packages() {
    case "$package_manager" in
        apt-get) run_as_root apt-get install -y "$@" ;;
        dnf|dnf5|yum) run_as_root "$package_manager" install -y "$@" ;;
        pacman) run_as_root pacman -S --needed --noconfirm "$@" ;;
        zypper) run_as_root zypper --non-interactive install "$@" ;;
        apk) run_as_root apk add "$@" ;;
        xbps-install) run_as_root xbps-install -Sy "$@" ;;
    esac
}

python_is_compatible() {
    "$1" -c 'import sys; raise SystemExit(sys.version_info[:2] < (3, 10))' >/dev/null 2>&1
}

find_python() {
    local candidate resolved version first_compatible=""
    local candidates=()
    python_bin=""
    if [[ -n "$requested_python" ]]; then
        candidates=("$requested_python")
    else
        # Prefer distro interpreters to pyenv shims, /usr/local, and active venvs:
        # only the matching distro Python can normally import system PyQt6.
        candidates=(/usr/bin/python3 /usr/bin/python3.[0-9]* python3 python)
    fi
    for candidate in "${candidates[@]}"; do
        command -v "$candidate" >/dev/null 2>&1 || continue
        # Unwrap an activated venv to avoid creating a venv inside another one.
        resolved="$("$candidate" -c 'import os, sys; print(os.path.realpath(getattr(sys, "_base_executable", sys.executable)))' 2>/dev/null)" || continue
        if python_is_compatible "$resolved"; then
            if [[ -z "$first_compatible" ]]; then
                first_compatible="$resolved"
            fi
            if "$resolved" -c 'from PyQt6 import QtCore, QtGui, QtWidgets, QtPrintSupport, QtSvg, uic' >/dev/null 2>&1; then
                python_bin="$resolved"
                return
            fi
        elif [[ -z "$old_python_version" ]]; then
            version="$("$resolved" -c 'import sys; print("%s.%s.%s" % sys.version_info[:3])' 2>/dev/null)" || continue
            old_python_version="$version"
        fi
    done
    python_bin="$first_compatible"
}

check_python() {
    if [[ -n "$python_bin" ]]; then
        return
    fi
    if [[ -n "$old_python_version" ]]; then
        die "Setup cannot continue: Python $old_python_version is older than Gambit's required Python $minimum_python. Install a newer Python with matching PyQt6 packages, then rerun with --python /path/to/python3 --recreate. The existing Python has not been replaced."
    fi
    if [[ -n "$requested_python" ]]; then
        die "Cannot run the requested Python interpreter: $requested_python"
    fi
}

# Reject an unusable existing environment before installing system packages.
[[ ! -L "$venv_dir" ]] || die "$venv_dir is a symlink. Use a local .venv directory instead."
if [[ -e "$venv_dir" && "$recreate_venv" -eq 0 ]]; then
    if [[ ! -f "$venv_dir/pyvenv.cfg" || ! -x "$venv_dir/bin/python" ]] ||
        ! grep -Eq '^include-system-site-packages[[:space:]]*=[[:space:]]*true[[:space:]]*$' "$venv_dir/pyvenv.cfg" ||
        ! python_is_compatible "$venv_dir/bin/python"; then
        die "$venv_dir is broken, outdated, or cannot see system packages. Rerun with --recreate."
    fi
fi

find_python
check_python

if [[ "$install_system_deps" -eq 1 ]]; then
    if [[ -e /run/ostree-booted && ! -e /run/.containerenv && ! -e /.dockerenv ]]; then
        die "Run this script inside Toolbox or Distrobox on an immutable Linux host, or provision dependencies manually and use --skip-system-deps."
    fi
    detect_package_manager
fi

if [[ -z "$python_bin" ]]; then
    [[ "$install_system_deps" -eq 1 ]] || die "Python $minimum_python+ is missing. Install it before using --skip-system-deps."
    if [[ "$assume_yes" -eq 0 ]]; then
        [[ -t 0 ]] || die "Python is missing. Rerun with --yes to install the distribution's Python, or install Python $minimum_python+ yourself."
        reply=""
        read -r -p "Python is missing. Install the distribution's Python with $package_manager? [y/N] " reply || true
        case "$reply" in
            y|Y|yes|YES) ;;
            *) die "Setup stopped. Install Python $minimum_python+ and rerun when ready." ;;
        esac
    fi
fi

if [[ "$install_system_deps" -eq 1 ]]; then
    if [[ "$package_manager" == apt-get ]]; then
        run_as_root apt-get update
    fi
    if [[ -z "$python_bin" ]]; then
        case "$package_manager" in
            pacman) install_packages python ;;
            *) install_packages python3 ;;
        esac
        find_python
        check_python
        [[ -n "$python_bin" ]] || die "The distribution did not provide a usable Python $minimum_python+ interpreter."
    fi

    case "$package_manager" in
        apt-get)
            packages=(python3-pip python3-venv python3-pyqt6 python3-pyqt6.qtsvg qt6-svg-plugins make g++)
            style_packages=(kde-style-breeze breeze-icon-theme)
            ;;
        dnf|dnf5|yum)
            packages=(python3-pip python3-pyqt6 qt6-qtsvg make gcc-c++)
            style_packages=(plasma-breeze-qt6 breeze-icon-theme)
            ;;
        pacman)
            packages=(python-pip python-pyqt6 qt6-svg make gcc)
            style_packages=(breeze breeze-icons)
            ;;
        zypper)
            python_tag="$("$python_bin" -c 'import sys; print("python%s%s" % sys.version_info[:2])')"
            packages=("$python_tag-pip" "$python_tag-PyQt6" libQt6Svg6 make gcc-c++)
            style_packages=(breeze6-style kf6-breeze-icons)
            ;;
        apk)
            packages=(py3-pip py3-qt6 qt6-qtsvg build-base)
            style_packages=(breeze breeze-icons)
            ;;
        xbps-install)
            packages=(python3-pip python3-pyqt6 python3-pyqt6-widgets python3-pyqt6-printsupport python3-pyqt6-svg qt6-svg base-devel)
            style_packages=(breeze-qt6 breeze-icons)
            ;;
    esac
    if ! install_packages "${packages[@]}"; then
        die "Required packages could not be installed. Check the enabled repositories and package names for your release, or install equivalents and use --skip-system-deps."
    fi
    if ! install_packages "${style_packages[@]}"; then
        notes+=("Optional Breeze packages could not be installed; check your release's package names and repositories.")
    fi
    # Installing packages may add PyQt6 for a different distro Python flavor.
    find_python
    check_python
fi

if ! system_qt="$("$python_bin" -c 'import os; from PyQt6 import QtCore, QtGui, QtWidgets, QtPrintSupport, QtSvg, uic; print(os.path.realpath(QtCore.__file__))')"; then
    die "The selected Python ($python_bin) cannot import the required PyQt6 modules. Install matching distro packages or select their interpreter with --python."
fi

if [[ "$recreate_venv" -eq 1 ]]; then
    rm -rf -- "$venv_dir"
fi
if [[ ! -e "$venv_dir" ]]; then
    if ! "$python_bin" -m venv --system-site-packages "$venv_dir"; then
        die "Could not create .venv. Install this Python's venv/ensurepip package and rerun with --recreate."
    fi
fi

venv_python="$venv_dir/bin/python"
base_python="$("$venv_python" -c 'import os, sys; print(os.path.realpath(sys._base_executable))')"
[[ "$base_python" == "$python_bin" ]] || die ".venv uses a different Python. Rerun with --recreate to use $python_bin."
check_venv_qt() {
    local venv_qt
    venv_qt="$("$venv_python" -c 'import os; from PyQt6 import QtCore; print(os.path.realpath(QtCore.__file__))')" || return 1
    [[ "$venv_qt" == "$system_qt" ]]
}
check_venv_qt || die ".venv is shadowing the selected Python's PyQt6. Rerun with --recreate to use the distro Qt runtime."

if ! "$venv_python" -m pip --version >/dev/null 2>&1; then
    if "$venv_python" -m ensurepip --version >/dev/null 2>&1; then
        "$venv_python" -m ensurepip --upgrade
    elif command -v uv >/dev/null 2>&1; then
        uv pip install --python "$venv_python" pip
    else
        die "Could not bootstrap pip in $venv_dir. Install this Python's pip/ensurepip package and rerun."
    fi
fi

# Prevent pip from replacing the distro PyQt6 with a wheel bundling another Qt.
constraints_file="$(mktemp)"
trap 'rm -f -- "$constraints_file"' EXIT
"$venv_python" -c 'from PyQt6.QtCore import PYQT_VERSION_STR; print("PyQt6==" + PYQT_VERSION_STR)' > "$constraints_file"
"$venv_python" -m pip install --upgrade pip

if ! command -v make >/dev/null 2>&1 || ! command -v g++ >/dev/null 2>&1; then
    die "The BBP pairing engine needs GNU make and a C++20-capable g++. Install them and rerun."
fi
"$venv_python" scripts/build_bbp.py
"$venv_python" -m pip install --constraint "$constraints_file" --editable "$project_dir"
check_venv_qt || die "pip replaced the distro PyQt6. Recreate .venv and check your Python package constraints."

echo "Checking the Qt runtime..."
if ! QT_QPA_PLATFORM=offscreen GAMBIT_NATIVE_STYLE_REQUIRED="$require_breeze" \
    "$venv_dir/bin/gambit-pairing" --verify-native-style; then
    die "Gambit's Qt runtime check failed. Check the output above; Breeze requires a Qt 6 style plugin matching the distro PyQt6."
fi
if ! QT_QPA_PLATFORM=offscreen "$venv_python" - <<'PY'
from PyQt6.QtWidgets import QApplication, QStyleFactory
app = QApplication([])
raise SystemExit("breeze" not in {name.casefold() for name in QStyleFactory.keys()})
PY
then
    notes+=("Breeze's Qt 6 style is unavailable. Gambit will use the available Qt style; install a matching Qt 6 Breeze plugin for Breeze styling.")
fi

cat <<EOF

Development setup is ready.
Run Gambit with: "$venv_dir/bin/gambit-pairing"
EOF
if [[ -n "$old_python_version" ]]; then
    notes+=("Python $old_python_version was also found. This environment uses a compatible Python; use .venv/bin/gambit-pairing to launch Gambit.")
fi
for note in "${notes[@]}"; do
    printf '\nNote: %s\n' "$note"
done
