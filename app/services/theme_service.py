"""Per-user custom theme service.

Builds the ``<style>`` block injected into every authenticated page so
users can customise the look of TimeTracker without touching any global
CSS file. Combines:

* a built-in catalogue of themes (:data:`BUILT_IN_THEMES`), and
* the four optional per-user overrides stored on
  :class:`~app.models.user.User` (``theme_accent_color``,
  ``theme_sidebar_style``, ``theme_font_size``, ``theme_border_radius``).

The service is defensive: any failure to read a user attribute simply
falls back to defaults and returns an empty string, so an unmigrated
database (or an unauthenticated request) never breaks rendering. All
inputs that end up in the generated CSS are validated against explicit
allow-lists before being embedded, so user data can never inject
arbitrary CSS.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from app import db

logger = logging.getLogger(__name__)


_HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

ALLOWED_SIDEBAR_STYLES = ("default", "compact", "minimal")
ALLOWED_FONT_SIZES = ("sm", "base", "lg")
ALLOWED_BORDER_RADII = ("none", "default", "full")

# 10-colour preset palette exposed in the theme picker. Mirrors the
# Tailwind 500-shade palette so the swatches feel consistent with the
# rest of the UI (and with the per-theme accent colours below).
ACCENT_PRESETS = (
    "#3b82f6",  # blue-500
    "#0ea5e9",  # sky-500
    "#06b6d4",  # cyan-500
    "#10b981",  # emerald-500
    "#16a34a",  # green-600
    "#eab308",  # yellow-500
    "#f59e0b",  # amber-500
    "#ea580c",  # orange-600
    "#e11d48",  # rose-600
    "#7c3aed",  # violet-600
)


BUILT_IN_THEMES: Dict[str, Dict[str, Any]] = {
    "default": {
        "label": "Default",
        "description": "The classic TimeTracker look — inherits all current colours.",
        "preview_colors": ["#3b82f6", "#1f2937", "#f9fafb"],
        "accent": "#3b82f6",
        "vars": {
            # No overrides – the default theme intentionally relies on the
            # existing Tailwind classes so existing users see no change.
        },
    },
    "ocean": {
        "label": "Ocean",
        "description": "Cool blues inspired by deep water.",
        "preview_colors": ["#0c4a6e", "#0ea5e9", "#e0f2fe"],
        "accent": "#0ea5e9",
        "vars": {
            "--sidebar-bg": "#0c4a6e",
            "--sidebar-text": "#e0f2fe",
            "--sidebar-hover": "#075985",
            "--sidebar-active": "#0369a1",
            "--nav-accent": "#38bdf8",
        },
    },
    "forest": {
        "label": "Forest",
        "description": "Calm greens for focused, grounded sessions.",
        "preview_colors": ["#14532d", "#16a34a", "#dcfce7"],
        "accent": "#16a34a",
        "vars": {
            "--sidebar-bg": "#14532d",
            "--sidebar-text": "#dcfce7",
            "--sidebar-hover": "#166534",
            "--sidebar-active": "#15803d",
            "--nav-accent": "#4ade80",
        },
    },
    "sunset": {
        "label": "Sunset",
        "description": "Warm oranges and reds for the end of the day.",
        "preview_colors": ["#431407", "#ea580c", "#ffedd5"],
        "accent": "#ea580c",
        "vars": {
            "--sidebar-bg": "#431407",
            "--sidebar-text": "#ffedd5",
            "--sidebar-hover": "#7c2d12",
            "--sidebar-active": "#9a3412",
            "--nav-accent": "#fb923c",
        },
    },
    "lavender": {
        "label": "Lavender",
        "description": "Soft purples for a relaxed, creative mood.",
        "preview_colors": ["#2e1065", "#7c3aed", "#ede9fe"],
        "accent": "#7c3aed",
        "vars": {
            "--sidebar-bg": "#2e1065",
            "--sidebar-text": "#ede9fe",
            "--sidebar-hover": "#4c1d95",
            "--sidebar-active": "#5b21b6",
            "--nav-accent": "#a78bfa",
        },
    },
    "rose": {
        "label": "Rose",
        "description": "Bold roses and pinks for a vibrant workspace.",
        "preview_colors": ["#4c0519", "#e11d48", "#ffe4e6"],
        "accent": "#e11d48",
        "vars": {
            "--sidebar-bg": "#4c0519",
            "--sidebar-text": "#ffe4e6",
            "--sidebar-hover": "#881337",
            "--sidebar-active": "#9f1239",
            "--nav-accent": "#fb7185",
        },
    },
    "slate": {
        "label": "Slate",
        "description": "Neutral, professional greys that fade into the background.",
        "preview_colors": ["#0f172a", "#475569", "#e2e8f0"],
        "accent": "#475569",
        "vars": {
            "--sidebar-bg": "#0f172a",
            "--sidebar-text": "#e2e8f0",
            "--sidebar-hover": "#1e293b",
            "--sidebar-active": "#334155",
            "--nav-accent": "#94a3b8",
        },
    },
    "high-contrast": {
        "label": "High contrast",
        "description": "Maximum contrast for improved readability and accessibility.",
        "preview_colors": ["#000000", "#ffffff", "#333333"],
        "accent": "#000000",
        "vars": {
            "--sidebar-bg": "#000000",
            "--sidebar-text": "#ffffff",
            "--sidebar-hover": "#1a1a1a",
            "--sidebar-active": "#333333",
            "--nav-accent": "#ffffff",
            "--text-primary": "#000000",
            "--bg-primary": "#ffffff",
        },
    },
}


def _hex_to_rgb(hex_str: str) -> Optional[tuple]:
    if not hex_str or not _HEX_COLOR_RE.match(hex_str):
        return None
    h = hex_str[1:]
    try:
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except ValueError:
        return None


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return "#{:02x}{:02x}{:02x}".format(
        max(0, min(255, int(r))),
        max(0, min(255, int(g))),
        max(0, min(255, int(b))),
    )


def _lighten(hex_str: str, factor: float = 0.1) -> str:
    """Lighten ``hex_str`` by ``factor`` (0..1). Used for hover states.

    Implementation matches the spec: shift each RGB channel toward 255
    by ``factor`` of the remaining distance to white.
    """
    rgb = _hex_to_rgb(hex_str)
    if not rgb:
        return hex_str
    r, g, b = rgb
    factor = max(0.0, min(1.0, factor))
    return _rgb_to_hex(
        r + (255 - r) * factor,
        g + (255 - g) * factor,
        b + (255 - b) * factor,
    )


def _rgba(hex_str: str, alpha: float) -> str:
    rgb = _hex_to_rgb(hex_str)
    if not rgb:
        return hex_str
    r, g, b = rgb
    alpha = max(0.0, min(1.0, float(alpha)))
    return f"rgba({r}, {g}, {b}, {alpha:g})"


def _safe_attr(user: Any, name: str, default: Any = None) -> Any:
    """Defensive attribute access — never raises, never returns blank str."""
    try:
        value = getattr(user, name, default)
    except Exception:
        return default
    if value is None or (isinstance(value, str) and not value.strip()):
        return default
    return value


class ThemeService:
    """Inject + persist per-user custom theme preferences."""

    # --------------------------------------------------------------- catalogue

    @staticmethod
    def get_all_themes() -> List[Dict[str, Any]]:
        """Return list of all built-in themes, ``default`` first then alpha."""
        result: List[Dict[str, Any]] = []
        for name, data in BUILT_IN_THEMES.items():
            result.append(
                {
                    "name": name,
                    "label": data.get("label", name.title()),
                    "description": data.get("description", ""),
                    "accent": data.get("accent"),
                    "preview_colors": list(data.get("preview_colors") or []),
                }
            )

        def _sort_key(theme: Dict[str, Any]) -> tuple:
            return (0 if theme["name"] == "default" else 1, theme["name"])

        result.sort(key=_sort_key)
        return result

    @staticmethod
    def get_accent_presets() -> List[str]:
        """Return the 10-colour preset palette used by the picker."""
        return list(ACCENT_PRESETS)

    # --------------------------------------------------------------- validate

    @staticmethod
    def validate_accent_color(hex_str: Optional[str]) -> bool:
        """Strict ``#RRGGBB`` (6 hex digits only) — used before embedding."""
        return bool(hex_str) and bool(_HEX_COLOR_RE.match(str(hex_str)))

    @staticmethod
    def _normalise_theme_name(value: Optional[str]) -> str:
        if not value:
            return "default"
        key = str(value).strip().lower()
        if key in BUILT_IN_THEMES:
            return key
        return "default"

    @staticmethod
    def _validate_sidebar_style(value: Optional[str]) -> str:
        return value if value in ALLOWED_SIDEBAR_STYLES else "default"

    @staticmethod
    def _validate_font_size(value: Optional[str]) -> str:
        return value if value in ALLOWED_FONT_SIZES else "base"

    @staticmethod
    def _validate_border_radius(value: Optional[str]) -> str:
        return value if value in ALLOWED_BORDER_RADII else "default"

    # --------------------------------------------------------------- CSS build

    def get_theme_css_vars(self, user: Any) -> str:
        """Return a complete ``<style id="tt-theme-vars">`` block.

        Returns an empty string when the user is anonymous, the theme
        columns are missing (migration not run), or the user is on the
        default theme with no custom overrides — there's no point
        emitting a no-op block in that case.
        """
        if user is None:
            return ""
        # Anonymous users (where AnonymousUserMixin is passed in) have
        # ``is_authenticated`` = False but no theme attributes either.
        try:
            if not getattr(user, "is_authenticated", False):
                return ""
        except Exception:
            return ""

        theme_name = self._normalise_theme_name(_safe_attr(user, "theme_name", "default"))
        accent_override = _safe_attr(user, "theme_accent_color", None)
        sidebar_style = self._validate_sidebar_style(_safe_attr(user, "theme_sidebar_style", "default"))
        font_size = self._validate_font_size(_safe_attr(user, "theme_font_size", "base"))
        border_radius = self._validate_border_radius(_safe_attr(user, "theme_border_radius", "default"))

        theme = BUILT_IN_THEMES.get(theme_name) or BUILT_IN_THEMES["default"]

        # Decide whether we need to emit anything at all.
        is_default_theme = theme_name == "default"
        has_overrides = (
            (accent_override and self.validate_accent_color(accent_override))
            or sidebar_style != "default"
            or font_size != "base"
            or border_radius != "default"
        )
        if is_default_theme and not has_overrides:
            return ""

        # ---------- Compute final accent + derived hover/muted values
        accent = theme.get("accent")
        if accent_override and self.validate_accent_color(accent_override):
            accent = accent_override
        if not self.validate_accent_color(accent or ""):
            accent = "#3b82f6"

        accent_hover = _lighten(accent, 0.1)
        accent_muted = _rgba(accent, 0.2)

        # ---------- Assemble CSS variables
        css_vars: Dict[str, str] = {
            "--color-accent": accent,
            "--color-accent-hover": accent_hover,
            "--color-accent-muted": accent_muted,
        }

        # Built-in theme variables (already trusted, defined above).
        for var_name, var_value in (theme.get("vars") or {}).items():
            # Defence in depth: only emit values that look like a hex
            # colour or a simple keyword/number, never anything else.
            if isinstance(var_value, str) and (
                _HEX_COLOR_RE.match(var_value) or re.match(r"^[a-zA-Z0-9_#\-.,()% ]+$", var_value)
            ):
                css_vars[var_name] = var_value

        # ---------- Sidebar style
        sidebar_width = "16rem"  # default Tailwind w-64 width
        sidebar_hover_width = sidebar_width
        sidebar_show_labels = "inline"
        if sidebar_style == "compact":
            sidebar_width = "56px"
            sidebar_hover_width = "56px"
            sidebar_show_labels = "none"
        elif sidebar_style == "minimal":
            sidebar_width = "0px"
            sidebar_hover_width = "220px"
        css_vars["--sidebar-width"] = sidebar_width
        css_vars["--sidebar-hover-width"] = sidebar_hover_width
        css_vars["--sidebar-show-labels"] = sidebar_show_labels

        # ---------- Font size
        font_base = {"sm": "13px", "base": "16px", "lg": "17px"}[font_size]
        css_vars["--font-size-base"] = font_base

        # ---------- Corner radius
        if border_radius == "none":
            css_vars["--border-radius-md"] = "0px"
            css_vars["--border-radius-lg"] = "0px"
            css_vars["--border-radius-xl"] = "0px"
        elif border_radius == "full":
            css_vars["--border-radius-md"] = "9999px"
            css_vars["--border-radius-lg"] = "9999px"
            css_vars["--border-radius-xl"] = "9999px"
        else:
            css_vars["--border-radius-md"] = "0.5rem"
            css_vars["--border-radius-lg"] = "0.75rem"
            css_vars["--border-radius-xl"] = "1rem"

        # ---------- Emit
        lines: List[str] = []
        lines.append('<style id="tt-theme-vars">')
        lines.append(":root {")
        for key in sorted(css_vars.keys()):
            lines.append(f"  {key}: {css_vars[key]};")
        lines.append("}")

        # Theme-aware rules. These deliberately use ``!important`` so
        # they win against the existing utility classes baked into the
        # markup (which we never touch).
        has_sidebar_vars = any(k.startswith("--sidebar-") or k == "--nav-accent" for k in css_vars)
        if has_sidebar_vars and "--sidebar-bg" in css_vars:
            lines.append(
                "#sidebar { background-color: var(--sidebar-bg) !important; " "color: var(--sidebar-text) !important; }"
            )
            lines.append(
                "#sidebar .sidebar-label, "
                "#sidebar h1, "
                "#sidebar .sidebar-header-title "
                "{ color: var(--sidebar-text) !important; }"
            )

        # Width / sidebar style rules. Skip the rule entirely when the
        # user is on the default sidebar style (no visual change).
        if sidebar_style != "default":
            lines.append(
                "#sidebar { width: var(--sidebar-width, 16rem) !important; "
                "transition: width 0.2s ease; overflow: hidden; }"
            )
            if sidebar_style == "minimal":
                lines.append(
                    "#sidebar:hover, #sidebar:focus-within " "{ width: var(--sidebar-hover-width, 220px) !important; }"
                )
            if sidebar_style == "compact":
                lines.append(
                    "#sidebar .sidebar-label, "
                    "#sidebar .sidebar-header-title "
                    "{ display: var(--sidebar-show-labels, inline) !important; }"
                )

        # Hover / active nav rules (always emitted when any sidebar var
        # is present so the picker preview is immediately visible).
        if has_sidebar_vars:
            lines.append(".sidebar-nav-item:hover { " "background-color: var(--sidebar-hover) !important; }")
            lines.append(
                ".sidebar-nav-item.active, "
                "#sidebar .sidebar-nav-item.active { "
                "background-color: var(--sidebar-active) !important; }"
            )

        # Body / link / primary button rules.
        lines.append("body { font-size: var(--font-size-base, 16px); }")
        lines.append("a, button { color: inherit; }")
        lines.append(
            ".btn-primary, [data-theme-accent] { "
            "background-color: var(--color-accent) !important; "
            "border-color: var(--color-accent) !important; color: #fff !important; }"
        )
        lines.append(
            ".btn-primary:hover, [data-theme-accent]:hover { "
            "background-color: var(--color-accent-hover) !important; "
            "border-color: var(--color-accent-hover) !important; }"
        )

        # Border-radius overrides (only when not default).
        if border_radius != "default":
            radius = "0px" if border_radius == "none" else "9999px"
            lines.append(
                ".rounded, .rounded-md, .rounded-lg, .rounded-xl, "
                ".rounded-2xl, .rounded-3xl { border-radius: "
                f"{radius} !important; }}"
            )

        lines.append("</style>")
        return "\n".join(lines)

    # --------------------------------------------------------------- persistence

    def save_user_theme(
        self,
        user: Any,
        theme_name: Optional[str] = None,
        accent_color: Optional[str] = None,
        sidebar_style: Optional[str] = None,
        font_size: Optional[str] = None,
        border_radius: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Validate inputs and persist them on ``user``.

        Returns ``{"ok": True}`` on success or ``{"ok": False, "error": ...}``
        for any validation problem. Never raises.
        """
        if user is None or not getattr(user, "is_authenticated", False):
            return {"ok": False, "error": "not_authenticated"}

        # ----- theme_name
        if theme_name is not None:
            normalised_theme = self._normalise_theme_name(theme_name)
            if normalised_theme not in BUILT_IN_THEMES:
                return {"ok": False, "error": "invalid_theme_name"}
        else:
            normalised_theme = self._normalise_theme_name(_safe_attr(user, "theme_name", "default"))

        # ----- accent_color (nullable)
        if accent_color in (None, "", "null"):
            accent_to_save: Optional[str] = None
        else:
            accent_str = str(accent_color).strip()
            if not self.validate_accent_color(accent_str):
                return {"ok": False, "error": "invalid_accent_color"}
            # Lowercase canonical form so the value embedded in CSS is
            # consistent and the equality check in the picker always
            # finds the matching preset.
            accent_to_save = accent_str.lower()

        # ----- sidebar_style
        if sidebar_style is None:
            sidebar_to_save = self._validate_sidebar_style(_safe_attr(user, "theme_sidebar_style", "default"))
        elif sidebar_style in ALLOWED_SIDEBAR_STYLES:
            sidebar_to_save = sidebar_style
        else:
            return {"ok": False, "error": "invalid_sidebar_style"}

        # ----- font_size
        if font_size is None:
            font_to_save = self._validate_font_size(_safe_attr(user, "theme_font_size", "base"))
        elif font_size in ALLOWED_FONT_SIZES:
            font_to_save = font_size
        else:
            return {"ok": False, "error": "invalid_font_size"}

        # ----- border_radius
        if border_radius is None:
            radius_to_save = self._validate_border_radius(_safe_attr(user, "theme_border_radius", "default"))
        elif border_radius in ALLOWED_BORDER_RADII:
            radius_to_save = border_radius
        else:
            return {"ok": False, "error": "invalid_border_radius"}

        # ----- Persist
        try:
            if hasattr(user, "theme_name"):
                user.theme_name = normalised_theme
            if hasattr(user, "theme_accent_color"):
                user.theme_accent_color = accent_to_save
            if hasattr(user, "theme_sidebar_style"):
                user.theme_sidebar_style = sidebar_to_save
            if hasattr(user, "theme_font_size"):
                user.theme_font_size = font_to_save
            if hasattr(user, "theme_border_radius"):
                user.theme_border_radius = radius_to_save
            db.session.commit()
        except Exception as exc:
            try:
                db.session.rollback()
            except Exception:
                pass
            logger.warning("Could not save user theme: %s", exc)
            return {"ok": False, "error": "save_failed"}

        return {"ok": True}


# Module-level singleton for ergonomic import in templates / context
# processors (instantiating is cheap, but keeps the call sites tidy).
theme_service = ThemeService()
