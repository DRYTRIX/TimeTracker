from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app import db
from app.models import CalendarEvent, Task, Project, Client, TimeEntry, CalendarIntegration
from app.services.calendar_integration_service import CalendarIntegrationService
from datetime import datetime, timedelta
from app.utils.db import safe_commit
from app.utils.timezone import now_in_app_timezone
from app.utils.permissions import check_permission
from app.utils.module_helpers import module_enabled
import os

calendar_bp = Blueprint("calendar", __name__)


@calendar_bp.route("/calendar")
@login_required
@module_enabled("calendar")
def view_calendar():
    """Display the calendar view with events, tasks, and time entries"""
    view_type = request.args.get("view", "month")  # day, week, month
    date_str = request.args.get("date", "")

    # Parse the date or use today
    if date_str:
        try:
            current_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            current_date = now_in_app_timezone()
    else:
        current_date = now_in_app_timezone()

    # Get projects and clients for event creation
    projects = Project.query.filter_by(status="active").order_by(Project.name).all()
    clients = Client.query.filter_by(is_active=True).order_by(Client.name).all()

    return render_template(
        "calendar/view.html", view_type=view_type, current_date=current_date, projects=projects, clients=clients
    )


@calendar_bp.route("/api/calendar/events")
@login_required
@module_enabled("calendar")
def get_events():
    """API endpoint to fetch calendar events for a date range"""
    start_str = request.args.get("start")
    end_str = request.args.get("end")
    include_tasks = request.args.get("include_tasks", "true").lower() == "true"
    include_time_entries = request.args.get("include_time_entries", "true").lower() == "true"

    print(f"\n{'='*80}")
    print(f"API ENDPOINT CALLED - /api/calendar/events")
    print(f"  include_tasks query param: {request.args.get('include_tasks')}")
    print(f"  include_time_entries query param: {request.args.get('include_time_entries')}")
    print(f"  include_tasks parsed: {include_tasks}")
    print(f"  include_time_entries parsed: {include_time_entries}")
    print(f"{'='*80}\n")

    if not start_str or not end_str:
        return jsonify({"error": "Start and end dates are required"}), 400

    try:
        start_date = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
        end_date = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return jsonify({"error": "Invalid date format"}), 400

    print(f"\n{'='*80}")
    print(f"ROUTE HANDLER - get_events API:")
    print(f"  user_id={current_user.id}")
    print(f"  start_date={start_date}")
    print(f"  end_date={end_date}")
    print(f"  include_tasks={include_tasks} (type: {type(include_tasks)})")
    print(f"  include_time_entries={include_time_entries} (type: {type(include_time_entries)})")
    print(f"{'='*80}\n")

    # Get events using the model's static method
    result = CalendarEvent.get_events_in_range(
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        include_tasks=include_tasks,
        include_time_entries=include_time_entries,
    )

    print(f"\n{'='*80}")
    print(f"ROUTE HANDLER - Result from get_events_in_range:")
    print(f"  events count: {len(result.get('events', []))}")
    print(f"  tasks count: {len(result.get('tasks', []))}")
    print(f"  time_entries count: {len(result.get('time_entries', []))}")
    print(f"{'='*80}\n")

    # Add debug marker to verify this code is running
    result["_debug_timestamp"] = datetime.now().isoformat()
    result["_debug_version"] = "v3_no_cache"

    response = jsonify(result)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@calendar_bp.route("/api/calendar/events", methods=["POST"])
