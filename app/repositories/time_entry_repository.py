"""
Repository for time entry data access operations.
"""

from typing import List, Optional
from datetime import datetime
from sqlalchemy import and_, or_
from sqlalchemy.orm import joinedload
from app import db
from app.models import TimeEntry, User, Project, Task
from app.repositories.base_repository import BaseRepository
from app.constants import TimeEntrySource, TimeEntryStatus


class TimeEntryRepository(BaseRepository[TimeEntry]):
    """Repository for time entry operations"""

    def __init__(self):
        super().__init__(TimeEntry)

    def get_active_timer(self, user_id: int) -> Optional[TimeEntry]:
        """Get the active timer for a user"""
        return self.model.query.filter_by(user_id=user_id, end_time=None).first()

    def get_by_user(
        self, user_id: int, limit: Optional[int] = None, offset: int = 0, include_relations: bool = False
    ) -> List[TimeEntry]:
        """Get time entries for a user with optional relations"""
        query = self.model.query.filter_by(user_id=user_id)

        if include_relations:
            query = query.options(
                joinedload(TimeEntry.project),
                joinedload(TimeEntry.client),
                joinedload(TimeEntry.task),
                joinedload(TimeEntry.user),
            )

        query = query.order_by(TimeEntry.start_time.desc())

        if limit:
            query = query.limit(limit).offset(offset)

        return query.all()

    def get_by_project(
        self, project_id: int, limit: Optional[int] = None, offset: int = 0, include_relations: bool = False
    ) -> List[TimeEntry]:
        """Get time entries for a project"""
        query = self.model.query.filter_by(project_id=project_id)

        if include_relations:
            query = query.options(
                joinedload(TimeEntry.user),
                joinedload(TimeEntry.project),
                joinedload(TimeEntry.client),
                joinedload(TimeEntry.task),
            )

        query = query.order_by(TimeEntry.start_time.desc())

        if limit:
            query = query.limit(limit).offset(offset)

        return query.all()

    def get_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        user_id: Optional[int] = None,
        project_id: Optional[int] = None,
        client_id: Optional[int] = None,
        include_relations: bool = False,
    ) -> List[TimeEntry]:
        """Get time entries within a date range"""
        query = self.model.query.filter(and_(TimeEntry.start_time >= start_date, TimeEntry.start_time <= end_date))

        if user_id:
            query = query.filter_by(user_id=user_id)

        if project_id:
            query = query.filter_by(project_id=project_id)

        if client_id:
            query = query.filter_by(client_id=client_id)

        if include_relations:
            query = query.options(
                joinedload(TimeEntry.user),
                joinedload(TimeEntry.project),
                joinedload(TimeEntry.client),
                joinedload(TimeEntry.task),
            )

        return query.order_by(TimeEntry.start_time.desc()).all()

    def get_billable_entries(
        self,
        user_id: Optional[int] = None,
        project_id: Optional[int] = None,
        client_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[TimeEntry]:
        """Get billable time entries with optional filters"""
        query = self.model.query.filter_by(billable=True)

        if user_id:
            query = query.filter_by(user_id=user_id)

        if project_id:
            query = query.filter_by(project_id=project_id)

        if client_id:
            query = query.filter_by(client_id=client_id)

        if start_date:
            query = query.filter(TimeEntry.start_time >= start_date)

        if end_date:
            query = query.filter(TimeEntry.start_time <= end_date)

        return query.order_by(TimeEntry.start_time.desc()).all()

    def stop_timer(self, entry_id: int, end_time: datetime) -> Optional[TimeEntry]:
        """Stop an active timer"""
        entry = self.get_by_id(entry_id)
        if entry and entry.end_time is None:
            entry.end_time = end_time
            entry.calculate_duration()
            return entry
        return None

    def create_timer(
        self,
        user_id: int,
        project_id: Optional[int] = None,
        client_id: Optional[int] = None,
        task_id: Optional[int] = None,
        notes: Optional[str] = None,
        source: str = TimeEntrySource.AUTO.value,
    ) -> TimeEntry:
        """Create a new timer (active time entry)"""
        from app.models.time_entry import local_now

        entry = self.model(
            user_id=user_id,
            project_id=project_id,
            client_id=client_id,
            task_id=task_id,
            start_time=local_now(),
            notes=notes,
            source=source,
        )
        db.session.add(entry)
        return entry

    def create_manual_entry(
        self,
        user_id: int,
        project_id: Optional[int] = None,
        client_id: Optional[int] = None,
        start_time: datetime = None,
        end_time: datetime = None,
        task_id: Optional[int] = None,
        notes: Optional[str] = None,
        tags: Optional[str] = None,
        billable: bool = True,
        paid: bool = False,
        invoice_number: Optional[str] = None,
    ) -> TimeEntry:
        """Create a manual time entry"""
        entry = self.model(
            user_id=user_id,
            project_id=project_id,
            client_id=client_id,
            task_id=task_id,
            start_time=start_time,
            end_time=end_time,
            notes=notes,
            tags=tags,
            billable=billable,
            paid=paid,
            invoice_number=invoice_number,
            source=TimeEntrySource.MANUAL.value,
        )
        entry.calculate_duration()
        db.session.add(entry)
        return entry

    def get_total_duration(
        self,
        user_id: Optional[int] = None,
        project_id: Optional[int] = None,
        client_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        billable_only: bool = False,
    ) -> int:
        """Get total duration in seconds for matching entries"""
        from sqlalchemy import func

        query = db.session.query(func.sum(TimeEntry.duration_seconds))

        if user_id:
            query = query.filter_by(user_id=user_id)

        if project_id:
            query = query.filter_by(project_id=project_id)

        if client_id:
            query = query.filter_by(client_id=client_id)

        if start_date:
            query = query.filter(TimeEntry.start_time >= start_date)

        if end_date:
            query = query.filter(TimeEntry.start_time <= end_date)

        if billable_only:
            query = query.filter_by(billable=True)

        result = query.scalar()
        return int(result) if result else 0
