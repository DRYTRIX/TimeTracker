"""
Keyboard shortcut default registry and validation.

Canonical list of shortcut IDs and default keys, aligned with
keyboard-shortcuts-advanced.js. Used by the API to return merged config
and to validate user overrides (conflicts, forbidden keys).
"""
import re
from typing import Any

# Default shortcuts: id, default_key, name, description, category, context.
# default_key must be normalized (lowercase, Ctrl not Cmd).
# Order determines display order in settings; group by category.
DEFAULT_SHORTCUTS = [
    # Global
    {"id": "global_command_palette", "default_key": "ctrl+k", "name": "Open command palette", "description": "Open command palette", "category": "Global", "context": "global"},
    {"id": "global_search", "default_key": "ctrl+/", "name": "Toggle search", "description": "Focus search box", "category": "Global", "context": "global"},
    {"id": "global_sidebar", "default_key": "ctrl+b", "name": "Toggle sidebar", "description": "Show/hide the sidebar", "category": "Global", "context": "global"},
    {"id": "appearance_dark_mode", "default_key": "ctrl+d", "name": "Toggle dark mode", "description": "Switch between light and dark themes", "category": "Appearance", "context": "global"},
    {"id": "help_shortcuts_panel", "default_key": "shift+/", "name": "Show keyboard shortcuts", "description": "Show keyboard shortcuts cheat sheet", "category": "Help", "context": "global"},
    {"id": "actions_quick_actions", "default_key": "shift+?", "name": "Show quick actions", "description": "Show quick actions menu", "category": "Actions", "context": "global"},
    # Navigation
    {"id": "nav_dashboard", "default_key": "g d", "name": "Go to Dashboard", "description": "Navigate to the main dashboard", "category": "Navigation", "context": "global"},
    {"id": "nav_projects", "default_key": "g p", "name": "Go to Projects", "description": "View all projects", "category": "Navigation", "context": "global"},
    {"id": "nav_tasks", "default_key": "g t", "name": "Go to Tasks", "description": "View all tasks", "category": "Navigation", "context": "global"},
    {"id": "nav_reports", "default_key": "g r", "name": "Go to Reports", "description": "View reports", "category": "Navigation", "context": "global"},
    {"id": "nav_invoices", "default_key": "g i", "name": "Go to Invoices", "description": "View all invoices", "category": "Navigation", "context": "global"},
    # Create
    {"id": "create_project", "default_key": "c p", "name": "Create new project", "description": "Create a new project", "category": "Actions", "context": "global"},
    {"id": "create_task", "default_key": "c t", "name": "Create new task", "description": "Create a new task", "category": "Actions", "context": "global"},
    {"id": "create_client", "default_key": "c c", "name": "Create new client", "description": "Create a new client", "category": "Actions", "context": "global"},
    # Timer
    {"id": "timer_start", "default_key": "t s", "name": "Start timer", "description": "Start a new timer", "category": "Timer", "context": "global"},
    {"id": "timer_pause", "default_key": "t p", "name": "Pause timer", "description": "Pause or stop the active timer", "category": "Timer", "context": "global"},
    {"id": "timer_log", "default_key": "t l", "name": "Log time manually", "description": "Log time manually", "category": "Timer", "context": "global"},
    # Table
    {"id": "table_select_all", "default_key": "ctrl+a", "name": "Select all rows", "description": "Select all rows in the table", "category": "Table", "context": "table"},
    {"id": "table_delete", "default_key": "delete", "name": "Delete selected", "description": "Delete selected rows", "category": "Table", "context": "table"},
    {"id": "table_clear_selection", "default_key": "escape", "name": "Clear selection", "description": "Clear table selection", "category": "Table", "context": "table"},
    # Modal
    {"id": "modal_close", "default_key": "escape", "name": "Close modal", "description": "Close the active modal", "category": "Modal", "context": "modal"},
    {"id": "modal_submit", "default_key": "enter", "name": "Submit form", "description": "Submit form in modal", "category": "Modal", "context": "modal"},
    # Editing
    {"id": "editing_save", "default_key": "ctrl+s", "name": "Save changes", "description": "Save the current form", "category": "Editing", "context": "editing"},
    {"id": "editing_undo", "default_key": "ctrl+z", "name": "Undo", "description": "Undo last action", "category": "Editing", "context": "global"},
    {"id": "editing_redo", "default_key": "ctrl+shift+z", "name": "Redo", "description": "Redo last action", "category": "Editing", "context": "global"},
]