@login_required
@module_enabled("calendar")
def create_event():
    """Create a new calendar event"""
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Validate required fields
    required_fields = ["title", "start", "end"]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    try:
        # Parse dates
        start_time = datetime.fromisoformat(data["start"].replace("Z", "+00:00"))
        end_time = datetime.fromisoformat(data["end"].replace("Z", "+00:00"))

        # Create event
        event = CalendarEvent(
            user_id=current_user.id,
            title=data["title"],
            start_time=start_time,
            end_time=end_time,
            description=data.get("description"),
            all_day=data.get("allDay", False),
            location=data.get("location"),
            event_type=data.get("eventType", "event"),
            project_id=data.get("projectId"),
            task_id=data.get("taskId"),
            client_id=data.get("clientId"),
            is_recurring=data.get("isRecurring", False),
            recurrence_rule=data.get("recurrenceRule"),
            recurrence_end_date=(
                datetime.fromisoformat(data["recurrenceEndDate"].replace("Z", "+00:00"))
                if data.get("recurrenceEndDate")
                else None
            ),
            reminder_minutes=data.get("reminderMinutes"),
            color=data.get("color"),
            is_private=data.get("isPrivate", False),
        )

        db.session.add(event)
        if not safe_commit():
            return jsonify({"error": "Failed to create event"}), 500

        return jsonify({"success": True, "event": event.to_dict(), "message": _("Event created successfully")}), 201

    except (ValueError, AttributeError) as e:
        return jsonify({"error": f"Invalid data: {str(e)}"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Error creating event: {str(e)}"}), 500


@calendar_bp.route("/api/calendar/events/<int:event_id>", methods=["GET"])
@login_required
@module_enabled("calendar")
def get_event(event_id):
    """Get a specific calendar event"""
    event = CalendarEvent.query.get_or_404(event_id)

    # Check if user has permission to view this event
    if event.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Permission denied"}), 403

    return jsonify(event.to_dict())


@calendar_bp.route("/api/calendar/events/<int:event_id>", methods=["PUT"])
@login_required
def update_event(event_id):
    """Update a calendar event"""
    event = CalendarEvent.query.get_or_404(event_id)

    # Check if user has permission to edit this event
    if event.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Permission denied"}), 403

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        # Update fields
        if "title" in data:
            event.title = data["title"]
        if "description" in data:
            event.description = data["description"]
        if "start" in data:
            event.start_time = datetime.fromisoformat(data["start"].replace("Z", "+00:00"))
        if "end" in data:
            event.end_time = datetime.fromisoformat(data["end"].replace("Z", "+00:00"))
        if "allDay" in data:
            event.all_day = data["allDay"]
        if "location" in data:
            event.location = data["location"]
        if "eventType" in data:
            event.event_type = data["eventType"]
        if "projectId" in data:
            event.project_id = data["projectId"]
        if "taskId" in data:
            event.task_id = data["taskId"]
        if "clientId" in data:
            event.client_id = data["clientId"]
        if "isRecurring" in data:
            event.is_recurring = data["isRecurring"]
        if "recurrenceRule" in data:
            event.recurrence_rule = data["recurrenceRule"]
        if "recurrenceEndDate" in data:
            event.recurrence_end_date = (
                datetime.fromisoformat(data["recurrenceEndDate"].replace("Z", "+00:00"))
                if data["recurrenceEndDate"]
                else None
            )
        if "reminderMinutes" in data:
            event.reminder_minutes = data["reminderMinutes"]
        if "color" in data:
            event.color = data["color"]
        if "isPrivate" in data:
            event.is_private = data["isPrivate"]

        event.updated_at = now_in_app_timezone()

        if not safe_commit():
            return jsonify({"error": "Failed to update event"}), 500

        return jsonify({"success": True, "event": event.to_dict(), "message": _("Event updated successfully")})

    except (ValueError, AttributeError) as e:
        return jsonify({"error": f"Invalid data: {str(e)}"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Error updating event: {str(e)}"}), 500


@calendar_bp.route("/api/calendar/events/<int:event_id>", methods=["DELETE", "POST"])
@login_required
def delete_event(event_id):
    """Delete a calendar event"""
    event = CalendarEvent.query.get_or_404(event_id)

    # Check if user has permission to delete this event
    if event.user_id != current_user.id and not current_user.is_admin:
        if request.method == "POST":
            flash(_("You do not have permission to delete this event."), "error")
            return redirect(url_for("calendar.view_calendar"))
        return jsonify({"error": "Permission denied"}), 403

    try:
        db.session.delete(event)
        if not safe_commit():
            if request.method == "POST":
                flash(_("Failed to delete event"), "error")
                return redirect(url_for("calendar.view_calendar"))
            return jsonify({"error": "Failed to delete event"}), 500

        if request.method == "POST":
            flash(_("Event deleted successfully"), "success")
            return redirect(url_for("calendar.view_calendar"))

        return jsonify({"success": True, "message": _("Event deleted successfully")})

    except Exception as e:
        db.session.rollback()
        if request.method == "POST":
            flash(_("Error deleting event: %(error)s", error=str(e)), "error")
            return redirect(url_for("calendar.view_calendar"))
        return jsonify({"error": f"Error deleting event: {str(e)}"}), 500


@calendar_bp.route("/api/calendar/events/<int:event_id>/move", methods=["POST"])
@login_required
def move_event(event_id):
    """Move an event to a new time (drag and drop support)"""
    event = CalendarEvent.query.get_or_404(event_id)

    # Check if user has permission to edit this event
    if event.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Permission denied"}), 403

    data = request.get_json()
    if not data or "start" not in data or "end" not in data:
        return jsonify({"error": "Start and end times are required"}), 400

    try:
        event.start_time = datetime.fromisoformat(data["start"].replace("Z", "+00:00"))
        event.end_time = datetime.fromisoformat(data["end"].replace("Z", "+00:00"))
        event.updated_at = now_in_app_timezone()

        if not safe_commit():
            return jsonify({"error": "Failed to move event"}), 500

        return jsonify({"success": True, "event": event.to_dict(), "message": _("Event moved successfully")})

    except (ValueError, AttributeError) as e:
        return jsonify({"error": f"Invalid data: {str(e)}"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Error moving event: {str(e)}"}), 500


@calendar_bp.route("/api/calendar/events/<int:event_id>/resize", methods=["POST"])
@login_required
def resize_event(event_id):
    """Resize an event (change duration)"""
    event = CalendarEvent.query.get_or_404(event_id)

    # Check if user has permission to edit this event
    if event.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Permission denied"}), 403

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        if "end" in data:
            event.end_time = datetime.fromisoformat(data["end"].replace("Z", "+00:00"))
        elif "start" in data:
            event.start_time = datetime.fromisoformat(data["start"].replace("Z", "+00:00"))

        event.updated_at = now_in_app_timezone()

        if not safe_commit():
            return jsonify({"error": "Failed to resize event"}), 500

        return jsonify({"success": True, "event": event.to_dict(), "message": _("Event resized successfully")})

    except (ValueError, AttributeError) as e:
        return jsonify({"error": f"Invalid data: {str(e)}"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Error resizing event: {str(e)}"}), 500


@calendar_bp.route("/calendar/event/<int:event_id>")
@login_required
def view_event(event_id):
    """View event details page"""
    event = CalendarEvent.query.get_or_404(event_id)

    # Check if user has permission to view this event
    if event.user_id != current_user.id and not current_user.is_admin:
        flash(_("You do not have permission to view this event."), "error")
        return redirect(url_for("calendar.view_calendar"))

    return render_template("calendar/event_detail.html", event=event)


@calendar_bp.route("/calendar/event/new")
@login_required
def new_event():
    """Create new event form"""
    projects = Project.query.filter_by(status="active").order_by(Project.name).all()
    clients = Client.query.filter_by(is_active=True).order_by(Client.name).all()
    tasks = Task.query.filter_by(assigned_to=current_user.id, status="in_progress").order_by(Task.name).all()

    # Get date from query params if provided
    date_str = request.args.get("date")
    time_str = request.args.get("time")

    initial_date = None
    initial_time = None

    if date_str:
        try:
            initial_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    if time_str:
        try:
            initial_time = datetime.strptime(time_str, "%H:%M").time()
        except ValueError:
            pass

    return render_template(
        "calendar/event_form.html",
        projects=projects,
        clients=clients,
        tasks=tasks,
        initial_date=initial_date,
        initial_time=initial_time,
    )


@calendar_bp.route("/calendar/event/<int:event_id>/edit")
@login_required
def edit_event(event_id):
    """Edit event form"""
    event = CalendarEvent.query.get_or_404(event_id)

    # Check if user has permission to edit this event
    if event.user_id != current_user.id and not current_user.is_admin:
        flash(_("You do not have permission to edit this event."), "error")
        return redirect(url_for("calendar.view_calendar"))

    projects = Project.query.filter_by(status="active").order_by(Project.name).all()
    clients = Client.query.filter_by(is_active=True).order_by(Client.name).all()
    tasks = Task.query.filter_by(assigned_to=current_user.id).order_by(Task.name).all()

    return render_template(
        "calendar/event_form.html", event=event, projects=projects, clients=clients, tasks=tasks, edit_mode=True
    )


@calendar_bp.route("/calendar/integrations")
@login_required
@module_enabled("calendar")
def list_integrations():
    """List calendar integrations - redirect to main integrations page"""
    # Redirect to main integrations page to avoid duplication
    return redirect(url_for("integrations.list_integrations"))


@calendar_bp.route("/calendar/integrations/google/connect")
@login_required
def connect_google():
    """Connect Google Calendar - redirect to main integrations"""
    return redirect(url_for("integrations.connect_integration", provider="google_calendar"))


@calendar_bp.route("/calendar/integrations/<int:integration_id>/disconnect", methods=["POST"])
@login_required
def disconnect_integration(integration_id):
    """Disconnect a calendar integration - redirect to main integrations"""
    return redirect(url_for("integrations.delete_integration", integration_id=integration_id))
