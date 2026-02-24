"""Style-sheet assembly engine for Gambit Pairing.

Combines multiple QSS template partials into a single complete stylesheet,
substituting colour and typography tokens from the active theme dictionary.

Architecture
------------
::

  resources/
    themes/
      base_theme.py      ← canonical token list + validation
      light_theme.py     ← default palette dictionary
      dark_theme.py      ← dark-mode palette dictionary
    styles/
      _01_reset_focus.qss
      _02_base.qss
      ...                ← QSS templates with {{token}} placeholders
      _14_print.qss
    style_manager.py     ← THIS FILE

All ``{{token_name}}`` placeholders in the QSS templates are replaced with
the concrete CSS values supplied by the active theme before the stylesheet is
handed to ``QApplication.setStyleSheet()``.  A ``KeyError`` is raised at
startup if any placeholder has no matching token — silent broken CSS is never
silently produced.

Theme switching (future UI)
---------------------------
Call ``set_active_theme(name)`` from the theme-picker dialog, then reapply::

    set_active_theme("dark")
    app.setStyleSheet(get_stylesheet())

New themes only require a new ``*_theme.py`` file and a ``_THEMES`` entry.
"""

from __future__ import annotations

import importlib
import logging
import re
from typing import Dict, List, Mapping, Tuple

from importlib_resources import files

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Theme registry
# Maps a theme name to (module_path, dict_attribute_name).  Add new entries
# here when new theme modules are created — no other code needs to change.
# ---------------------------------------------------------------------------
_THEMES: Mapping[str, Tuple[str, str]] = {
    "light": ("gambitpairing.resources.themes.light_theme", "LIGHT_THEME"),
    "dark":  ("gambitpairing.resources.themes.dark_theme",  "DARK_THEME"),
}

# The name of the theme that get_stylesheet() uses when called with no
# explicit argument.  Alter this via set_active_theme() at runtime — for
# example from a future preferences dialog.
DEFAULT_THEME: str = "light"
_active_theme: str = DEFAULT_THEME

