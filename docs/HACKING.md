# HACKING.md

# to build:

- requires on path:

  - bash
  - pip or pip3 (if so replace pip with pip3)
  - Python 3.10 or newer (see `requires-python` in `pyproject.toml`)
  - all runtime dependencies

    test building with `python3 -m build .` (from git root)
# dependencies
    can be installed with sh script: `ensure-all-dependancies.sh`
    will parse the pyproject.toml and install with pip

# recommendations for developers:

    1. Install in a virtual environment
    IE:
    ```bash
    $ cd Gambit-Pairing
    $ python -m venv .venv
    ```

    2. Activate your environment with:
      `source .venv/bin/activate` on Unix/macOS
        or   `.venv\Scripts\activate` on Windows

    3. Install as editable
    ```bash
    $ pip install --editable .
    ```
    or:
    >A helper script in the git root called "install_editable_pip.sh" should automate this.

# Then

load the tournament defined in /test_data/tournaments/test_32_players...
and happy hacking

to commit, use the commit.py script. see:
    `git_commit_helper.md`

# auto enter virtual env on cd
    > this uses direnv [https://direnv.net/](https://direnv.net/)

make a .envrc with whatever command activates your venv

mine:
```
# Make sure virtualenvwrapper is loaded
export WORKON_HOME="${WORKON_HOME:-$HOME/.virtualenvs}"
if [ -f "$HOME/.local/bin/virtualenvwrapper.sh" ]; then
    source "$HOME/.local/bin/virtualenvwrapper.sh"
else
    echo ".envrc FAIL"
fi


# Name of your venvwrapper environment
VENV_NAME="gambit-pairing"

# Activate it
workon "$VENV_NAME"
```
