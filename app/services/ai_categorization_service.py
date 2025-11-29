"""
AI-powered categorization service for automatic project/task categorization
Uses pattern matching and heuristics (can be extended with actual AI APIs)
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from app import db
from app.models import TimeEntry, Project, Task, Client
from sqlalchemy import func
import logging
import re

logger = logging.getLogger(__name__)


class AICategorizationService:
    """Service for automatic project/task categorization"""

    # Category patterns (can be extended with ML models)
    CATEGORY_PATTERNS = {
        "development": {
            "keywords": [
                "code",
                "develop",
                "programming",
                "debug",
                "fix",
                "bug",
                "feature",
                "api",
                "backend",
                "frontend",
            ],
            "projects": ["software", "app", "website", "system"],
        },
        "design": {
            "keywords": ["design", "ui", "ux", "mockup", "wireframe", "prototype", "figma", "sketch"],
            "projects": ["design", "ui", "ux", "branding"],
        },
        "meeting": {"keywords": ["meeting", "call", "discuss", "review", "standup", "sync"], "projects": []},
        "documentation": {
            "keywords": ["document", "write", "docs", "readme", "spec", "requirements"],
            "projects": ["documentation", "wiki"],
        },
        "testing": {
            "keywords": ["test", "qa", "quality", "verify", "validate", "check"],
            "projects": ["testing", "qa"],
        },
        "support": {
            "keywords": ["support", "help", "ticket", "issue", "customer", "client"],
            "projects": ["support", "helpdesk"],
        },
        "research": {
            "keywords": ["research", "investigate", "analyze", "study", "explore"],
            "projects": ["research", "analysis"],
        },
    }

    def categorize_time_entry(self, time_entry: TimeEntry) -> Dict[str, Any]:
        """Automatically categorize a time entry"""
        categories = []

        # Analyze notes
        if time_entry.notes:
            note_categories = self._categorize_text(time_entry.notes)
            categories.extend(note_categories)

        # Analyze project name
        if time_entry.project:
            project_categories = self._categorize_text(time_entry.project.name)
            categories.extend(project_categories)

        # Analyze task name
        if time_entry.task:
            task_categories = self._categorize_text(time_entry.task.name)
            categories.extend(task_categories)

        # Get most likely category
        category_scores = {}
        for cat, score in categories:
            category_scores[cat] = category_scores.get(cat, 0) + score

        if category_scores:
            best_category = max(category_scores.items(), key=lambda x: x[1])
            return {
                "category": best_category[0],
                "confidence": min(best_category[1] / 3.0, 1.0),  # Normalize
                "all_matches": category_scores,
            }

        return {"category": "uncategorized", "confidence": 0.0, "all_matches": {}}

    def suggest_project_for_entry(self, description: str, user_id: int) -> Optional[Dict]:
        """Suggest project based on entry description"""
        description_lower = description.lower()

        # Get user's recent projects
        recent_projects = (
            Project.query.join(TimeEntry)
            .filter(TimeEntry.user_id == user_id, TimeEntry.start_time >= datetime.utcnow() - timedelta(days=90))
            .distinct()
            .all()
        )

        best_match = None
        best_score = 0

        for project in recent_projects:
            score = self._calculate_match_score(description_lower, project)
            if score > best_score:
                best_score = score
                best_match = project

        if best_match and best_score > 0.3:
            return {
                "project_id": best_match.id,
                "project_name": best_match.name,
                "confidence": min(best_score, 1.0),
                "reason": "Pattern match with project",
            }

        return None

    def suggest_task_for_entry(self, description: str, project_id: int) -> Optional[Dict]:
        """Suggest task based on entry description"""
        description_lower = description.lower()

        # Get project tasks
        tasks = Task.query.filter_by(project_id=project_id).all()

        best_match = None
        best_score = 0

        for task in tasks:
            score = self._calculate_match_score(description_lower, task)
            if score > best_score:
                best_score = score
                best_match = task

        if best_match and best_score > 0.3:
            return {
                "task_id": best_match.id,
                "task_name": best_match.name,
                "confidence": min(best_score, 1.0),
                "reason": "Pattern match with task",
            }

        return None

    def auto_categorize_batch(self, time_entries: List[TimeEntry]) -> Dict[int, Dict]:
        """Categorize multiple time entries"""
        results = {}

        for entry in time_entries:
            category = self.categorize_time_entry(entry)
            results[entry.id] = category

        return results

    def _categorize_text(self, text: str) -> List[tuple]:
        """Categorize text based on patterns"""
        if not text:
            return []

        text_lower = text.lower()
        matches = []

        for category, patterns in self.CATEGORY_PATTERNS.items():
            score = 0

            # Check keywords
            for keyword in patterns["keywords"]:
                if keyword in text_lower:
                    score += 1

            # Check project patterns
            for project_pattern in patterns["projects"]:
                if project_pattern in text_lower:
                    score += 2

            if score > 0:
                matches.append((category, score))

        return matches

    def _calculate_match_score(self, description: str, entity) -> float:
        """Calculate match score between description and entity"""
        score = 0.0
        entity_text = f"{entity.name} {getattr(entity, 'description', '')}".lower()

        # Word overlap
        desc_words = set(re.findall(r"\b\w+\b", description))
        entity_words = set(re.findall(r"\b\w+\b", entity_text))

        common_words = desc_words.intersection(entity_words)
        if desc_words:
            score = len(common_words) / len(desc_words)

        # Exact phrase match bonus
        if description in entity_text or entity.name.lower() in description:
            score += 0.3

        return min(score, 1.0)

    def learn_from_user_patterns(self, user_id: int) -> Dict[str, Any]:
        """Learn categorization patterns from user's historical data"""
        # Get user's time entries
        entries = TimeEntry.query.filter_by(user_id=user_id).limit(1000).all()

        category_distribution = {}
        project_category_map = {}

        for entry in entries:
            # Categorize entry
            category_info = self.categorize_time_entry(entry)
            category = category_info["category"]

            category_distribution[category] = category_distribution.get(category, 0) + 1

            # Map projects to categories
            if entry.project_id:
                if entry.project_id not in project_category_map:
                    project_category_map[entry.project_id] = {}
                project_category_map[entry.project_id][category] = (
                    project_category_map[entry.project_id].get(category, 0) + 1
                )

        return {
            "category_distribution": category_distribution,
            "project_categories": {
                pid: max(cats.items(), key=lambda x: x[1])[0] if cats else "uncategorized"
                for pid, cats in project_category_map.items()
            },
        }