# Pre-compiled regex for {{token_name}} placeholders.
_TOKEN_RE = re.compile(r"\{\{([A-Za-z_][A-Za-z0-9_]*)\}\}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_active_theme() -> str:
    """Return the name of the currently active theme.

    Returns
    -------
    str
        One of the keys registered in ``_THEMES``, e.g. ``"light"`` or
        ``"dark"``.
    """
    return _active_theme


def set_active_theme(theme_name: str) -> None:
    """Set the application-wide active theme.

    This is the hook for the future theme-picker UI.  After calling this,
    re-assemble and reapply the stylesheet::

        set_active_theme("dark")
        app.setStyleSheet(get_stylesheet())

    Parameters
    ----------
    theme_name : str
        Name of the theme to activate.  Must be a key in ``_THEMES``.

    Raises
    ------
    ValueError
        If *theme_name* is not a registered theme.
    """
    global _active_theme  # noqa: PLW0603  (intentional module-level state)
    if theme_name not in _THEMES:
        raise ValueError(
            f"Unknown theme '{theme_name}'. "
            f"Available: {list_themes()}"
        )
    _active_theme = theme_name
    logger.debug("style_manager: active theme set to '%s'", theme_name)


def list_themes() -> List[str]:
    """Return the names of all registered themes in sorted order.

    Returns
    -------
    List[str]
        Sorted theme name strings, e.g. ``["dark", "light"]``.
    """
    return sorted(_THEMES.keys())


def get_stylesheet(theme_name: str | None = None) -> str:
    """Assemble and return the complete application stylesheet.

    Loads all ``_NN_*.qss`` partial files from ``gambitpairing.resources.styles``
    in lexicographic order, concatenates them, then performs a single-pass
    token substitution using the active (or explicitly requested) theme.

    Parameters
    ----------
    theme_name : str or None, optional
        Theme to apply.  When ``None`` (default) the current active theme is
        used — see ``set_active_theme()``.  Passing an explicit name overrides
        the active theme for this call only.

    Returns
    -------
    str
        Fully resolved QSS string ready for ``QApplication.setStyleSheet()``.

    Raises
    ------
    ValueError
        If *theme_name* is not a registered theme.
    KeyError
        If any QSS template references a token the theme does not define.

    Examples
    --------
    Apply the active theme (set via ``set_active_theme``):

    >>> app.setStyleSheet(get_stylesheet())

    Apply a specific theme once without changing the active theme:

    >>> qss = get_stylesheet("light")
    """
    resolved_name = theme_name if theme_name is not None else _active_theme
    variables = _load_theme(resolved_name)
    raw_qss   = _load_partials()
    compiled  = _substitute_tokens(raw_qss, variables, resolved_name)

    logger.debug(
        "style_manager: assembled %d-char stylesheet with theme '%s'",
        len(compiled),
        resolved_name,
    )
    return compiled


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _load_theme(theme_name: str) -> Dict[str, str]:
    """Import and return the variable dictionary for *theme_name*.

    Uses a deferred ``importlib.import_module`` call so that only the
    requested theme module is loaded at any one time.

    Parameters
    ----------
    theme_name : str
        A key registered in ``_THEMES``.

    Returns
    -------
    Dict[str, str]
        Mapping of token names to CSS values for the theme.

    Raises
    ------
    ValueError
        If *theme_name* is not registered.
    ValueError
        If the theme dictionary is missing required tokens (raised by
        ``validate_theme``).
    """
    if theme_name not in _THEMES:
        raise ValueError(
            f"Unknown theme '{theme_name}'. "
            f"Available: {list_themes()}"
        )

    module_path, attr_name = _THEMES[theme_name]
    module = importlib.import_module(module_path)
    variables: Dict[str, str] = getattr(module, attr_name)

    from gambitpairing.resources.themes.base_theme import validate_theme
    validate_theme(variables, theme_name)

    return variables


def _load_partials() -> str:
    """Read all QSS partial files from the styles sub-package in order.

    Files are iterated in lexicographic order so the ``_NN_`` numeric prefix
    in each filename controls render precedence.

    Returns
    -------
    str
        All partial QSS content joined with blank-line separators.

    Raises
    ------
    OSError
        If any partial file cannot be read from the package.
    """
    styles_pkg = files("gambitpairing.resources.styles")
    qss_files = sorted(
        entry for entry in styles_pkg.iterdir() if entry.name.endswith(".qss")
    )

    if not qss_files:
        logger.warning(
            "style_manager: no .qss partials found in gambitpairing.resources.styles"
        )
        return ""

    parts: List[str] = []
    for qss_file in qss_files:
        try:
            content = qss_file.read_text(encoding="utf-8")
            parts.append(content)
            logger.debug("style_manager: loaded '%s'", qss_file.name)
        except OSError as exc:  # pragma: no cover
            logger.error(
                "style_manager: failed to read '%s': %s", qss_file.name, exc
            )
            raise

    return "\n\n".join(parts)


def _substitute_tokens(
    qss: str, variables: Dict[str, str], theme_name: str
) -> str:
    """Replace every ``{{token}}`` placeholder in *qss* with its theme value.

    Parameters
    ----------
    qss : str
        Raw QSS string containing ``{{token_name}}`` placeholders.
    variables : Dict[str, str]
        Token-to-CSS-value mapping from the active theme.
    theme_name : str
        Included in the error message when tokens are undefined.

    Returns
    -------
    str
        QSS with all ``{{token_name}}`` placeholders replaced by their values.

    Raises
    ------
    KeyError
        If the QSS references one or more tokens absent from *variables*.
    """
    undefined: List[str] = []

    def _replacer(match: re.Match) -> str:  # type: ignore[type-arg]
        token = match.group(1)
        if token not in variables:
            undefined.append(token)
            return match.group(0)  # preserve intact so the error is human-readable
        return variables[token]

    result = _TOKEN_RE.sub(_replacer, qss)

    if undefined:
        raise KeyError(
            f"Theme '{theme_name}' is missing tokens referenced in QSS: "
            + ", ".join(sorted(set(undefined)))
        )

    return result
