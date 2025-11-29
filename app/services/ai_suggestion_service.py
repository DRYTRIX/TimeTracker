"""
AI-powered time entry suggestion service
Uses pattern matching and heuristics (can be extended with actual AI APIs)
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from app import db
from app.models import TimeEntry, Project, Task, User
from sqlalchemy import func, desc
import logging

logger = logging.getLogger(__name__)


class AISuggestionService:
    """Service for AI-powered time entry suggestions"""

    def get_time_entry_suggestions(self, user_id: int, context: str = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Get AI-powered suggestions for time entries"""
        suggestions = []

        # 1. Suggest based on recent patterns
        recent_patterns = self._analyze_recent_patterns(user_id)
        suggestions.extend(recent_patterns[:limit])

        # 2. Suggest based on active tasks
        active_task_suggestions = self._suggest_from_active_tasks(user_id)
        suggestions.extend(active_task_suggestions[:limit])

        # 3. Suggest based on time of day patterns
        time_based = self._suggest_by_time_pattern(user_id)
        suggestions.extend(time_based[:limit])

        # 4. Suggest based on project deadlines
        deadline_suggestions = self._suggest_by_deadlines(user_id)
        suggestions.extend(deadline_suggestions[:limit])

        # Deduplicate and rank
        unique_suggestions = self._deduplicate_suggestions(suggestions)
        ranked = self._rank_suggestions(unique_suggestions, user_id)

        return ranked[:limit]

    def _analyze_recent_patterns(self, user_id: int) -> List[Dict]:
        """Analyze recent time entry patterns"""
        suggestions = []

        # Get recent entries (last 30 days)
        cutoff = datetime.utcnow() - timedelta(days=30)
        recent_entries = (
            TimeEntry.query.filter(
                TimeEntry.user_id == user_id, TimeEntry.start_time >= cutoff, TimeEntry.end_time.isnot(None)
            )
            .order_by(TimeEntry.start_time.desc())
            .limit(100)
            .all()
        )

        if not recent_entries:
            return suggestions

        # Find most common project/task combinations
        project_task_counts = {}
        for entry in recent_entries:
            key = (entry.project_id, entry.task_id)
            project_task_counts[key] = project_task_counts.get(key, 0) + 1

        # Suggest top patterns
        sorted_patterns = sorted(project_task_counts.items(), key=lambda x: x[1], reverse=True)

        for (project_id, task_id), count in sorted_patterns[:3]:
            project = Project.query.get(project_id)
            task = Task.query.get(task_id) if task_id else None

            if project:
                suggestions.append(
                    {
                        "type": "pattern",
                        "confidence": min(count / 10.0, 1.0),  # Normalize to 0-1
                        "project_id": project_id,
                        "project_name": project.name,
                        "task_id": task_id,
                        "task_name": task.name if task else None,
                        "reason": f"You've logged time here {count} times recently",
                        "suggested_duration": self._estimate_duration(recent_entries, project_id, task_id),
                    }
                )

        return suggestions

    def _suggest_from_active_tasks(self, user_id: int) -> List[Dict]:
        """Suggest based on active tasks"""
        suggestions = []

        # Get active tasks assigned to user
        active_tasks = (
            Task.query.filter(Task.assigned_to == user_id, Task.status.in_(["todo", "in_progress"]))
            .order_by(Task.priority.desc(), Task.created_at.desc())
            .limit(5)
            .all()
        )

        for task in active_tasks:
            # Check if already logged today
            today = datetime.utcnow().date()
            today_entry = TimeEntry.query.filter(
                TimeEntry.user_id == user_id, TimeEntry.task_id == task.id, func.date(TimeEntry.start_time) == today
            ).first()

            if not today_entry:
                suggestions.append(
                    {
                        "type": "active_task",
                        "confidence": 0.8,
                        "project_id": task.project_id,
                        "project_name": task.project.name if task.project else None,
                        "task_id": task.id,
                        "task_name": task.name,
                        "reason": f"Active task: {task.name}",
                        "priority": task.priority,
                        "suggested_duration": task.estimated_hours or 2.0,
                    }
                )

        return suggestions

    def _suggest_by_time_pattern(self, user_id: int) -> List[Dict]:
        """Suggest based on time-of-day patterns"""
        suggestions = []
        current_hour = datetime.utcnow().hour

        # Get entries by hour of day
        recent_entries = TimeEntry.query.filter(
            TimeEntry.user_id == user_id,
            TimeEntry.start_time >= datetime.utcnow() - timedelta(days=30),
            TimeEntry.end_time.isnot(None),
        ).all()

        if not recent_entries:
            return suggestions

        # Find most common project for this hour
        hour_entries = [e for e in recent_entries if e.start_time.hour == current_hour]

        if hour_entries:
            project_counts = {}
            for entry in hour_entries:
                project_counts[entry.project_id] = project_counts.get(entry.project_id, 0) + 1

            if project_counts:
                most_common_project_id = max(project_counts.items(), key=lambda x: x[1])[0]
                project = Project.query.get(most_common_project_id)

                if project:
                    suggestions.append(
                        {
                            "type": "time_pattern",
                            "confidence": 0.6,
                            "project_id": project.id,
                            "project_name": project.name,
                            "task_id": None,
                            "reason": f"You usually work on {project.name} around this time",
                            "suggested_duration": 2.0,
                        }
                    )

        return suggestions

    def _suggest_by_deadlines(self, user_id: int) -> List[Dict]:
        """Suggest based on upcoming deadlines"""
        suggestions = []

        # Get tasks with upcoming deadlines
        upcoming_deadline = datetime.utcnow() + timedelta(days=7)
        urgent_tasks = (
            Task.query.filter(
                Task.assigned_to == user_id,
                Task.status.in_(["todo", "in_progress"]),
                Task.due_date.isnot(None),
                Task.due_date <= upcoming_deadline,
            )
            .order_by(Task.due_date.asc())
            .limit(3)
            .all()
        )

        for task in urgent_tasks:
            days_until_deadline = (task.due_date.date() - datetime.utcnow().date()).days

            suggestions.append(
                {
                    "type": "deadline",
                    "confidence": 0.9 if days_until_deadline <= 2 else 0.7,
                    "project_id": task.project_id,
                    "project_name": task.project.name if task.project else None,
                    "task_id": task.id,
                    "task_name": task.name,
                    "reason": f"Deadline in {days_until_deadline} days",
                    "urgency": "high" if days_until_deadline <= 2 else "medium",
                    "suggested_duration": task.estimated_hours or 4.0,
                }
            )

        return suggestions

    def _estimate_duration(self, entries: List[TimeEntry], project_id: int, task_id: int = None) -> float:
        """Estimate duration based on historical data"""
        relevant_entries = [
            e for e in entries if e.project_id == project_id and (task_id is None or e.task_id == task_id)
        ]

        if not relevant_entries:
            return 2.0  # Default

        durations = [e.duration_hours for e in relevant_entries if e.duration_hours]
        if durations:
            return sum(durations) / len(durations)  # Average

        return 2.0

    def _deduplicate_suggestions(self, suggestions: List[Dict]) -> List[Dict]:
        """Remove duplicate suggestions"""
        seen = set()
        unique = []

        for suggestion in suggestions:
            key = (suggestion.get("project_id"), suggestion.get("task_id"))
            if key not in seen:
                seen.add(key)
                unique.append(suggestion)

        return unique

    def _rank_suggestions(self, suggestions: List[Dict], user_id: int) -> List[Dict]:
        """Rank suggestions by relevance"""
        # Sort by confidence, then by type priority
        type_priority = {"deadline": 4, "active_task": 3, "pattern": 2, "time_pattern": 1}

        def rank_key(s):
            return (
                s.get("confidence", 0),
                type_priority.get(s.get("type", ""), 0),
                s.get("urgency") == "high" if s.get("urgency") else False,
            )

        return sorted(suggestions, key=rank_key, reverse=True)

    def get_project_suggestion(self, description: str, user_id: int) -> Optional[Dict]:
        """Suggest project based on description/text"""
        # Simple keyword matching (can be enhanced with NLP)
        description_lower = description.lower()

        # Get user's projects
        user_projects = Project.query.join(TimeEntry).filter(TimeEntry.user_id == user_id).distinct().all()

        # Match keywords
        best_match = None
        best_score = 0

        for project in user_projects:
            score = 0
            project_name_lower = project.name.lower()
            project_desc_lower = (project.description or "").lower()

            # Check for keyword matches
            words = description_lower.split()
            for word in words:
                if len(word) > 3:  # Ignore short words
                    if word in project_name_lower:
                        score += 2
                    if word in project_desc_lower:
                        score += 1

            if score > best_score:
                best_score = score
                best_match = project

        if best_match and best_score > 0:
            return {
                "project_id": best_match.id,
                "project_name": best_match.name,
                "confidence": min(best_score / 5.0, 1.0),
                "reason": "Keyword match with project name/description",
            }

        return None
