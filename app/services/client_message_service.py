"""Client–team messaging service."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from app import db
from app.models.client_message import ClientMessage
from app.utils.db import safe_commit


class ClientMessageService:
    """Send and list messages for a client communication hub thread."""

    def list_messages(self, client_id: int, *, after_id: Optional[int] = None, limit: int = 100) -> List[ClientMessage]:
        q = ClientMessage.query.filter_by(client_id=client_id)
        if after_id:
            q = q.filter(ClientMessage.id > after_id)
        return q.order_by(ClientMessage.created_at.asc()).limit(min(limit, 500)).all()

    def send(
        self,
        client_id: int,
        *,
        sender_type: str,
        body: str,
        sender_id: Optional[int] = None,
        sender_name: Optional[str] = None,
        attachments=None,
    ) -> Optional[ClientMessage]:
        body = (body or "").strip()
        if not body:
            return None
        if sender_type not in ("team", "client"):
            raise ValueError("sender_type must be 'team' or 'client'")

        msg = ClientMessage(
            client_id=client_id,
            sender_type=sender_type,
            sender_id=sender_id,
            sender_name=sender_name,
            body=body,
            attachments=attachments or [],
        )
        db.session.add(msg)
        if not safe_commit("client_message_send", {"client_id": client_id}):
            db.session.rollback()
            return None
        return msg

    def mark_thread_read(self, client_id: int, *, for_sender_type: str) -> int:
        """Mark messages from the opposite party as read."""
        opposite = "client" if for_sender_type == "team" else "team"
        rows = (
            ClientMessage.query.filter_by(client_id=client_id, sender_type=opposite)
            .filter(ClientMessage.read_at.is_(None))
            .all()
        )
        now = datetime.utcnow()
        for row in rows:
            row.read_at = now
        if rows:
            safe_commit("client_message_mark_read", {"client_id": client_id, "count": len(rows)})
        return len(rows)

    def unread_count(self, client_id: int, *, for_sender_type: str) -> int:
        opposite = "client" if for_sender_type == "team" else "team"
        return (
            ClientMessage.query.filter_by(client_id=client_id, sender_type=opposite)
            .filter(ClientMessage.read_at.is_(None))
            .count()
        )
