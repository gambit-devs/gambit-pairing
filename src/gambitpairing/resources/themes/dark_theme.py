"""Dark theme variable definitions for Gambit Pairing.

This module is a **stub** — values are placeholders adapted from the light
theme and have not been specifically tuned for dark-mode contrast.  Swap these
values for a fully tested dark palette when implementing dark mode UI support.

Usage
-----
Pass ``theme_name="dark"`` to ``style_manager.get_stylesheet()`` to activate:

    from gambitpairing.resources import style_manager
    qss = style_manager.get_stylesheet(theme_name="dark")
    app.setStyleSheet(qss)
"""

from __future__ import annotations

from typing import Dict

DARK_THEME: Dict[str, str] = {
    # -----------------------------------------------------------------------
    # Brand — Primary (Chess Green — slightly brighter for dark backgrounds)
    # -----------------------------------------------------------------------
    "color_primary":          "#4a9e40",
    "color_primary_hover":    "#5ab84e",
    "color_primary_light":    "#7ab86a",
    "color_primary_dark":     "#2d6624",
    "color_primary_bg":       "#1e3b1a",
    "color_primary_bg_light": "#1a3316",

    # -----------------------------------------------------------------------
    # Accent — Chess Wood / Beige (muted on dark backgrounds)
    # -----------------------------------------------------------------------
    "color_accent":           "#c4a060",
    "color_accent_hover":     "#3a2e1e",
    "color_accent_light":     "#8c6c38",
    "color_accent_dark":      "#6b4520",

    # -----------------------------------------------------------------------
    # Background Hierarchy
    # -----------------------------------------------------------------------
    "bg_page":                "#1a1d23",
    "bg_surface":             "#22262e",
    "bg_subtle":              "#272b34",
    "bg_muted":               "#1e2228",
    "bg_input":               "#2a2e38",
    "bg_input_focus":         "#2e3340",
    "bg_disabled":            "#1e2228",
    "bg_header":              "#272b34",

    # -----------------------------------------------------------------------
    # Text
    # -----------------------------------------------------------------------
    "text_body":              "#e2e6ef",
    "text_heading":           "#f0f3f8",
    "text_secondary":         "#9ca3af",
    "text_muted":             "#6b7280",
    "text_disabled":          "#4b5563",
    "text_dark":              "#d1d5db",
    "text_on_primary":        "#ffffff",

    # -----------------------------------------------------------------------
    # Borders
    # -----------------------------------------------------------------------
    "border_light":           "#2e3340",
    "border_medium":          "#3a3f4d",
    "border_input":           "#3a3f4d",
    "border_input_focus":     "#c4a060",
    "border_header":          "#3a3f4d",
    "border_header_bottom":   "#555e6e",

    # -----------------------------------------------------------------------
    # Selection
    # -----------------------------------------------------------------------
    "selection_bg":           "#2a3d5c",
    "selection_text":         "#e2e6ef",

    # -----------------------------------------------------------------------
    # Table
    # -----------------------------------------------------------------------
    "table_grid":             "#2e3340",
    "table_alt":              "#252930",
    "table_hover_bg":         "#2a2e38",

    # -----------------------------------------------------------------------
    # Semantic States
    # -----------------------------------------------------------------------
    "state_info_text":        "#93c5fd",
    "state_info_bg":          "#1e3048",
    "state_info_border":      "#2a4a72",
    "state_info_hover":       "#60a5fa",

    "state_warn_text":        "#fbbf24",
    "state_warn_bg":          "#2e2308",
    "state_warn_border":      "#5c4510",
    "state_warn_accent":      "#d97706",

    "state_success_text":     "#4a9e40",
    "state_success_bg":       "#1a2e18",
    "state_success_border":   "#2d5a27",

    "state_error_accent":     "#f87171",

    # -----------------------------------------------------------------------
    # Typography (identical to light — typeface never changes)
    # -----------------------------------------------------------------------
    "font_family":            '"Segoe UI", "Inter", "DejaVu Sans", Arial, sans-serif',
    "font_size_xs":           "9pt",
    "font_size_sm":           "10pt",
    "font_size_base":         "11pt",
    "font_size_md":           "11.5pt",
    "font_size_lg":           "12pt",
    "font_size_xl":           "13pt",
    "font_size_2xl":          "16pt",
    "font_size_3xl":          "20pt",
    "font_size_icon":         "54pt",

    # -----------------------------------------------------------------------
    # Border Radius (identical to light)
    # -----------------------------------------------------------------------
    "radius_xs":              "4px",
    "radius_sm":              "6px",
    "radius_md":              "8px",
    "radius_lg":              "12px",
    "radius_xl":              "14px",
    "radius_2xl":             "16px",
    "radius_3xl":             "18px",
}
