"""Theme palette dictionaries for the Gambit Pairing stylesheet system.

Each theme is a plain ``Dict[str, str]`` that maps token names (as used in
the QSS template partials) to concrete CSS values.  The active theme is
controlled by ``style_manager.set_active_theme()`` and read back by
``style_manager.get_active_theme()``.

Available themes
----------------
light
    Default high-contrast chess-inspired palette (greens, beiges, neutrals).
dark
    Low-luminance palette stub — values are reasoned approximations and
    should be refined once a design spec for dark mode is available.

Adding a theme
--------------
1. Create ``<name>_theme.py`` with a ``<NAME>_THEME`` dict that supplies
   every token listed in ``base_theme.REQUIRED_TOKENS``.
2. Register the module path and dict name in
   ``style_manager._THEMES``.
No QSS partial files need changing.
"""

from gambitpairing.resources.themes.dark_theme import DARK_THEME
from gambitpairing.resources.themes.light_theme import LIGHT_THEME

__all__ = ["DARK_THEME", "LIGHT_THEME"]
