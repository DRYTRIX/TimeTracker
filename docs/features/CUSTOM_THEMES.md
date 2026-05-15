# Custom themes

## Overview

TimeTracker ships with a small catalogue of built-in themes that any
authenticated user can pick from their settings page, plus four
optional per-user overrides for accent colour, sidebar style, text size
and corner radius.

Themes are applied on every page load via a tiny `<style>` block
injected into `<head>`. They never replace existing CSS files, never
require recompiling Tailwind, and gracefully no-op for users on the
default theme — so existing installations look identical to before
unless someone opts in.

Navigation: **Settings → Custom theme**.

## Built-in themes

| Name            | Accent  | Notes                                                  |
|-----------------|---------|--------------------------------------------------------|
| `default`       | #3b82f6 | The classic TimeTracker look — no overrides applied.   |
| `ocean`         | #0ea5e9 | Deep blue sidebar with sky accents.                    |
| `forest`        | #16a34a | Calm greens.                                           |
| `sunset`        | #ea580c | Warm oranges and reds.                                 |
| `lavender`      | #7c3aed | Soft purples.                                          |
| `rose`          | #e11d48 | Bold roses and pinks.                                  |
| `slate`         | #475569 | Neutral, professional greys.                           |
| `high-contrast` | #000000 | Pure black/white for maximum readability.              |

Each theme is defined as a dict of CSS variable overrides in
[`app/services/theme_service.py`](../../app/services/theme_service.py)
under `BUILT_IN_THEMES`. The variables it touches are deliberately
scoped:

- `--color-accent`, `--color-accent-hover`, `--color-accent-muted`
- `--sidebar-bg`, `--sidebar-text`, `--sidebar-hover`, `--sidebar-active`
- `--nav-accent`
- `--font-size-base`
- `--border-radius-md`, `--border-radius-lg`, `--border-radius-xl`
- `--sidebar-width`, `--sidebar-hover-width`

## Per-user customisations

In addition to picking a theme, each user can independently override:

- **Accent colour** — any `#RRGGBB` hex value, or one of 10 preset
  palette colours. Hover and muted variants are derived automatically
  (`+10%` lightness and `20%` alpha respectively).
- **Sidebar** — `default` (16 rem), `compact` (56 px icon rail) or
  `minimal` (collapsed, expands to 220 px on hover).
- **Text size** — `sm` (13 px), `base` (16 px) or `lg` (17 px).
- **Corners** — `none` (0 px), `default` (Tailwind values) or `full`
  (9999 px / pill).

All five values are validated server-side against explicit allow-lists
before being persisted or embedded in CSS, so theme settings can never
be used to inject arbitrary styles.

## How it is applied

1. A context processor in
   [`app/utils/context_processors.py`](../../app/utils/context_processors.py)
   (`inject_theme`) runs on every request and exposes a `theme_css`
   string to all templates.
2. [`app/templates/base.html`](../../app/templates/base.html) renders
   `{{ theme_css | safe }}` immediately after the existing stylesheet
   `<link>` tags.
3. The string is the full `<style id="tt-theme-vars"> :root { … } </style>`
   block, containing both `:root` CSS variables and any theme-aware
   rules (sidebar background, hover/active nav items, primary button
   accent, body font size, etc.).
4. For the **default** theme with no per-user overrides, `theme_css`
   is the empty string — so existing users see zero visual change and
   no inline `<style>` block is added.

`ThemeService` reads every user attribute through
`getattr(user, 'theme_name', 'default')`, so the system degrades
gracefully on databases where migration `156_add_user_theme_columns`
has not yet run.

## Theme picker UI

The picker lives in
[`app/templates/components/theme_picker.html`](../../app/templates/components/theme_picker.html)
and is included from
[`app/templates/user/settings.html`](../../app/templates/user/settings.html).
It is fully self-contained:

- responsive swatch grid (3 columns on mobile, 4 on `md`, 8 on `lg`)
- collapsible **Customise** section (accent presets + colour picker +
  pill button groups)
- **Save** and **Reset to default** buttons in the action row

