"""Match synced emails to CRM entities and persist threads."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app import db
from app.models import Client, Contact, Deal, Lead
from app.models.email_thread import EmailMessage, EmailThread
from app.utils.db import safe_commit

logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


def extract_emails(text: str) -> List[str]:
    if not text:
        return []
    return [m.lower() for m in EMAIL_RE.findall(text)]


class EmailSyncService:
    """Ingest provider threads and link them to clients / leads / deals."""

    def match_crm(self, addresses: List[str]) -> Tuple[Optional[int], Optional[int], Optional[int]]:
        """Return (client_id, lead_id, deal_id) for the first matching address."""
        normalized = {a.lower().strip() for a in addresses if a}
        if not normalized:
            return None, None, None

        # Contacts → client
        for contact in Contact.query.filter(Contact.email.isnot(None)).all():
            if contact.email and contact.email.lower() in normalized:
                return contact.client_id, None, None

        for client in Client.query.filter(Client.email.isnot(None)).all():
            if client.email and client.email.lower() in normalized:
                return client.id, None, None

        for lead in Lead.query.filter(Lead.email.isnot(None)).all():
            if lead.email and lead.email.lower() in normalized:
                return getattr(lead, "client_id", None), lead.id, None

        for deal in Deal.query.all():
            # Deals may link via contact email on related client
            if getattr(deal, "contact_email", None) and deal.contact_email.lower() in normalized:
                return getattr(deal, "client_id", None), None, deal.id

        return None, None, None

    def ingest_threads(self, provider: str, threads: List[Dict[str, Any]]) -> Dict[str, int]:
        created = updated = skipped = 0
        for raw in threads:
            external_id = str(raw.get("id") or "")
            if not external_id:
                skipped += 1
                continue
            participants = []
            for p in raw.get("participants") or []:
                participants.extend(extract_emails(p) if "@" not in p else [p.lower()])
            for msg in raw.get("messages") or []:
                participants.extend(extract_emails(msg.get("from") or ""))
                for t in msg.get("to") or []:
                    participants.extend(extract_emails(t) if isinstance(t, str) else [])

            participants = sorted(set(a for a in participants if a))
            client_id, lead_id, deal_id = self.match_crm(participants)

            thread = EmailThread.query.filter_by(provider=provider, external_thread_id=external_id).first()
            if not thread:
                thread = EmailThread(
                    provider=provider,
                    external_thread_id=external_id,
                    subject=raw.get("subject"),
                    snippet=raw.get("snippet"),
                    participants=participants,
                    client_id=client_id,
                    lead_id=lead_id,
                    deal_id=deal_id,
                )
                db.session.add(thread)
                created += 1
            else:
                thread.subject = raw.get("subject") or thread.subject
                thread.snippet = raw.get("snippet") or thread.snippet
                thread.participants = participants or thread.participants
                if client_id:
                    thread.client_id = client_id
                if lead_id:
                    thread.lead_id = lead_id
                if deal_id:
                    thread.deal_id = deal_id
                updated += 1

            last_at = None
            for msg in raw.get("messages") or []:
                mid = str(msg.get("id") or "")
                if not mid:
                    continue
                existing = EmailMessage.query.filter_by(external_message_id=mid).first()
                sent_at = msg.get("sent_at")
                if isinstance(sent_at, str):
                    try:
                        sent_at = datetime.fromisoformat(sent_at.replace("Z", "+00:00"))
                    except Exception:
                        sent_at = None
                if existing:
                    continue
                # Need thread.id — flush first for new threads
                db.session.flush()
                em = EmailMessage(
                    thread_id=thread.id,
                    external_message_id=mid,
                    from_address=(extract_emails(msg.get("from") or "") or [msg.get("from") or ""])[0][:320],
                    to_addresses=msg.get("to") or [],
                    subject=msg.get("subject"),
                    body_text=msg.get("body_text") or msg.get("snippet"),
                    sent_at=sent_at,
                )
                db.session.add(em)
                if sent_at and (last_at is None or sent_at > last_at):
                    last_at = sent_at

            if last_at:
                thread.last_message_at = last_at
            elif thread.last_message_at is None:
                thread.last_message_at = datetime.utcnow()

        if not safe_commit("email_sync_ingest", {"provider": provider, "created": created}):
            db.session.rollback()
            return {"created": 0, "updated": 0, "skipped": skipped, "error": "commit_failed"}
        return {"created": created, "updated": updated, "skipped": skipped}

    def threads_for_client(self, client_id: int, limit: int = 20):
        return (
            EmailThread.query.filter_by(client_id=client_id)
            .order_by(EmailThread.last_message_at.desc())
            .limit(limit)
            .all()
        )

    def threads_for_lead(self, lead_id: int, limit: int = 20):
        return (
            EmailThread.query.filter_by(lead_id=lead_id)
            .order_by(EmailThread.last_message_at.desc())
            .limit(limit)
            .all()
        )

    def threads_for_deal(self, deal_id: int, limit: int = 20):
        return (
            EmailThread.query.filter_by(deal_id=deal_id)
            .order_by(EmailThread.last_message_at.desc())
            .limit(limit)
            .all()
        )

    def sync_all_connected(self) -> Dict[str, Any]:
        """Run sync for all active gmail / outlook_email integrations."""
        from app.models import Integration
        from app.services.integration_service import IntegrationService

        results = []
        service = IntegrationService()
        for provider in ("gmail", "outlook_email"):
            for integration in Integration.query.filter_by(provider=provider, is_active=True).all():
                try:
                    connector = service.get_connector(integration)
                    if connector:
                        results.append({"integration_id": integration.id, "provider": provider, **connector.sync_data()})
                except Exception as exc:
                    logger.exception("Email sync failed for %s #%s", provider, integration.id)
                    results.append({"integration_id": integration.id, "provider": provider, "success": False, "error": str(exc)})
        return {"results": results}
