"""Service for public shareable report links."""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from flask import url_for

from app import db
from app.models import SavedReportView, SharedReportLink


class SharedReportService:
    """Create and resolve public shared report links."""

    def create_link(
        self,
        saved_view: SavedReportView,
        created_by_id: int,
        expires_in_days: Optional[int] = None,
        password: Optional[str] = None,
    ) -> SharedReportLink:
        expires_at = None
        if expires_in_days is not None:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        try:
            config = json.loads(saved_view.config_json)
        except (json.JSONDecodeError, TypeError, ValueError):
            config = {}

        link = SharedReportLink(
            saved_view_id=saved_view.id,
            created_by_id=created_by_id,
            report_config_snapshot=config,
            report_name=saved_view.name,
            expires_at=expires_at,
            password=password,
        )
        db.session.add(link)
        db.session.flush()
        return link

    def resolve_token(self, token: str) -> Tuple[Optional[SharedReportLink], Optional[str]]:
        link = SharedReportLink.query.filter_by(token=token).first()
        if not link:
            return None, "Link not found"
        if not link.is_active:
            return None, "Link has been revoked"
        if link.is_expired():
            return None, "Link has expired"
        return link, None

    def execute_report_with_snapshot(self, link: SharedReportLink) -> Dict[str, Any]:
        from app.routes.custom_reports import generate_report_data

        config = link.get_config()
        report_data = generate_report_data(config, link.created_by_id)
        link.record_access()
        db.session.commit()
        return report_data

    def get_public_url(self, link: SharedReportLink) -> str:
        return url_for("custom_reports.view_shared_report", token=link.token, _external=True)

    def revoke_link(self, saved_view_id: int, token: str) -> bool:
        link = SharedReportLink.query.filter_by(saved_view_id=saved_view_id, token=token).first()
        if not link:
            return False
        link.is_active = False
        link.updated_at = datetime.utcnow()
        db.session.commit()
        return True

    def list_active_links_for_view(self, saved_view_id: int):
        return (
            SharedReportLink.query.filter_by(saved_view_id=saved_view_id, is_active=True)
            .order_by(SharedReportLink.created_at.desc())
            .all()
        )