Clicking a swatch or any control fires a debounced live preview by
`POST /api/user/theme` and swaps the `<style id="tt-theme-vars">`
block with the regenerated one returned by the API — no page reload
required. The state is only persisted to the database when **Save** is
clicked. Vanilla JS only; no framework dependency.

## API

```
GET /api/user/theme
```

**Authentication:** session cookie (`@login_required`).

**Response (200):**

```json
{
  "ok": true,
  "current": {
    "theme_name": "ocean",
    "accent_color": null,
    "sidebar_style": "default",
    "font_size": "base",
    "border_radius": "default"
  },
  "themes": [
    {
      "name": "default",
      "label": "Default",
      "description": "The classic TimeTracker look — …",
      "accent": "#3b82f6",
      "preview_colors": ["#3b82f6", "#1f2937", "#f9fafb"]
    }
    // …
  ],
  "accent_presets": ["#3b82f6", "#0ea5e9", "#06b6d4", "…"],
  "css": "<style id=\"tt-theme-vars\">…</style>"
}
```

```
POST /api/user/theme
Content-Type: application/json

{
  "theme_name": "ocean",
  "accent_color": "#abcdef",
  "sidebar_style": "compact",
  "font_size": "lg",
  "border_radius": "full"
}
```

- All five fields are optional. Omitted fields keep their existing
  value. `accent_color` accepts `null`/`""` to revert to the theme’s
  default accent.
- Returns `{"ok": true, "css": "<style …>…</style>"}` on success so
  the caller can swap the page’s theme block for an instant live
  preview.
- Returns `400` with `{"ok": false, "error": "invalid_accent_color"}`
  (or similar) on validation failure. Allowed error codes:
  `invalid_theme_name`, `invalid_accent_color`,
  `invalid_sidebar_style`, `invalid_font_size`,
  `invalid_border_radius`, `save_failed`, `not_authenticated`.

## Database schema

Migration
[`156_add_user_theme_columns`](../../migrations/versions/156_add_user_theme_columns.py)
adds five nullable columns to the `users` table (defensively — each
column is only added if missing):

| Column                  | Type        | Default     | Notes                                            |
|-------------------------|-------------|-------------|--------------------------------------------------|
| `theme_name`            | String(50)  | `"default"` | One of the keys in `BUILT_IN_THEMES`.            |
| `theme_accent_color`    | String(7)   | `NULL`      | Hex `#RRGGBB`; `NULL` falls back to theme accent.|
| `theme_sidebar_style`   | String(20)  | `"default"` | `default` / `compact` / `minimal`.               |
| `theme_font_size`       | String(10)  | `"base"`    | `sm` / `base` / `lg`.                            |
| `theme_border_radius`   | String(10)  | `"default"` | `none` / `default` / `full`.                     |

Run with `flask db upgrade` after pulling the change.

## Files of interest

- [`app/services/theme_service.py`](../../app/services/theme_service.py)
  — `BUILT_IN_THEMES`, `ACCENT_PRESETS`, and the `ThemeService` class
  (CSS generation, validation, persistence).
- [`app/templates/components/theme_picker.html`](../../app/templates/components/theme_picker.html)
  — the self-contained picker component.
- [`app/utils/context_processors.py`](../../app/utils/context_processors.py)
  — `inject_theme` context processor.
- [`app/routes/api.py`](../../app/routes/api.py) — `GET` / `POST
  /api/user/theme` endpoints.
- [`migrations/versions/156_add_user_theme_columns.py`](../../migrations/versions/156_add_user_theme_columns.py)
  — Alembic revision.

## Security notes

- Every value embedded in the generated CSS goes through one of:
  - the strict `#RRGGBB` regex (`validate_accent_color`), or
  - an explicit allow-list (`ALLOWED_SIDEBAR_STYLES`,
    `ALLOWED_FONT_SIZES`, `ALLOWED_BORDER_RADII`), or
  - a per-theme catalogue defined in source code.

  Free-form user input therefore cannot appear in the page as CSS.
- The service returns `""` and the context processor falls back to a
  blank string on any exception, so a broken theme can never break
  page rendering.
- Dark mode is unchanged — themes set CSS variables that work
  alongside Tailwind’s existing `dark:` prefix; no theme overrides the
  dark-mode detection.
