"""
Gamification Service for badges and leaderboards
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta, date
from app import db
from app.models.gamification import Badge, UserBadge, Leaderboard, LeaderboardEntry
from app.models import TimeEntry, Task, Project, User
from sqlalchemy import func, and_, desc
import logging

logger = logging.getLogger(__name__)


class GamificationService:
    """Service for managing badges and leaderboards"""

    def check_and_award_badges(self, user_id: int, event_type: str, event_data: Dict = None) -> List[Dict]:
        """Check if user qualifies for any badges and award them"""
        awarded = []
        
        # Get all active badges
        badges = Badge.query.filter_by(is_active=True).all()

        for badge in badges:
            # Check if user already has this badge
            existing = UserBadge.query.filter_by(user_id=user_id, badge_id=badge.id).first()
            if existing:
                continue

            # Check criteria
            if self._check_badge_criteria(user_id, badge, event_type, event_data or {}):
                # Award badge
                user_badge = UserBadge(
                    user_id=user_id,
                    badge_id=badge.id,
                    progress=100
                )
                db.session.add(user_badge)
                awarded.append(badge.to_dict())

        if awarded:
            db.session.commit()
            logger.info(f"Awarded {len(awarded)} badges to user {user_id}")

        return awarded

    def _check_badge_criteria(self, user_id: int, badge: Badge, event_type: str, event_data: Dict) -> bool:
        """Check if badge criteria are met"""
        criteria = badge.criteria or {}
        badge_type = criteria.get("type")

        if badge_type == "time_tracked":
            total_hours = self._get_total_hours(user_id, criteria)
            target = criteria.get("target_hours", 0)
            return total_hours >= target

        elif badge_type == "tasks_completed":
            count = self._get_completed_tasks(user_id, criteria)
            target = criteria.get("target_count", 0)
            return count >= target

        elif badge_type == "streak":
            streak = self._get_streak(user_id, criteria)
            target = criteria.get("target_days", 0)
            return streak >= target

        elif badge_type == "projects_completed":
            count = self._get_completed_projects(user_id, criteria)
            target = criteria.get("target_count", 0)
            return count >= target

        elif badge_type == "milestone":
            # Check specific milestone
            milestone_type = criteria.get("milestone_type")
            if milestone_type == "first_time_entry":
                return event_type == "time_entry_created"
            elif milestone_type == "first_task":
                return event_type == "task_completed"
            elif milestone_type == "first_project":
                return event_type == "project_created"

        return False

    def _get_total_hours(self, user_id: int, criteria: Dict) -> float:
        """Get total hours tracked for user"""
        query = TimeEntry.query.filter_by(
            user_id=user_id,
            billable=True
        ).filter(TimeEntry.end_time.isnot(None))

        if criteria.get("date_from"):
            query = query.filter(TimeEntry.start_time >= criteria["date_from"])
        if criteria.get("date_to"):
            query = query.filter(TimeEntry.start_time <= criteria["date_to"])

        entries = query.all()
        return sum(e.duration_hours for e in entries)

    def _get_completed_tasks(self, user_id: int, criteria: Dict) -> int:
        """Get completed tasks count"""
        query = Task.query.join(TimeEntry).filter(
            Task.status == "completed",
            TimeEntry.user_id == user_id
        )

        if criteria.get("date_from"):
            query = query.filter(Task.updated_at >= criteria["date_from"])

        return query.count()

    def _get_streak(self, user_id: int, criteria: Dict) -> int:
        """Get current streak of days with time entries"""
        today = date.today()
        streak = 0

        for i in range(365):  # Check up to 1 year
            check_date = today - timedelta(days=i)
            has_entry = TimeEntry.query.filter(
                TimeEntry.user_id == user_id,
                func.date(TimeEntry.start_time) == check_date
            ).first()

            if has_entry:
                streak += 1
            else:
                break

        return streak

    def _get_completed_projects(self, user_id: int, criteria: Dict) -> int:
        """Get completed projects count"""
        query = Project.query.filter_by(status="completed")

        if criteria.get("user_id") == user_id:
            # Projects where user is owner or has entries
            query = query.join(TimeEntry).filter(TimeEntry.user_id == user_id)

        return query.count()

    def get_user_badges(self, user_id: int) -> List[Dict]:
        """Get all badges earned by user"""
        user_badges = UserBadge.query.filter_by(user_id=user_id).order_by(
            UserBadge.earned_at.desc()
        ).all()

        return [ub.to_dict() for ub in user_badges]

    def get_user_points(self, user_id: int) -> int:
        """Get total points for user from badges"""
        user_badges = UserBadge.query.join(Badge).filter(
            UserBadge.user_id == user_id
        ).all()

        return sum(ub.badge.points for ub in user_badges)

    def calculate_leaderboard(self, leaderboard_id: int, period_start: datetime = None, period_end: datetime = None) -> List[Dict]:
        """Calculate and update leaderboard rankings"""
        leaderboard = Leaderboard.query.get_or_404(leaderboard_id)

        if not period_start or not period_end:
            period_start, period_end = self._get_period_dates(leaderboard.period)

        # Calculate scores based on type
        scores = self._calculate_scores(leaderboard, period_start, period_end)

        # Rank users
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        # Clear old entries for this period
        LeaderboardEntry.query.filter_by(
            leaderboard_id=leaderboard_id
        ).filter(
            LeaderboardEntry.period_start == period_start
        ).delete()

        # Create new entries
        entries = []
        for rank, (user_id, score) in enumerate(sorted_scores, start=1):
            entry = LeaderboardEntry(
                leaderboard_id=leaderboard_id,
                user_id=user_id,
                rank=rank,
                score=score,
                period_start=period_start,
                period_end=period_end
            )
            db.session.add(entry)
            entries.append(entry)

        db.session.commit()

        return [e.to_dict() for e in entries[:100]]  # Top 100

    def _get_period_dates(self, period: str) -> tuple:
        """Get period start and end dates"""
        today = datetime.now().date()
        
        if period == "daily":
            start = datetime.combine(today, datetime.min.time())
            end = datetime.combine(today, datetime.max.time())
        elif period == "weekly":
            days_since_monday = today.weekday()
            start = datetime.combine(today - timedelta(days=days_since_monday), datetime.min.time())
            end = datetime.combine(start + timedelta(days=6), datetime.max.time())
        elif period == "monthly":
            start = datetime(today.year, today.month, 1)
            if today.month == 12:
                end = datetime(today.year + 1, 1, 1) - timedelta(seconds=1)
            else:
                end = datetime(today.year, today.month + 1, 1) - timedelta(seconds=1)
        else:  # all_time
            start = datetime(2000, 1, 1)
            end = datetime.now()

        return start, end

    def _calculate_scores(self, leaderboard: Leaderboard, start: datetime, end: datetime) -> Dict[int, float]:
        """Calculate scores for leaderboard"""
        scores = {}
        leaderboard_type = leaderboard.leaderboard_type

        if leaderboard_type == "time_tracked":
            # Total hours tracked
            query = db.session.query(
                TimeEntry.user_id,
                func.sum(TimeEntry.duration_seconds).label("total_seconds")
            ).filter(
                TimeEntry.start_time >= start,
                TimeEntry.start_time <= end,
                TimeEntry.end_time.isnot(None)
            ).group_by(TimeEntry.user_id)

            for user_id, total_seconds in query.all():
                scores[user_id] = (total_seconds or 0) / 3600  # Convert to hours

        elif leaderboard_type == "tasks_completed":
            # Tasks completed
            query = db.session.query(
                Task.assigned_to.label("user_id"),
                func.count(Task.id).label("count")
            ).filter(
                Task.status == "completed",
                Task.updated_at >= start,
                Task.updated_at <= end
            ).group_by(Task.assigned_to)

            for user_id, count in query.all():
                if user_id:
                    scores[user_id] = count or 0

        elif leaderboard_type == "points":
            # Badge points
            query = db.session.query(
                UserBadge.user_id,
                func.sum(Badge.points).label("total_points")
            ).join(Badge).filter(
                UserBadge.earned_at >= start,
                UserBadge.earned_at <= end
            ).group_by(UserBadge.user_id)

            for user_id, total_points in query.all():
                scores[user_id] = total_points or 0

        return scores

    def get_leaderboard(self, leaderboard_id: int, limit: int = 100) -> List[Dict]:
        """Get current leaderboard rankings"""
        leaderboard = Leaderboard.query.get_or_404(leaderboard_id)
        period_start, period_end = self._get_period_dates(leaderboard.period)

        entries = LeaderboardEntry.query.filter_by(
            leaderboard_id=leaderboard_id
        ).filter(
            LeaderboardEntry.period_start == period_start
        ).order_by(LeaderboardEntry.rank.asc()).limit(limit).all()

        return [e.to_dict() for e in entries]

