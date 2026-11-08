"""Minimal team chat service extracted from web route ORM usage."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from app import db
from app.models.team_chat import ChatChannel, ChatChannelMember, ChatMessage, ChatReadReceipt


class TeamChatService:
    """Channel and message helpers for API and web callers."""

    def list_channels_for_user(self, user_id: int, *, include_archived: bool = False) -> List[ChatChannel]:
        query = ChatChannel.query.join(ChatChannelMember).filter(ChatChannelMember.user_id == user_id)
        if not include_archived:
            query = query.filter(ChatChannel.is_archived == False)  # noqa: E712
        return query.order_by(ChatChannel.updated_at.desc()).all()

    def get_channel(self, channel_id: int) -> Optional[ChatChannel]:
        return ChatChannel.query.get(channel_id)

    def user_can_access_channel(self, channel_id: int, user_id: int, *, is_admin: bool = False) -> bool:
        if is_admin:
            return True
        return (
            ChatChannelMember.query.filter_by(channel_id=channel_id, user_id=user_id).first() is not None
        )

    def list_messages(
        self,
        channel_id: int,
        *,
        before_id: Optional[int] = None,
        limit: int = 50,
    ) -> List[ChatMessage]:
        query = ChatMessage.query.filter_by(channel_id=channel_id, is_deleted=False)
        if before_id:
            query = query.filter(ChatMessage.id < before_id)
        messages = query.order_by(ChatMessage.created_at.desc()).limit(max(1, min(limit, 200))).all()
        messages.reverse()
        return messages

    def mark_messages_read(self, messages: List[ChatMessage], user_id: int) -> None:
        message_ids = [m.id for m in messages]
        if not message_ids:
            return
        existing = ChatReadReceipt.query.filter(
            ChatReadReceipt.message_id.in_(message_ids),
            ChatReadReceipt.user_id == user_id,
        ).all()
        have = {r.message_id for r in existing}
        for message in messages:
            if message.id not in have:
                db.session.add(ChatReadReceipt(message_id=message.id, user_id=user_id))
        db.session.commit()

    def post_message(
        self,
        channel_id: int,
        user_id: int,
        *,
        message: str,
        message_type: str = "text",
        reply_to_id: Optional[int] = None,
        attachment_url: Optional[str] = None,
        attachment_filename: Optional[str] = None,
        attachment_size: Optional[int] = None,
    ) -> ChatMessage:
        channel = ChatChannel.query.get_or_404(channel_id)
        chat_message = ChatMessage(
            channel_id=channel_id,
            user_id=user_id,
            message=message or "",
            message_type=message_type or "text",
            reply_to_id=reply_to_id,
            attachment_url=attachment_url,
            attachment_filename=attachment_filename,
            attachment_size=attachment_size,
        )
        mentions = chat_message.parse_mentions()
        if mentions:
            chat_message.mentions = mentions
        db.session.add(chat_message)
        channel.updated_at = datetime.utcnow()
        db.session.commit()
        return chat_message

    def create_channel(
        self,
        *,
        name: str,
        created_by: int,
        description: Optional[str] = None,
        channel_type: str = "public",
        project_id: Optional[int] = None,
        member_ids: Optional[List[int]] = None,
    ) -> ChatChannel:
        channel = ChatChannel(
            name=name,
            description=description,
            channel_type=channel_type or "public",
            created_by=created_by,
            project_id=project_id,
        )
        db.session.add(channel)
        db.session.flush()
        db.session.add(ChatChannelMember(channel_id=channel.id, user_id=created_by, is_admin=True))
        for user_id in member_ids or []:
            if user_id != created_by:
                db.session.add(ChatChannelMember(channel_id=channel.id, user_id=user_id))
        db.session.commit()
        return channel

    def notify_mentions(self, channel: ChatChannel, sender_display_name: str, mentions: List[int]) -> None:
        if not mentions:
            return
        from app.utils.notification_service import NotificationService

        service = NotificationService()
        for user_id in mentions:
            service.send_notification(
                user_id=user_id,
                title="You were mentioned",
                message=f"{sender_display_name} mentioned you in {channel.name}",
                type="info",
                priority="high",
            )

    def serialize_channel(self, channel: ChatChannel) -> Dict[str, Any]:
        return channel.to_dict()

    def serialize_message(self, message: ChatMessage) -> Dict[str, Any]:
        return message.to_dict()
