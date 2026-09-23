"""Server-side AI helper service.

Provider keys stay in Flask settings and are never exposed to browsers or desktop clients.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests
from sqlalchemy.orm import joinedload

from app import db
from app.models import Project, Settings, Task, TimeEntry, User
from app.models.time_entry import local_now
from app.services.ai_suggestion_service import AISuggestionService
from app.services.time_tracking_service import TimeTrackingService
from app.utils.scope_filter import user_can_access_project

logger = logging.getLogger(__name__)

# Named provider presets. base_url is the host root; chat_path is appended for completions.
PROVIDER_PRESETS: Dict[str, Dict[str, Any]] = {
    "ollama": {
        "base_url": "http://127.0.0.1:11434",
        "requires_key": False,
        "default_model": "llama3.1",
        "suggested_models": ["llama3.1", "llama3.2", "mistral", "qwen2.5"],
        "chat_path": "/v1/chat/completions",
    },
    "openai": {
        "base_url": "https://api.openai.com",
        "requires_key": True,
        "default_model": "gpt-4o-mini",
        "suggested_models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
        "chat_path": "/v1/chat/completions",
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com",
        "requires_key": True,
        "default_model": "claude-sonnet-4-5",
        "suggested_models": ["claude-opus-4-5", "claude-sonnet-4-5"],
        "chat_path": "/v1/chat/completions",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "requires_key": True,
        "default_model": "gemini-2.0-flash",
        "suggested_models": ["gemini-2.0-flash", "gemini-1.5-pro"],
        "chat_path": "/chat/completions",
    },
    "orcarouter": {
        "base_url": "https://api.orcarouter.ai",
        "requires_key": True,
        "default_model": "auto",
        "suggested_models": ["auto"],
        "chat_path": "/v1/chat/completions",
    },
    "openai_compatible": {
        "base_url": "",
        "requires_key": True,
        "default_model": "",
        "suggested_models": [],
        "chat_path": "/v1/chat/completions",
    },
    "custom": {
        "base_url": "",
        "requires_key": True,
        "default_model": "",
        "suggested_models": [],
        "chat_path": "/v1/chat/completions",
    },
}

NAMED_PROVIDERS = set(PROVIDER_PRESETS.keys())
HOSTED_PROVIDERS = {name for name, preset in PROVIDER_PRESETS.items() if preset.get("requires_key")}
ROUTING_STRATEGIES = {"cost", "quality", "balanced"}


class AIServiceError(Exception):
    """User-facing AI service error with a stable code."""

    def __init__(self, message: str, code: str = "ai_error", status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


@dataclass
class AIProviderConfig:
    enabled: bool
    provider: str
    base_url: str
    model: str
    api_key: str
    api_key_set: bool
    timeout_seconds: int
    context_limit: int
    system_prompt: str
    routing_strategy: str = ""

    @classmethod
    def from_settings(cls) -> "AIProviderConfig":
        # Runtime use: include decrypted API key if configured.
        config = Settings.get_settings().get_ai_config(include_secrets=True)
        known = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in config.items() if k in known})

    def public_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "provider": self.provider,
            "base_url": self.base_url,
            "model": self.model,
            "api_key_set": self.api_key_set,
            "timeout_seconds": self.timeout_seconds,
            "context_limit": self.context_limit,
            "routing_strategy": self.routing_strategy or None,
        }

    def chat_completions_url(self) -> str:
        preset = PROVIDER_PRESETS.get(self.provider) or PROVIDER_PRESETS["openai_compatible"]
        path = preset.get("chat_path") or "/v1/chat/completions"
        base = (self.base_url or "").rstrip("/")
        if not base:
            raise AIServiceError("AI helper is not fully configured.", "ai_not_configured", 400)
        # Avoid doubling /v1 when the stored base URL already includes it.
        if path.startswith("/v1/") and base.endswith("/v1"):
            path = path[len("/v1") :]
        return f"{base}{path}"


class LLMService:
    """Provider-neutral service for AI chat, context building, and confirmed actions."""

    def __init__(self, config: Optional[AIProviderConfig] = None):
        self.config = config or AIProviderConfig.from_settings()

    def is_enabled(self) -> bool:
        """True when the AI helper feature flag is on (may still be misconfigured for LLM calls)."""
        return bool(self.config.enabled)

    def ensure_enabled(self) -> None:
        if not self.config.enabled:
            raise AIServiceError("AI helper is disabled.", "ai_disabled", 503)
        if not self.config.base_url or not self.config.model:
            raise AIServiceError("AI helper is not fully configured.", "ai_not_configured", 400)
        provider = self.config.provider
        if provider in HOSTED_PROVIDERS and not self.config.api_key:
            raise AIServiceError("Hosted AI provider requires an API key.", "ai_missing_api_key", 400)

    def test_connection(self) -> Dict[str, Any]:
        self.ensure_enabled()
        response = self._chat_completion(
            [
                {"role": "system", "content": "Reply with a short confirmation only."},
                {"role": "user", "content": "Say TimeTracker AI helper is connected."},
            ],
            max_tokens=40,
        )
        return {"ok": True, "reply": response.get("content", "").strip(), "provider": self.config.public_dict()}

    def build_context(self, user: User, limit: Optional[int] = None) -> Dict[str, Any]:
        limit = max(5, min(int(limit or self.config.context_limit or 40), 100))
        recent_entries = (
            TimeEntry.query.options(joinedload(TimeEntry.project), joinedload(TimeEntry.task))
            .filter(TimeEntry.user_id == user.id)
            .order_by(TimeEntry.start_time.desc())
            .limit(limit)
            .all()
        )
        active_timer = next((entry for entry in recent_entries if entry.end_time is None), None)
        if active_timer is None:
            active_timer = (
                TimeEntry.query.options(joinedload(TimeEntry.project), joinedload(TimeEntry.task))
                .filter_by(user_id=user.id, end_time=None)
                .first()
            )

        tasks = (
            Task.query.options(joinedload(Task.project))
            .filter(Task.assigned_to == user.id, Task.status.in_(["todo", "in_progress", "review"]))
            .order_by(Task.due_date.asc().nullslast(), Task.updated_at.desc())
            .limit(20)
            .all()
        )
        project_ids = {entry.project_id for entry in recent_entries if entry.project_id}
        project_ids.update(task.project_id for task in tasks if task.project_id)
        projects = []
        if project_ids:
            projects = Project.query.filter(Project.id.in_(project_ids)).limit(30).all()

        deterministic_suggestions = AISuggestionService().get_time_entry_suggestions(user.id, limit=5)
        total_seconds = sum(entry.duration_seconds or 0 for entry in recent_entries if entry.end_time is not None)
        context = {
            "user": {"id": user.id, "username": user.username, "is_admin": bool(user.is_admin)},
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {
                "recent_entry_count": len(recent_entries),
                "recent_total_hours": round(total_seconds / 3600, 2),
                "open_task_count": len(tasks),
            },
            "active_timer": self._entry_dict(active_timer) if active_timer else None,
            "recent_entries": [self._entry_dict(entry) for entry in recent_entries],
            "assigned_tasks": [self._task_dict(task) for task in tasks],
            "projects": [self._project_dict(project) for project in projects],
            "deterministic_suggestions": deterministic_suggestions,
        }
        return context

    def chat(self, user: User, prompt: str, history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        self.ensure_enabled()
        prompt = (prompt or "").strip()
        if not prompt:
            raise AIServiceError("Prompt is required.", "validation_error", 400)

        context = self.build_context(user)
        messages = self._build_messages(prompt, context, history or [])
        provider_response = self._chat_completion(messages)
        content = provider_response.get("content", "").strip()
        actions = self._extract_actions(content)
        return {
            "reply": content,
            "actions": actions,
            "context_preview": self.context_preview_from_context(context),
            "provider": self.config.public_dict(),
        }

    def context_preview(self, user: User) -> Dict[str, Any]:
        return self.context_preview_from_context(self.build_context(user))

    def summarize_time_entries(
        self,
        user: User,
        date_range: Dict[str, Any],
        *,
        target_user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Summarize completed time entries for a user over a date range using the configured LLM."""
        self.ensure_enabled()

        subject = user
        if target_user_id is not None and target_user_id != user.id:
            if not user.is_admin:
                raise AIServiceError("You cannot summarize another user's entries.", "forbidden", 403)
            subject = User.query.get(target_user_id)
            if not subject:
                raise AIServiceError("User not found.", "not_found", 404)

        start_dt, end_dt = self._parse_date_range(date_range)
        entries = (
            TimeEntry.query.options(joinedload(TimeEntry.project), joinedload(TimeEntry.task))
            .filter(
                TimeEntry.user_id == subject.id,
                TimeEntry.end_time.isnot(None),
                TimeEntry.start_time >= start_dt,
                TimeEntry.start_time <= end_dt,
            )
            .order_by(TimeEntry.start_time.asc())
            .limit(500)
            .all()
        )

        total_seconds = sum(entry.duration_seconds or 0 for entry in entries)
        compact_lines = []
        for entry in entries:
            project_name = entry.project.name if entry.project else "—"
            task_name = entry.task.name if entry.task else ""
            label = f"{project_name}" + (f" / {task_name}" if task_name else "")
            hours = round((entry.duration_seconds or 0) / 3600, 2)
            note = (entry.notes or "").strip()
            compact_lines.append(
                f"- {entry.start_time.date().isoformat()}: {label}, {hours}h"
                + (f" — {note[:120]}" if note else "")
            )

        entries_text = "\n".join(compact_lines) if compact_lines else "(no completed entries in range)"
        prompt = (
            f"Summarize this user's tracked work from {start_dt.date().isoformat()} "
            f"to {end_dt.date().isoformat()} for a weekly status report. "
            "Group by project, note totals, and call out anything billable or notable. "
            "Use concise bullet points.\n\n"
            f"User: {subject.username}\n"
            f"Entry count: {len(entries)}\n"
            f"Total hours: {round(total_seconds / 3600, 2)}\n\n"
            f"Entries:\n{entries_text}"
        )
        provider_response = self._chat_completion(
            [
                {
                    "role": "system",
                    "content": "You summarize timesheets for managers. Be factual; do not invent projects or hours.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=900,
        )
        summary = provider_response.get("content", "").strip()
        return {
            "summary": summary,
            "user_id": subject.id,
            "entry_count": len(entries),
            "total_hours": round(total_seconds / 3600, 2),
            "date_range": {"start": start_dt.isoformat(), "end": end_dt.isoformat()},
            "provider": self.config.public_dict(),
        }

    def _parse_date_range(self, date_range: Dict[str, Any]) -> Tuple[datetime, datetime]:
        if not date_range or not isinstance(date_range, dict):
            raise AIServiceError("date_range with start and end is required.", "validation_error", 400)
        start_dt = self._parse_datetime(date_range.get("start"))
        end_dt = self._parse_datetime(date_range.get("end"))
        if not start_dt or not end_dt:
            raise AIServiceError("date_range.start and date_range.end must be ISO datetimes.", "validation_error", 400)
        if end_dt < start_dt:
            raise AIServiceError("date_range.end must be on or after date_range.start.", "validation_error", 400)
        max_span = timedelta(days=366)
        if end_dt - start_dt > max_span:
            raise AIServiceError("date_range cannot exceed 366 days.", "validation_error", 400)
        return start_dt, end_dt

    def context_preview_from_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "summary": context.get("summary", {}),
            "active_timer": context.get("active_timer"),
            "recent_entries": context.get("recent_entries", [])[:8],
            "assigned_tasks": context.get("assigned_tasks", [])[:8],
            "projects": context.get("projects", [])[:8],
        }

    def confirm_action(self, user: User, action: Dict[str, Any]) -> Dict[str, Any]:
        action_type = (action or {}).get("type")
        payload = (action or {}).get("payload") or {}
        if action_type == "start_timer":
            return self._confirm_start_timer(user, payload)
        if action_type == "create_time_entry":
            return self._confirm_create_time_entry(user, payload)
        if action_type == "summary":
            return {"ok": True, "type": "summary", "summary": str(payload.get("text") or "")}
        raise AIServiceError("Unsupported AI action.", "unsupported_action", 400)

    def _chat_completion(self, messages: List[Dict[str, str]], max_tokens: int = 700) -> Dict[str, Any]:
        url = self.config.chat_completions_url()
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self.config.provider in HOSTED_PROVIDERS and self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        if self.config.provider == "orcarouter" and self.config.routing_strategy in ROUTING_STRATEGIES:
            headers["x-routing-strategy"] = self.config.routing_strategy
        if self.config.provider == "anthropic" and self.config.api_key:
            # Anthropic OpenAI-compatible gateways often still want the Anthropic version header.
            headers.setdefault("anthropic-version", "2023-06-01")
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": max_tokens,
        }
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=self.config.timeout_seconds)
            response.raise_for_status()
            data = response.json()
        except requests.Timeout as exc:
            raise AIServiceError("AI provider timed out.", "ai_timeout", 504) from exc
        except requests.ConnectionError as exc:
            raise AIServiceError("AI provider is not reachable.", "ai_unreachable", 502) from exc
        except requests.HTTPError as exc:
            status = getattr(exc.response, "status_code", 502)
            raise AIServiceError("AI provider rejected the request.", "ai_provider_error", status) from exc
        except (ValueError, requests.RequestException) as exc:
            raise AIServiceError("AI provider returned an invalid response.", "ai_invalid_response", 502) from exc

        choices = data.get("choices") or []
        content = ""
        if choices:
            content = ((choices[0] or {}).get("message") or {}).get("content") or ""
        return {"content": content, "raw": data}

    def _build_messages(
        self, prompt: str, context: Dict[str, Any], history: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        instructions = (
            f"{self.config.system_prompt}\n\n"
            "Use only the TimeTracker context provided. If suggesting a write action, include a short explanation and "
            'a JSON block like {"actions":[{"type":"create_time_entry","label":"...","payload":{...}}]}. '
            "Supported action types are create_time_entry, start_timer, and summary. Never claim an action was executed."
        )
        messages = [
            {"role": "system", "content": instructions},
            {
                "role": "system",
                "content": "TimeTracker context:\n" + json.dumps(context, default=str, ensure_ascii=False),
            },
        ]
        for item in history[-8:]:
            role = item.get("role")
            content = item.get("content")
            if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
                messages.append({"role": role, "content": content[:4000]})
        messages.append({"role": "user", "content": prompt})
        return messages

    def _extract_actions(self, content: str) -> List[Dict[str, Any]]:
        candidates = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", content, flags=re.DOTALL)
        if not candidates:
            candidates = re.findall(r"(\{\s*\"actions\"\s*:\s*\[.*?\]\s*\})", content, flags=re.DOTALL)
        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
            except ValueError:
                continue
            actions = parsed.get("actions")
            if isinstance(actions, list):
                return [a for a in actions if isinstance(a, dict) and a.get("type")]
        return []

    def _confirm_start_timer(self, user: User, payload: Dict[str, Any]) -> Dict[str, Any]:
        project_id = self._int_or_none(payload.get("project_id"))
        task_id = self._int_or_none(payload.get("task_id"))
        if not project_id:
            raise AIServiceError("Project is required to start a timer.", "validation_error", 400)
        if not user_can_access_project(user, project_id):
            raise AIServiceError("You cannot access that project.", "forbidden", 403)
        result = TimeTrackingService().start_timer(
            user_id=user.id, project_id=project_id, task_id=task_id, notes=payload.get("notes")
        )
        if not result.get("success"):
            raise AIServiceError(
                result.get("message") or "Could not start timer.", result.get("error") or "action_failed", 400
            )
        timer = result.get("timer")
        return {"ok": True, "type": "start_timer", "timer": self._entry_dict(timer)}

    def _confirm_create_time_entry(self, user: User, payload: Dict[str, Any]) -> Dict[str, Any]:
        project_id = self._int_or_none(payload.get("project_id"))
        task_id = self._int_or_none(payload.get("task_id"))
        if project_id and not user_can_access_project(user, project_id):
            raise AIServiceError("You cannot access that project.", "forbidden", 403)
        start_time, end_time = self._resolve_entry_times(payload)
        result = TimeTrackingService().create_manual_entry(
            user_id=user.id,
            project_id=project_id,
            task_id=task_id,
            start_time=start_time,
            end_time=end_time,
            notes=payload.get("notes") or payload.get("description") or "",
            tags=payload.get("tags") or "",
            billable=bool(payload.get("billable", True)),
        )
        if not result.get("success"):
            raise AIServiceError(
                result.get("message") or "Could not create time entry.", result.get("error") or "action_failed", 400
            )
        entry = result.get("entry")
        return {"ok": True, "type": "create_time_entry", "entry": self._entry_dict(entry)}

    def _resolve_entry_times(self, payload: Dict[str, Any]) -> Tuple[datetime, datetime]:
        start_raw = payload.get("start_time")
        end_raw = payload.get("end_time")
        duration_minutes = self._int_or_none(payload.get("duration_minutes")) or 60
        end_time = self._parse_datetime(end_raw) or local_now()
        start_time = self._parse_datetime(start_raw) or (end_time - timedelta(minutes=max(1, duration_minutes)))
        if end_time < start_time:
            raise AIServiceError("End time must be after start time.", "validation_error", 400)
        return start_time, end_time

    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        if not value or not isinstance(value, str):
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            return None

    def _int_or_none(self, value: Any) -> Optional[int]:
        try:
            return int(value) if value not in (None, "") else None
        except (TypeError, ValueError):
            return None

    def _entry_dict(self, entry: Optional[TimeEntry]) -> Optional[Dict[str, Any]]:
        if not entry:
            return None
        return {
            "id": entry.id,
            "project_id": entry.project_id,
            "project_name": entry.project.name if entry.project else None,
            "task_id": entry.task_id,
            "task_name": entry.task.name if entry.task else None,
            "start_time": entry.start_time.isoformat() if entry.start_time else None,
            "end_time": entry.end_time.isoformat() if entry.end_time else None,
            "duration_hours": entry.duration_hours,
            "notes": entry.notes or "",
            "tags": entry.tag_list,
            "billable": bool(entry.billable),
            "active": entry.end_time is None,
        }

    def _task_dict(self, task: Task) -> Dict[str, Any]:
        return {
            "id": task.id,
            "name": task.name,
            "project_id": task.project_id,
            "project_name": task.project.name if task.project else None,
            "status": task.status,
            "priority": task.priority,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "estimated_hours": task.estimated_hours,
        }

    def _project_dict(self, project: Project) -> Dict[str, Any]:
        return {
            "id": project.id,
            "name": project.name,
            "client": project.client,
            "status": project.status,
            "estimated_hours": project.estimated_hours,
            "actual_hours": project.actual_hours,
            "budget_amount": float(project.budget_amount) if project.budget_amount is not None else None,
        }
