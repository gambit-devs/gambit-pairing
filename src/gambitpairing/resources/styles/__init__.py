"""QSS template partials for Gambit Pairing.

Files in this package are named ``_NN_<section>.qss`` and are loaded in
lexicographic order by ``style_manager.get_stylesheet()``.  Each file
addresses a distinct area of the UI so individual sections are easy to locate
and amend without touching unrelated rules.

Token syntax
------------
Colour and typography values are written as ``{{token_name}}``.  The style
manager replaces every token with the concrete value from the active theme
before the stylesheet is applied to the application.
"""
