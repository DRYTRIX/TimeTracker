"""
Team Chat routes
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models.team_chat import ChatChannel, ChatMessage, ChatChannelMember, ChatReadReceipt
from app.models import Project, User
from flask_babel import gettext as _
from datetime import datetime
from sqlalchemy import and_, or_

team_chat_bp = Blueprint("team_chat", __name__)


@team_chat_bp.route("/chat")
@login_required
def chat_index():
    """Main chat interface"""
    # Get all channels user is member of
    channels = ChatChannel.query.join(ChatChannelMember).filter(
        ChatChannelMember.user_id == current_user.id,
        ChatChannel.is_archived == False
    ).order_by(ChatChannel.updated_at.desc()).all()

    # Get direct messages (channels with type='direct' and 2 members)
    direct_channels = ChatChannel.query.join(ChatChannelMember).filter(
        ChatChannelMember.user_id == current_user.id,
        ChatChannel.channel_type == "direct",
        ChatChannel.is_archived == False
    ).all()

    return render_template("chat/index.html", channels=channels, direct_channels=direct_channels)


@team_chat_bp.route("/chat/channels/<int:channel_id>")
@login_required
def chat_channel(channel_id):
    """View a specific chat channel"""
    channel = ChatChannel.query.get_or_404(channel_id)

    # Check membership
    membership = ChatChannelMember.query.filter_by(
        channel_id=channel_id,
        user_id=current_user.id
    ).first()

    if not membership and not current_user.is_admin:
        flash(_("You don't have access to this channel"), "error")
        return redirect(url_for("team_chat.chat_index"))

    # Get messages
    messages = ChatMessage.query.filter_by(
        channel_id=channel_id,
        is_deleted=False
    ).order_by(ChatMessage.created_at.asc()).limit(100).all()

    # Get channel members
    members = ChatChannelMember.query.filter_by(channel_id=channel_id).all()

    # Mark messages as read
    for message in messages:
        receipt = ChatReadReceipt.query.filter_by(
            message_id=message.id,
            user_id=current_user.id
        ).first()
        if not receipt:
            receipt = ChatReadReceipt(message_id=message.id, user_id=current_user.id)
            db.session.add(receipt)

    db.session.commit()

    return render_template("chat/channel.html", channel=channel, messages=messages, members=members)


@team_chat_bp.route("/api/chat/channels", methods=["GET", "POST"])
@login_required
def api_channels():
    """Get or create channels"""
    if request.method == "POST":
        # Create new channel
        data = request.get_json()
        
        channel = ChatChannel(
            name=data.get("name"),
            description=data.get("description"),
            channel_type=data.get("channel_type", "public"),
            created_by=current_user.id,
            project_id=data.get("project_id")
        )
        db.session.add(channel)
        db.session.flush()

        # Add creator as member
        member = ChatChannelMember(
            channel_id=channel.id,
            user_id=current_user.id,
            is_admin=True
        )
        db.session.add(member)

        # Add other members if specified
        if data.get("member_ids"):
            for user_id in data.get("member_ids", []):
                if user_id != current_user.id:
                    member = ChatChannelMember(
                        channel_id=channel.id,
                        user_id=user_id
                    )
                    db.session.add(member)

        db.session.commit()

        return jsonify({"success": True, "channel": channel.to_dict()})

    # GET - List channels
    channels = ChatChannel.query.join(ChatChannelMember).filter(
        ChatChannelMember.user_id == current_user.id,
        ChatChannel.is_archived == False
    ).order_by(ChatChannel.updated_at.desc()).all()

    return jsonify({
        "channels": [c.to_dict() for c in channels]
    })


@team_chat_bp.route("/api/chat/channels/<int:channel_id>/messages", methods=["GET", "POST"])
@login_required
def api_messages(channel_id):
    """Get or create messages"""
    channel = ChatChannel.query.get_or_404(channel_id)

    # Check membership
    membership = ChatChannelMember.query.filter_by(
        channel_id=channel_id,
        user_id=current_user.id
    ).first()

    if not membership and not current_user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    if request.method == "POST":
        # Create new message
        data = request.get_json()
        
        message = ChatMessage(
            channel_id=channel_id,
            user_id=current_user.id,
            message=data.get("message"),
            message_type=data.get("message_type", "text"),
            reply_to_id=data.get("reply_to_id")
        )

        # Parse mentions
        mentions = message.parse_mentions()
        if mentions:
            message.mentions = mentions

        db.session.add(message)
        db.session.commit()

        # Update channel updated_at
        channel.updated_at = datetime.utcnow()
        db.session.commit()

        # Notify mentioned users
        if mentions:
            from app.utils.notification_service import NotificationService
            service = NotificationService()
            for user_id in mentions:
                service.send_notification(
                    user_id=user_id,
                    title="You were mentioned",
                    message=f"{current_user.display_name} mentioned you in {channel.name}",
                    type="info",
                    priority="high"
                )

        return jsonify({"success": True, "message": message.to_dict()})

    # GET - List messages
    before_id = request.args.get("before_id", type=int)
    limit = request.args.get("limit", 50, type=int)

    query = ChatMessage.query.filter_by(
        channel_id=channel_id,
        is_deleted=False
    )

    if before_id:
        query = query.filter(ChatMessage.id < before_id)

    messages = query.order_by(ChatMessage.created_at.desc()).limit(limit).all()
    messages.reverse()  # Return in chronological order

    # Mark as read
    for message in messages:
        receipt = ChatReadReceipt.query.filter_by(
            message_id=message.id,
            user_id=current_user.id
        ).first()
        if not receipt:
            receipt = ChatReadReceipt(message_id=message.id, user_id=current_user.id)
            db.session.add(receipt)

    db.session.commit()

    return jsonify({
        "messages": [m.to_dict() for m in messages]
    })


@team_chat_bp.route("/api/chat/messages/<int:message_id>", methods=["PUT", "DELETE"])
@login_required
def api_message(message_id):
    """Update or delete message"""
    message = ChatMessage.query.get_or_404(message_id)

    if message.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    if request.method == "PUT":
        # Update message
        data = request.get_json()
        message.message = data.get("message", message.message)
        message.is_edited = True
        message.edited_at = datetime.utcnow()
        
        # Re-parse mentions
        message.parse_mentions()

        db.session.commit()
        return jsonify({"success": True, "message": message.to_dict()})

    elif request.method == "DELETE":
        # Soft delete
        message.is_deleted = True
        db.session.commit()
        return jsonify({"success": True})


@team_chat_bp.route("/api/chat/messages/<int:message_id>/react", methods=["POST"])
@login_required
def api_react(message_id):
    """Add or remove reaction to message"""
    message = ChatMessage.query.get_or_404(message_id)
    data = request.get_json()
    
    emoji = data.get("emoji")
    if not emoji:
        return jsonify({"error": "Emoji required"}), 400

    reactions = message.reactions or {}
    if emoji not in reactions:
        reactions[emoji] = []
    
    if current_user.id in reactions[emoji]:
        reactions[emoji].remove(current_user.id)
        if not reactions[emoji]:
            del reactions[emoji]
    else:
        reactions[emoji].append(current_user.id)

    message.reactions = reactions if reactions else None
    db.session.commit()

    return jsonify({"success": True, "reactions": reactions})

