"""
Linear integration: import issues as tasks using a Personal API Key.

https://developers.linear.app/docs/graphql/working-with-the-graphql-api
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.integrations.base import BaseConnector
from app.utils.integration_http import integration_session, session_request

logger = logging.getLogger(__name__)

LINEAR_GRAPHQL = "https://api.linear.app/graphql"


class LinearConnector(BaseConnector):
    """Linear connector (API key; issues → tasks)."""

    display_name = "Linear"
    description = "Import Linear issues as tasks"
    icon = "tasks"

    @property
    def provider_name(self) -> str:
        return "linear"

    def get_authorization_url(self, redirect_uri: str, state: str = None) -> str:
        raise NotImplementedError("Linear uses a Personal API key; configure in Integrations.")

    def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        raise NotImplementedError("Linear uses a Personal API key.")

    def refresh_access_token(self) -> Dict[str, Any]:
        raise NotImplementedError("Linear API keys do not expire.")

    def _api_key(self) -> Optional[str]:
        if self.credentials and self.credentials.access_token:
            return self.credentials.access_token.strip()
        return None

    def _graphql(self, query: str, variables: Optional[Dict] = None) -> Dict[str, Any]:
        key = self._api_key()
        if not key:
            raise ValueError("No Linear API key configured.")
        session = integration_session()
        resp = session_request(
            session,
            "POST",
            LINEAR_GRAPHQL,
            headers={"Authorization": key, "Content-Type": "application/json"},
            json={"query": query, "variables": variables or {}},
        )
        if resp.status_code >= 400:
            raise ValueError(f"Linear API HTTP {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
        if data.get("errors"):
            raise ValueError(f"Linear GraphQL error: {data['errors'][:1]}")
        return data.get("data") or {}

    def test_connection(self) -> Dict[str, Any]:
        try:
            data = self._graphql("query { viewer { id name } }")
            viewer = data.get("viewer") or {}
            name = viewer.get("name") or viewer.get("id") or "OK"
            return {"success": True, "message": f"Connected to Linear as {name}."}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def sync_data(self, sync_type: str = "full") -> Dict[str, Any]:
        from app import db
        from app.models import Project, Task
        from app.utils.integration_sync_context import (
            ensure_project_integration_fields,
            find_project_by_integration_ref,
            find_task_by_integration_ref,
            require_sync_context,
            set_task_integration_ref,
        )

        key = self._api_key()
        if not key:
            return {"success": False, "message": "No Linear API key. Save your key under Integrations → Linear."}

        team_filter = (self.integration.config or {}).get("linear_team_keys", "")
        team_keys: Optional[List[str]] = None
        if team_filter and isinstance(team_filter, str):
            team_keys = [t.strip() for t in team_filter.split(",") if t.strip()]

        try:
            actor_id, client_id = require_sync_context(self.integration)
        except ValueError as e:
            return {"success": False, "message": str(e)}

        q = """
        query SyncIssues($after: String) {
          issues(first: 100, after: $after) {
            pageInfo { hasNextPage endCursor }
            nodes {
              id
              identifier
              title
              url
              team { key name }
              state { name }
            }
          }
        }
        """
        all_nodes: List[Dict] = []
        after = None
        try:
            for _ in range(20):
                data = self._graphql(q, {"after": after})
                conn = data.get("issues") or {}
                nodes = conn.get("nodes") or []
                for n in nodes:
                    tk = (n.get("team") or {}).get("key") or ""
                    if team_keys and tk not in team_keys:
                        continue
                    all_nodes.append(n)
                page = conn.get("pageInfo") or {}
                if not page.get("hasNextPage"):
                    break
                after = page.get("endCursor")
        except Exception as e:
            logger.error("Linear sync fetch failed: %s", e, exc_info=True)
            return {"success": False, "message": str(e)}

        synced = 0
        errors: List[str] = []
        projects_cache: Dict[str, Project] = {}

        def project_for_team(team_key: str, team_name: str) -> Optional[Project]:
            ref = f"{team_key}:{team_name}" if team_key else team_name or "default"
            if ref in projects_cache:
                return projects_cache[ref]
            p = find_project_by_integration_ref(client_id, "linear", ref)
            if not p:
                display = f"Linear / {team_name or team_key or 'Issues'}"
                p = Project.query.filter_by(client_id=client_id, name=display).first()
            if not p:
                try:
                    p = Project(
                        name=f"Linear / {team_name or team_key or 'Issues'}",
                        client_id=client_id,
                        description=f"Linear workspace team {team_key or '—'}",
                        status="active",
                    )
                    db.session.add(p)
                    db.session.flush()
                except Exception as ex:
                    errors.append(f"Project create: {ex}")
                    return None
            ensure_project_integration_fields(
                project=p,
                source="linear",
                ref=ref,
                display_name=p.name,
                description=p.description or "",
            )
            projects_cache[ref] = p
            return p

        for n in all_nodes:
            issue_id = n.get("id")
            if not issue_id:
                continue
            team = n.get("team") or {}
            tk = team.get("key") or "unknown"
            tn = team.get("name") or tk
            project = project_for_team(tk, tn)
            if not project:
                continue
            title = (n.get("title") or "Untitled").strip()[:500]
            ident = n.get("identifier") or issue_id
            try:
                task = find_task_by_integration_ref(project.id, issue_id, source="linear")
                state_name = (n.get("state") or {}).get("name") or ""
                status = "done" if state_name.lower() in ("done", "completed", "canceled", "cancelled") else "todo"
                if not task:
                    task = Task(
                        name=f"{ident}: {title}"[:500],
                        description=(n.get("url") or "")[:2000],
                        project_id=project.id,
                        status=status,
                        created_by=actor_id,
                    )
                    db.session.add(task)
                    db.session.flush()
                    set_task_integration_ref(
                        task,
                        source="linear",
                        ref=issue_id,
                        extra={"identifier": ident, "url": n.get("url")},
                    )
                    synced += 1
                else:
                    task.name = f"{ident}: {title}"[:500]
                    task.status = status
                    if n.get("url"):
                        task.description = (n.get("url") or "")[:2000]
                    set_task_integration_ref(
                        task,
                        source="linear",
                        ref=issue_id,
                        extra={"identifier": ident, "url": n.get("url")},
                    )
                    synced += 1
            except Exception as ex:
                errors.append(f"{ident}: {ex}")
                logger.warning("Linear issue upsert failed: %s", ex, exc_info=True)

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return {"success": False, "message": f"Database error: {e}"}

        msg = f"Processed {len(all_nodes)} Linear issues."
        if errors:
            msg += f" ({len(errors)} errors)"
        return {
            "success": True,
            "message": msg,
            "synced_items": synced,
            "synced_count": synced,
            "errors": errors[:20],
        }

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "fields": [
                {
                    "name": "linear_team_keys",
                    "label": "Team keys (optional)",
                    "type": "text",
                    "description": "Comma-separated Linear team keys to import (empty = all teams)",
                    "required": False,
                },
                {
                    "name": "auto_sync",
                    "label": "Automatic sync",
                    "type": "boolean",
                    "default": True,
                },
            ]
        }
