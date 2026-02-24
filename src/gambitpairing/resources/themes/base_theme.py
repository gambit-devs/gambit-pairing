"""Canonical token contract for the Gambit Pairing stylesheet system.

Defines the exhaustive set of token names that every concrete theme
dictionary must supply.  The ``style_manager`` module calls
``validate_theme`` at startup to catch missing tokens before any QSS
substitution is attempted, ensuring broken stylesheets are never silently
produced.

Adding a new token
------------------
1. Append its name to ``REQUIRED_TOKENS``.
2. Supply the value in **every** theme module (``light_theme``, ``dark_theme``,
   etc.).
3. Reference ``{{token_name}}`` in the relevant QSS partial.

Removing a token follows the same three steps in reverse.
"""

from __future__ import annotations

from typing import Dict, FrozenSet

# ---------------------------------------------------------------------------
# Canonical token list
# Every partial QSS template references only tokens that appear here.
# Concrete theme dicts must supply all of them.
# ---------------------------------------------------------------------------
REQUIRED_TOKENS: FrozenSet[str] = frozenset(
    {
        # Brand — Primary (Chess Green)
        "color_primary",
        "color_primary_hover",
        "color_primary_light",
        "color_primary_dark",
        "color_primary_bg",
        "color_primary_bg_light",
        # Accent (Chess Wood / Beige)
        "color_accent",
        "color_accent_hover",
        "color_accent_light",
        "color_accent_dark",
        # Background hierarchy
        "bg_page",
        "bg_surface",
        "bg_subtle",
        "bg_muted",
        "bg_input",
        "bg_input_focus",
        "bg_disabled",
        "bg_header",
        # Text
        "text_body",
        "text_heading",
        "text_secondary",
        "text_muted",
        "text_disabled",
        "text_dark",
        "text_on_primary",
        # Borders
        "border_light",
        "border_medium",
        "border_input",
        "border_input_focus",
        "border_header",
        "border_header_bottom",
        # Selection
        "selection_bg",
        "selection_text",
        # Table
        "table_grid",
        "table_alt",
        "table_hover_bg",
        # State — Info / Recording
        "state_info_text",
        "state_info_bg",
        "state_info_border",
        "state_info_hover",
        # State — Warning
        "state_warn_text",
        "state_warn_bg",
        "state_warn_border",
        "state_warn_accent",
        # State — Success / Finished
        "state_success_text",
        "state_success_bg",
        "state_success_border",
        # State — Error
        "state_error_accent",
        # Typography
        "font_family",
        "font_size_xs",
        "font_size_sm",
        "font_size_base",
        "font_size_md",
        "font_size_lg",
        "font_size_xl",
        "font_size_2xl",
        "font_size_3xl",
        "font_size_icon",
        # Border radius
        "radius_xs",
        "radius_sm",
        "radius_md",
        "radius_lg",
        "radius_xl",
        "radius_2xl",
        "radius_3xl",
    }
)


def validate_theme(variables: Dict[str, str], theme_name: str = "unknown") -> None:
    """Raise ``ValueError`` if *variables* is missing any required token.

    Called automatically by ``style_manager._load_theme`` before QSS
    substitution so that incomplete theme dictionaries are rejected at
    startup rather than silently producing malformed output.

    Parameters
    ----------
    variables : Dict[str, str]
        Token-to-value mapping produced by a concrete theme module.
    theme_name : str, optional
        Human-readable identifier included in the error message,
        by default ``"unknown"``.

    Raises
    ------
    ValueError
        When one or more ``REQUIRED_TOKENS`` are absent from *variables*.

    Examples
    --------
    >>> from gambitpairing.resources.themes.light_theme import LIGHT_THEME
    >>> validate_theme(LIGHT_THEME, "light")  # passes silently
    """
    missing = REQUIRED_TOKENS - variables.keys()
    if missing:
        raise ValueError(
            f"Theme '{theme_name}' is missing required tokens: "
            + ", ".join(sorted(missing))
        )
