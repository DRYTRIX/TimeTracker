"""
Shared validation for time entry requirements (task, description).

Used when creating/updating time entries and when starting timers.
"""

from typing import Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.settings import Settings


def validate_time_entry_requirements(
    settings: "Settings",
    project_id: Optional[int],
    client_id: Optional[int],
    task_id: Optional[int],
    notes: Optional[str],
) -> Optional[Dict[str, Any]]:
    """
    Validate time entry requirements based on admin settings.

    Returns error dict with keys: success=False, message, error; or None if valid.

    Rules:
    - time_entry_require_task: Only when project_id is set; task_id must be non-null.
    - time_entry_require_description: notes must be non-empty and meet min length.
    - Client-only entries (client_id set, no project_id): task requirement does not apply.
    """
    require_task = getattr(settings, "time_entry_require_task", False)
    require_description = getattr(settings, "time_entry_require_description", False)
    min_length = getattr(settings, "time_entry_description_min_length", 20)

    if not require_task and not require_description:
        return None

    # Task requirement: only when project_id is set (not client-only)
    if require_task and project_id and not task_id:
        return {
            "success": False,
            "message": "A task must be selected when logging time for a project",
            "error": "task_required",
        }

    # Description requirement
    if require_description:
        notes_stripped = (notes or "").strip()
        if not notes_stripped:
            return {
                "success": False,
                "message": "A description is required when logging time",
                "error": "description_required",
            }
        if len(notes_stripped) < min_length:
            return {
                "success": False,
                "message": f"Description must be at least {min_length} characters",
                "error": "description_too_short",
            }

    return None