# Keys that cannot be assigned (browser/OS behavior: close tab, new window, etc.)
FORBIDDEN_KEYS = frozenset({
    "ctrl+w",
    "ctrl+n",
    "ctrl+t",
    "alt+f4",
    "ctrl+shift+w",
})


def normalize_key(key: str) -> str:
    """Normalize a key combo for storage and comparison. Matches frontend logic."""
    if not key or not isinstance(key, str):
        return ""
    s = key.strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"command|cmd", "ctrl", s)
    return s


def get_defaults_by_id() -> dict[str, dict[str, Any]]:
    """Return a dict id -> default shortcut entry (with default_key normalized)."""
    by_id = {}
    for entry in DEFAULT_SHORTCUTS:
        e = dict(entry)
        e["default_key"] = normalize_key(e["default_key"])
        by_id[e["id"]] = e
    return by_id


def merge_overrides(overrides: dict[str, str] | None) -> list[dict[str, Any]]:
    """
    Merge user overrides with defaults. Returns list of shortcuts with
    default_key and current_key (effective key for each id).
    """
    overrides = overrides or {}
    by_id = get_defaults_by_id()
    result = []
    for sid, entry in by_id.items():
        current = normalize_key(overrides.get(sid, "")) or entry["default_key"]
        result.append({
            "id": sid,
            "name": entry["name"],
            "description": entry["description"],
            "category": entry["category"],
            "context": entry["context"],
            "default_key": entry["default_key"],
            "current_key": current,
        })
    return result


def validate_overrides(
    overrides: dict[str, str] | None,
) -> tuple[bool, str | None, list[dict[str, Any]] | None, dict[str, str] | None]:
    """
    Validate overrides and return merged shortcuts and the dict to persist if valid.

    Returns:
        (True, None, merged_shortcuts, overrides_to_save) on success
        (False, error_message, None, None) on validation failure
    """
    overrides = overrides or {}
    by_id = get_defaults_by_id()

    # Normalize and validate each override key
    normalized_overrides: dict[str, str] = {}
    for sid, key in overrides.items():
        if sid not in by_id:
            return False, f"Unknown shortcut id: {sid}", None, None
        nkey = normalize_key(key)
        if not nkey:
            # Empty key = revert to default (don't store)
            continue
        if nkey in FORBIDDEN_KEYS:
            return False, f"Forbidden key: {key}", None, None
        normalized_overrides[sid] = nkey

    # Build effective key per id and check for duplicates (conflicts) per context
    effective: dict[str, str] = {}
    for sid, entry in by_id.items():
        effective[sid] = normalized_overrides.get(sid) or entry["default_key"]

    # Conflict: same (context, key) used by more than one id
    context_key_to_ids: dict[tuple[str, str], list[str]] = {}
    for sid, current in effective.items():
        ctx = by_id[sid]["context"]
        context_key_to_ids.setdefault((ctx, current), []).append(sid)
    for (_ctx, current), ids in context_key_to_ids.items():
        if len(ids) > 1:
            return False, f"Conflict: key '{current}' is assigned to multiple actions", None, None

    merged = merge_overrides(normalized_overrides)
    # Only persist overrides that differ from default
    overrides_to_save = {
        sid: key for sid, key in normalized_overrides.items()
        if by_id[sid]["default_key"] != key
    }
    return True, None, merged, overrides_to_save
