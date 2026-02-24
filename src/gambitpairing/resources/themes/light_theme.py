"""Light theme variable definitions for Gambit Pairing.

This is the default theme.  Every entry in this dictionary is substituted
into the QSS template partials by ``style_manager.get_stylesheet()``.

To create a new theme (e.g. dark mode), copy this file, rename the constant,
adjust the values, and register it in ``style_manager._THEMES``.  No QSS
partial files need to change.

Palette overview
----------------
Primary   : chess green   (#2d5a27 family)
Accent    : chess wood     (#e2c290 / #f5e9da / #8b5c2b family)
Neutrals  : cool grays     (#f9fafb → #23272f)
State     : blue (recording), amber (prepare), green (done), red (error)
"""

from __future__ import annotations

from typing import Dict

LIGHT_THEME: Dict[str, str] = {
    # -----------------------------------------------------------------------
    # Brand — Primary (Chess Green)
    # Used for: selected states, active indicators, primary actions, headings
    # -----------------------------------------------------------------------
    "color_primary":          "#2d5a27",
    "color_primary_hover":    "#3d7a37",
    "color_primary_light":    "#6e8b5b",
    "color_primary_dark":     "#1d4a17",
    "color_primary_bg":       "#e8f0e8",   # light green fill for selection
    "color_primary_bg_light": "#e8f5e9",   # even lighter for success states

    # -----------------------------------------------------------------------
    # Accent — Chess Wood / Beige
    # Used for: hover surfaces, focus borders, pressed states
    # -----------------------------------------------------------------------
    "color_accent":           "#e2c290",   # primary accent (beige/gold)
    "color_accent_hover":     "#f5e9da",   # very light wood for hover bg
    "color_accent_light":     "#f3d5a7",   # lighter beige (tab hover underline)
    "color_accent_dark":      "#8b5c2b",   # dark wood / brown text

    # -----------------------------------------------------------------------
    # Background Hierarchy
    # -----------------------------------------------------------------------
    "bg_page":                "#f9fafb",   # outermost window / dialog bg
    "bg_surface":             "#ffffff",   # cards, panels, inputs
    "bg_subtle":              "#f8f9fc",   # alternating rows, header bg
    "bg_muted":               "#f3f7fc",   # disabled inputs, toolbar bg
    "bg_input":               "#ffffff",   # input default bg
    "bg_input_focus":         "#f7fafd",   # input focused bg
    "bg_disabled":            "#f3f7fc",   # disabled widget fills
    "bg_header":              "#f8f9fc",   # table header row bg

    # -----------------------------------------------------------------------
    # Text
    # -----------------------------------------------------------------------
    "text_body":              "#23272f",   # primary body text
    "text_heading":           "#1f2937",   # headings, titles
    "text_secondary":         "#6b7280",   # de-emphasised labels
    "text_muted":             "#9ca3af",   # placeholder / hint text
    "text_disabled":          "#a1a7b3",   # disabled widget text
    "text_dark":              "#374151",   # slightly lighter than heading
    "text_on_primary":        "#ffffff",   # text placed on primary bg

    # -----------------------------------------------------------------------
    # Borders
    # -----------------------------------------------------------------------
    "border_light":           "#e3e7ee",   # most widget borders
    "border_medium":          "#d1d5db",   # slightly heavier border
    "border_input":           "#e3e7ee",   # input default border
    "border_input_focus":     "#e2c290",   # input focused border (accent)
    "border_header":          "#d5dbe4",   # table header border
    "border_header_bottom":   "#a8b2c4",   # bottom accent on header

    # -----------------------------------------------------------------------
    # Selection
    # -----------------------------------------------------------------------
    "selection_bg":           "#d0d9eb",   # selected cell / item bg
    "selection_text":         "#1f2937",   # selected cell text

    # -----------------------------------------------------------------------
    # Table
    # -----------------------------------------------------------------------
    "table_grid":             "#e1e6ef",   # grid line colour
    "table_alt":              "#fbfcfe",   # alternating row bg
    "table_hover_bg":         "#f1f4fa",   # hovered (unselected) row

    # -----------------------------------------------------------------------
    # Semantic States
    # -----------------------------------------------------------------------

    # Info / Recording (blue)
    "state_info_text":        "#1e40af",
    "state_info_bg":          "#eff6ff",
    "state_info_border":      "#bfdbfe",
    "state_info_hover":       "#1d4ed8",

    # Warning / Prepare (amber)
    "state_warn_text":        "#92400e",
    "state_warn_bg":          "#fef3c7",
    "state_warn_border":      "#f3d5a7",
    "state_warn_accent":      "#f59e0b",

    # Success / Finished (green — reuses primary)
    "state_success_text":     "#2d5a27",
    "state_success_bg":       "#e8f5e9",
    "state_success_border":   "#a7d9a0",

    # Error (red)
    "state_error_accent":     "#f87171",

    # -----------------------------------------------------------------------
    # Typography
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
    # Border Radius
    # -----------------------------------------------------------------------
    "radius_xs":              "4px",
    "radius_sm":              "6px",
    "radius_md":              "8px",
    "radius_lg":              "12px",
    "radius_xl":              "14px",
    "radius_2xl":             "16px",
    "radius_3xl":             "18px",
}
