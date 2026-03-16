# Keyboard Shortcuts – Developer Guide

## Persistence and API

- **Storage**: Per-user overrides are stored in `User.keyboard_shortcuts_overrides` (JSON column). Keys are shortcut `id` → normalized key string (e.g. `"nav_dashboard": "g 1"`).
- **Defaults**: Canonical list is in `app/utils/keyboard_shortcuts_defaults.py` (`DEFAULT_SHORTCUTS`). Normalization (lowercase, `Cmd` → `Ctrl`) and forbidden keys are defined there.
- **Endpoints** (all require authenticated user):
  - `GET /api/settings/keyboard-shortcuts` — returns `{ shortcuts, overrides }`.
  - `POST /api/settings/keyboard-shortcuts` — body `{ "overrides": { "id": "key", ... } }`; validates then saves (only overrides that differ from default are stored).
  - `POST /api/settings/keyboard-shortcuts/reset` — clears overrides, returns full config.
- **Validation**: Conflicts are checked **per context**: the same key cannot be assigned to two actions in the same context. Forbidden keys (e.g. `ctrl+w`, `ctrl+n`, `alt+f4`) are rejected.

## Registering new shortcuts

To add a new keyboard shortcut that appears in the settings UI and supports user overrides:

1. **Backend** (`app/utils/keyboard_shortcuts_defaults.py`):
   - Append an entry to `DEFAULT_SHORTCUTS` with:
     - `id`: unique string (e.g. `"nav_analytics"`), used as the key for overrides.
     - `default_key`: normalized default key (e.g. `"g a"`).
     - `name`, `description`, `category`, `context` (e.g. `"global"`, `"table"`, `"modal"`).
   - No database migration is needed for new defaults; overrides are keyed by `id`.

2. **Frontend** (`app/static/keyboard-shortcuts-advanced.js`):
   - In `initDefaultShortcuts()`, call `this.register(...)` with the **same `id`** and the same default key as in `DEFAULT_SHORTCUTS`.
   - Example: `this.register('g a', () => this.navigateTo('/analytics'), { id: 'nav_analytics', description: 'Go to Analytics', category: 'Navigation' });`

3. **Conflict rules**: Avoid reusing the same `default_key` in the same `context` for another action; validation will flag duplicate effective keys per context. Forbidden keys are listed in `FORBIDDEN_KEYS` in `keyboard_shortcuts_defaults.py`.

After adding the entry to both the backend list and the JS registry, the new shortcut appears in the settings page and can be overridden by the user; the injected config and the API will include it automatically.
