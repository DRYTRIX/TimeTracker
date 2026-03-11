"""
API v1 - Tasks sub-blueprint.
Routes under /api/v1/tasks.
"""

from flask import Blueprint, jsonify, request, g
from app import db
from app.utils.api_auth import require_api_token

api_v1_tasks_bp = Blueprint("api_v1_tasks", __name__, url_prefix="/api/v1")


@api_v1_tasks_bp.route("/tasks", methods=["GET"])
@require_api_token("read:tasks")
def list_tasks():
    """List tasks."""
    from app.services import TaskService

    project_id = request.args.get("project_id", type=int)
    status = request.args.get("status")
    tags = request.args.get("tags", "").strip() or None
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)

    task_service = TaskService()
    result = task_service.list_tasks(
        project_id=project_id,
        status=status,
        tags=tags,
        page=page,
        per_page=per_page,
    )
    pagination = result["pagination"]
    pagination_dict = {
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "pages": pagination.pages,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
        "next_page": pagination.page + 1 if pagination.has_next else None,
        "prev_page": pagination.page - 1 if pagination.has_prev else None,
    }
    return jsonify({"tasks": [t.to_dict() for t in result["tasks"]], "pagination": pagination_dict})


@api_v1_tasks_bp.route("/tasks/<int:task_id>", methods=["GET"])
@require_api_token("read:tasks")
def get_task(task_id):
    """Get a specific task."""
    from sqlalchemy.orm import joinedload
    from app.models import Task

    task = (
        Task.query.options(
            joinedload(Task.project), joinedload(Task.assignee), joinedload(Task.created_by_user)
        )
        .filter_by(id=task_id)
        .first_or_404()
    )
    return jsonify({"task": task.to_dict()})


@api_v1_tasks_bp.route("/tasks", methods=["POST"])
@require_api_token("write:tasks")
def create_task():
    """Create a new task."""
    from app.services import TaskService

    data = request.get_json() or {}
    if not data.get("name"):
        return jsonify({"error": "Task name is required"}), 400
    if not data.get("project_id"):
        return jsonify({"error": "project_id is required"}), 400

    task_service = TaskService()
    result = task_service.create_task(
        name=data["name"],
        project_id=data["project_id"],
        created_by=g.api_user.id,
        description=data.get("description"),
        assignee_id=data.get("assignee_id"),
        priority=data.get("priority", "medium"),
        due_date=data.get("due_date"),
        estimated_hours=data.get("estimated_hours"),
        tags=data.get("tags"),
    )
    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not create task")}), 400
    return jsonify({"message": "Task created successfully", "task": result["task"].to_dict()}), 201


@api_v1_tasks_bp.route("/tasks/<int:task_id>", methods=["PUT", "PATCH"])
@require_api_token("write:tasks")
def update_task(task_id):
    """Update a task."""
    from app.services import TaskService

    data = request.get_json() or {}
    task_service = TaskService()
    update_kwargs = {}
    if "name" in data:
        update_kwargs["name"] = data["name"]
    if "description" in data:
        update_kwargs["description"] = data["description"]
    if "status" in data:
        update_kwargs["status"] = data["status"]
    if "priority" in data:
        update_kwargs["priority"] = data["priority"]
    if "assignee_id" in data:
        update_kwargs["assignee_id"] = data["assignee_id"]
    if "due_date" in data:
        update_kwargs["due_date"] = data["due_date"]
    if "estimated_hours" in data:
        update_kwargs["estimated_hours"] = data["estimated_hours"]
    if "tags" in data:
        update_kwargs["tags"] = data["tags"]

    result = task_service.update_task(task_id=task_id, user_id=g.api_user.id, **update_kwargs)
    if not result.get("success"):
        return jsonify({"error": result.get("message", "Could not update task")}), 400
    return jsonify({"message": "Task updated successfully", "task": result["task"].to_dict()})


@api_v1_tasks_bp.route("/tasks/<int:task_id>", methods=["DELETE"])
@require_api_token("write:tasks")
def delete_task(task_id):
    """Delete a task."""
    from app.repositories import TaskRepository

    task_repo = TaskRepository()
    task = task_repo.get_by_id(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    db.session.delete(task)
    db.session.commit()
    return jsonify({"message": "Task deleted successfully"})
