from datetime import datetime
from app import db
from app.utils.timezone import now_in_app_timezone


def _isoformat_calendar(dt):
    """Return YYYY-MM-DDTHH:mm:ss for calendar API (no microseconds)."""
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


class CalendarEvent(db.Model):
    """Calendar event model for scheduling meetings, appointments, and other events"""

    __tablename__ = "calendar_events"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    start_time = db.Column(db.DateTime, nullable=False, index=True)
    end_time = db.Column(db.DateTime, nullable=False, index=True)
    all_day = db.Column(db.Boolean, default=False, nullable=False)
    location = db.Column(db.String(200), nullable=True)

    # Event type: meeting, appointment, reminder, deadline, or custom
    event_type = db.Column(db.String(50), default="event", nullable=False, index=True)

    # Optional associations
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=True, index=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=True, index=True)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=True, index=True)

    # Recurring event support
    is_recurring = db.Column(db.Boolean, default=False, nullable=False)
    recurrence_rule = db.Column(db.String(200), nullable=True)  # RRULE format (e.g., "FREQ=WEEKLY;BYDAY=MO,WE,FR")
    recurrence_end_date = db.Column(db.DateTime, nullable=True)
    parent_event_id = db.Column(db.Integer, db.ForeignKey("calendar_events.id"), nullable=True, index=True)

    # Reminders
    reminder_minutes = db.Column(db.Integer, nullable=True)  # Minutes before event to remind

    # Color coding
    color = db.Column(db.String(7), nullable=True)  # Hex color code (e.g., #FF5733)

    # Privacy
    is_private = db.Column(db.Boolean, default=False, nullable=False)

    created_at = db.Column(db.DateTime, default=now_in_app_timezone, nullable=False)
    updated_at = db.Column(db.DateTime, default=now_in_app_timezone, onupdate=now_in_app_timezone, nullable=False)

    # Relationships
    user = db.relationship("User", backref=db.backref("calendar_events", lazy="dynamic", cascade="all, delete-orphan"))
    project = db.relationship("Project", backref=db.backref("calendar_events", lazy="dynamic"))
    task = db.relationship("Task", backref=db.backref("calendar_events", lazy="dynamic"))
    client = db.relationship("Client", backref=db.backref("calendar_events", lazy="dynamic"))

    # For recurring events - parent/child relationship
    child_events = db.relationship(
        "CalendarEvent",
        backref=db.backref("parent_event", remote_side=[id]),
        foreign_keys=[parent_event_id],
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def __init__(self, user_id, title, start_time, end_time, **kwargs):
        """Initialize a CalendarEvent instance.

        Args:
            user_id: ID of the user who created this event
            title: Title of the event
            start_time: Start datetime of the event
            end_time: End datetime of the event
            **kwargs: Additional optional fields
        """
        self.user_id = user_id
        self.title = title
        self.start_time = start_time
        self.end_time = end_time

        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def __repr__(self):
        return f"<CalendarEvent {self.title} ({self.start_time})>"

    def to_dict(self):
        """Convert event to dictionary for API responses"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "start": self.start_time.isoformat() if self.start_time else None,
            "end": self.end_time.isoformat() if self.end_time else None,
            "allDay": self.all_day,
            "location": self.location,
            "eventType": self.event_type,
            "projectId": self.project_id,
            "taskId": self.task_id,
            "clientId": self.client_id,
            "isRecurring": self.is_recurring,
            "recurrenceRule": self.recurrence_rule,
            "recurrenceEndDate": self.recurrence_end_date.isoformat() if self.recurrence_end_date else None,
            "parentEventId": self.parent_event_id,
            "reminderMinutes": self.reminder_minutes,
            "color": self.color,
            "isPrivate": self.is_private,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }

    def duration_hours(self):
        """Calculate duration of event in hours"""
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            return delta.total_seconds() / 3600
        return 0

    @staticmethod
    def get_events_in_range(user_id, start_date, end_date, include_tasks=False, include_time_entries=False):
        """Get all events for a user within a date range.

        Args:
            user_id: ID of the user
            start_date: Start of date range
            end_date: End of date range
            include_tasks: Whether to include tasks with due dates
            include_time_entries: Whether to include time entries

        Returns:
            Dictionary with events, tasks, and time entries
        """
        from app.models import Task, TimeEntry
        import logging

        logger = logging.getLogger(__name__)

        print(f"\n{'*'*80}")
        print(f"MODEL - get_events_in_range called:")
        print(f"  user_id={user_id}")
        print(f"  start={start_date}")
        print(f"  end={end_date}")
        print(f"  include_tasks={include_tasks} (type: {type(include_tasks)})")
        print(f"  include_time_entries={include_time_entries} (type: {type(include_time_entries)})")
        print(f"{'*'*80}\n")

        logger.info(
            f"get_events_in_range called: user_id={user_id}, start={start_date}, end={end_date}, include_tasks={include_tasks}, include_time_entries={include_time_entries}"
        )

        result = {"events": [], "tasks": [], "time_entries": []}

        # Get calendar events
        events = (
            CalendarEvent.query.filter(
                CalendarEvent.user_id == user_id,
                CalendarEvent.start_time >= start_date,
                CalendarEvent.start_time <= end_date,
            )
            .order_by(CalendarEvent.start_time)
            .all()
        )

        logger.info(f"Found {len(events)} calendar events")
        print(f"MODEL - Found {len(events)} calendar events")
        result["events"] = [event.to_dict() for event in events]

        # Optionally include tasks with due dates
        if include_tasks:
            print(f"MODEL - Querying tasks for user {user_id}")
            logger.info(f"Querying tasks for user {user_id}")
            tasks = Task.query.filter(
                Task.assigned_to == user_id,
                Task.due_date.isnot(None),
                Task.due_date >= start_date.date() if hasattr(start_date, "date") else start_date,
                Task.due_date <= end_date.date() if hasattr(end_date, "date") else end_date,
                Task.status.in_(["todo", "in_progress", "review"]),
            ).all()

            print(f"MODEL - Found {len(tasks)} tasks with due dates")
            logger.info(f"Found {len(tasks)} tasks with due dates")

            result["tasks"] = [
                {
                    "id": task.id,
                    "title": task.name,
                    "description": task.description,
                    "dueDate": task.due_date.isoformat() if task.due_date else None,
                    "status": task.status,
                    "priority": task.priority,
                    "projectId": task.project_id,
                    "type": "task",
                }
                for task in tasks
            ]
        else:
            print(f"MODEL - Not including tasks (include_tasks=False)")
            logger.info("Not including tasks (include_tasks=False)")

        # Optionally include time entries
        if include_time_entries:
            print(f"MODEL - Querying time entries for user {user_id}")
            logger.info(f"Querying time entries for user {user_id}")
            time_entries = (
                TimeEntry.query.filter(
                    TimeEntry.user_id == user_id,
                    TimeEntry.start_time >= start_date,
                    TimeEntry.start_time <= end_date,
                    TimeEntry.end_time.isnot(None),  # Only include completed entries (CalDAV entries have end_time)
                )
                .order_by(TimeEntry.start_time)
                .all()
            )

            print(f"MODEL - Found {len(time_entries)} time entries")
            logger.info(f"Found {len(time_entries)} time entries")

            result["time_entries"] = [
                {
                    "id": entry.id,
                    "title": f"Time: {entry.project.name if entry.project else 'Unknown'}",
                    "start": _isoformat_calendar(entry.start_time),
                    "end": _isoformat_calendar(entry.end_time),
                    "projectId": entry.project_id,
                    "taskId": entry.task_id,
                    "notes": entry.notes,
                    "type": "time_entry",
                    "source": entry.source,  # Include source to identify CalDAV entries (source="auto")
                }
                for entry in time_entries
                if entry.start_time and entry.end_time  # Ensure both times are set for proper display
            ]
        else:
            print(f"MODEL - Not including time entries (include_time_entries=False)")
            logger.info("Not including time entries (include_time_entries=False)")

        print(f"\n{'*'*80}")
        print(f"MODEL - Returning:")
        print(f"  events: {len(result['events'])}")
        print(f"  tasks: {len(result['tasks'])}")
        print(f"  time_entries: {len(result['time_entries'])}")
        print(f"{'*'*80}\n")

        logger.info(
            f"Returning: {len(result['events'])} events, {len(result['tasks'])} tasks, {len(result['time_entries'])} time_entries"
        )
        return result
