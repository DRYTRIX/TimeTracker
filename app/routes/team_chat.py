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
from app.utils.module_helpers import module_enabled

team_chat_bp = Blueprint("team_chat", __name__)


@team_chat_bp.route("/chat")
@login_required
@module_enabled("team_chat")
def chat_index():
    """Main chat interface"""
    # Get all channels user is member of
    channels = (
        ChatChannel.query.join(ChatChannelMember)
        .filter(ChatChannelMember.user_id == current_user.id, ChatChannel.is_archived == False)
        .order_by(ChatChannel.updated_at.desc())
        .all()
    )

    # Get direct messages (channels with type='direct' and 2 members)
    direct_channels = (
        ChatChannel.query.join(ChatChannelMember)
        .filter(
            ChatChannelMember.user_id == current_user.id,
            ChatChannel.channel_type == "direct",
            ChatChannel.is_archived == False,
        )
        .all()
    )

    return render_template("chat/index.html", channels=channels, direct_channels=direct_channels)


@team_chat_bp.route("/chat/channels/<int:channel_id>")
@login_required
@module_enabled("team_chat")
def chat_channel(channel_id):
    """View a specific chat channel"""
    channel = ChatChannel.query.get_or_404(channel_id)

    # Check membership
    membership = ChatChannelMember.query.filter_by(channel_id=channel_id, user_id=current_user.id).first()

    if not membership and not current_user.is_admin:
        flash(_("You don't have access to this channel"), "error")
        return redirect(url_for("team_chat.chat_index"))

    # Get messages
    messages = (
        ChatMessage.query.filter_by(channel_id=channel_id, is_deleted=False)
        .order_by(ChatMessage.created_at.asc())
        .limit(100)
        .all()
    )

    # Get channel members
    members = ChatChannelMember.query.filter_by(channel_id=channel_id).all()

    # Mark messages as read
    for message in messages:
        receipt = ChatReadReceipt.query.filter_by(message_id=message.id, user_id=current_user.id).first()
        if not receipt:
            receipt = ChatReadReceipt(message_id=message.id, user_id=current_user.id)
            db.session.add(receipt)

    db.session.commit()

    return render_template("chat/channel.html", channel=channel, messages=messages, members=members)


@team_chat_bp.route("/chat/channels/<int:channel_id>/send-message", methods=["POST"])
@login_required
@module_enabled("team_chat")
def send_message(channel_id):
    """Send a message via form submission (supports attachments)"""
    import json
    import os

    channel = ChatChannel.query.get_or_404(channel_id)

    # Check membership
    membership = ChatChannelMember.query.filter_by(channel_id=channel_id, user_id=current_user.id).first()

    if not membership and not current_user.is_admin:
        flash(_("You don't have access to this channel"), "error")
        return redirect(url_for("team_chat.chat_channel", channel_id=channel_id))

    content = request.form.get("content", "").strip()
    attachment_data = request.form.get("attachment_data")

    if not content and not attachment_data:
        flash(_("Message cannot be empty"), "error")
        return redirect(url_for("team_chat.chat_channel", channel_id=channel_id))

    # Parse attachment data if provided
    attachment_url = None
    attachment_filename = None
    attachment_size = None
    message_type = "text"

    if attachment_data:
        try:
            attachment_info = json.loads(attachment_data)
            attachment_url = attachment_info.get("url")
            attachment_filename = attachment_info.get("filename")
            attachment_size = attachment_info.get("size")
            message_type = "file"
        except (json.JSONDecodeError, TypeError, ValueError, AttributeError) as e:
            from flask import current_app
            current_app.logger.debug(f"Could not parse attachment data: {e}")
            pass

    # Create message
    message = ChatMessage(
        channel_id=channel_id,
        user_id=current_user.id,
        message=content or attachment_filename or "",
        message_type=message_type,
        attachment_url=attachment_url,
        attachment_filename=attachment_filename,
        attachment_size=attachment_size,
    )

    # Parse mentions
    mentions = message.parse_mentions()
    if mentions:
        message.mentions = mentions

    db.session.add(message)

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
                priority="high",
            )

    if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"success": True, "message": message.to_dict()})

    return redirect(url_for("team_chat.chat_channel", channel_id=channel_id))


@team_chat_bp.route("/api/chat/channels", methods=["GET", "POST"])
@login_required
@module_enabled("team_chat")
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
            project_id=data.get("project_id"),
        )
        db.session.add(channel)
        db.session.flush()

        # Add creator as member
        member = ChatChannelMember(channel_id=channel.id, user_id=current_user.id, is_admin=True)
        db.session.add(member)

        # Add other members if specified
        if data.get("member_ids"):
            for user_id in data.get("member_ids", []):
                if user_id != current_user.id:
                    member = ChatChannelMember(channel_id=channel.id, user_id=user_id)
                    db.session.add(member)

        db.session.commit()

        return jsonify({"success": True, "channel": channel.to_dict()})

    # GET - List channels
    channels = (
        ChatChannel.query.join(ChatChannelMember)
        .filter(ChatChannelMember.user_id == current_user.id, ChatChannel.is_archived == False)
        .order_by(ChatChannel.updated_at.desc())
        .all()
    )

    return jsonify({"channels": [c.to_dict() for c in channels]})


@team_chat_bp.route("/api/chat/channels/<int:channel_id>/messages", methods=["GET", "POST"])
@login_required
@module_enabled("team_chat")
def api_messages(channel_id):
    """Get or create messages"""
    channel = ChatChannel.query.get_or_404(channel_id)

    # Check membership
    membership = ChatChannelMember.query.filter_by(channel_id=channel_id, user_id=current_user.id).first()

    if not membership and not current_user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    if request.method == "POST":
        # Create new message
        data = request.get_json()

        message = ChatMessage(
            channel_id=channel_id,
            user_id=current_user.id,
            message=data.get("message", ""),
            message_type=data.get("message_type", "text"),
            reply_to_id=data.get("reply_to_id"),
            attachment_url=data.get("attachment_url"),
            attachment_filename=data.get("attachment_filename"),
            attachment_size=data.get("attachment_size"),
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
                    priority="high",
                )

        return jsonify({"success": True, "message": message.to_dict()})

    # GET - List messages
    before_id = request.args.get("before_id", type=int)
    limit = request.args.get("limit", 50, type=int)

    query = ChatMessage.query.filter_by(channel_id=channel_id, is_deleted=False)

    if before_id:
        query = query.filter(ChatMessage.id < before_id)

    messages = query.order_by(ChatMessage.created_at.desc()).limit(limit).all()
    messages.reverse()  # Return in chronological order

    # Mark as read
    for message in messages:
        receipt = ChatReadReceipt.query.filter_by(message_id=message.id, user_id=current_user.id).first()
        if not receipt:
            receipt = ChatReadReceipt(message_id=message.id, user_id=current_user.id)
            db.session.add(receipt)

    db.session.commit()

    return jsonify({"messages": [m.to_dict() for m in messages]})


@team_chat_bp.route("/api/chat/messages/<int:message_id>", methods=["PUT", "DELETE"])
@login_required
@module_enabled("team_chat")
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
@module_enabled("team_chat")
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


@team_chat_bp.route("/chat/channels/<int:channel_id>/messages/<int:message_id>/attachments/download")
@login_required
@module_enabled("team_chat")
def download_attachment(channel_id, message_id):
    """Download an attachment from a chat message"""
    from flask import send_file, current_app
    import os

    message = ChatMessage.query.get_or_404(message_id)

    # Verify message belongs to channel
    if message.channel_id != channel_id:
        flash(_("Invalid message"), "error")
        return redirect(url_for("team_chat.chat_channel", channel_id=channel_id))

    # Check membership
    membership = ChatChannelMember.query.filter_by(channel_id=channel_id, user_id=current_user.id).first()

    if not membership and not current_user.is_admin:
        flash(_("You don't have access to this channel"), "error")
        return redirect(url_for("team_chat.chat_index"))

    if not message.attachment_url:
        flash(_("No attachment found"), "error")
        return redirect(url_for("team_chat.chat_channel", channel_id=channel_id))

    # Build file path
    file_path = os.path.join(current_app.root_path, "..", message.attachment_url)

    if not os.path.exists(file_path):
        flash(_("File not found"), "error")
        return redirect(url_for("team_chat.chat_channel", channel_id=channel_id))

    return send_file(
        file_path,
        as_attachment=True,
        download_name=message.attachment_filename,
    )


@team_chat_bp.route("/chat/channels/<int:channel_id>/upload-attachment", methods=["POST"])
@login_required
@module_enabled("team_chat")
def upload_attachment(channel_id):
    """Upload an attachment for a chat message"""
    from werkzeug.utils import secure_filename
    from flask import current_app, jsonify
    import os
    from datetime import datetime

    channel = ChatChannel.query.get_or_404(channel_id)

    # Check membership
    membership = ChatChannelMember.query.filter_by(channel_id=channel_id, user_id=current_user.id).first()

    if not membership and not current_user.is_admin:
        return jsonify({"error": _("You don't have access to this channel")}), 403

    # File upload configuration
    ALLOWED_EXTENSIONS = {
        "png",
        "jpg",
        "jpeg",
        "gif",
        "pdf",
        "doc",
        "docx",
        "txt",
        "xls",
        "xlsx",
        "zip",
        "rar",
        "csv",
        "json",
    }
    UPLOAD_FOLDER = "uploads/chat_attachments"
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

    def allowed_file(filename):
        return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

    if "file" not in request.files:
        return jsonify({"error": _("No file provided")}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": _("No file selected")}), 400

    # Use the file upload utility for proper validation
    from app.utils.file_upload import validate_file_upload
    # Normalize allowed extensions to include leading dots for validation
    normalized_allowed = {ext if ext.startswith('.') else '.' + ext for ext in ALLOWED_EXTENSIONS}
    
    is_valid, error_msg = validate_file_upload(file, allowed_extensions=normalized_allowed, max_size=MAX_FILE_SIZE)
    if not is_valid:
        return jsonify({"error": _(error_msg)}), 400

    # Save file - secure_filename after validation
    original_filename = secure_filename(file.filename)
    if not original_filename:
        return jsonify({"error": _("Invalid filename")}), 400
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{channel_id}_{timestamp}_{original_filename}"

    # Ensure upload directory exists
    upload_dir = os.path.join(current_app.root_path, "..", UPLOAD_FOLDER)
    try:
        os.makedirs(upload_dir, exist_ok=True)
    except (OSError, IOError) as e:
        current_app.logger.error(f"Failed to create upload directory {upload_dir}: {e}")
        return jsonify({"error": _("Server error: Could not create upload directory")}), 500

    file_path = os.path.join(upload_dir, filename)
    try:
        file.save(file_path)
        file_size = os.path.getsize(file_path)
    except (OSError, IOError) as e:
        current_app.logger.error(f"Failed to save file {filename}: {e}")
        return jsonify({"error": _("Server error: Could not save file")}), 500

    # Return file info for message creation
    return jsonify(
        {
            "success": True,
            "attachment": {
                "url": os.path.join(UPLOAD_FOLDER, filename),
                "filename": original_filename,
                "size": file_size,
            },
        }
    )


@team_chat_bp.route("/api/chat/users", methods=["GET"])
@login_required
@module_enabled("team_chat")
def api_chat_users():
    """Get list of users for chat selection"""
    # Get all active users except current user
    # Order by full_name if available, otherwise by username
    users = (
        User.query.filter(User.id != current_user.id, User.is_active == True)
        .order_by(User.full_name, User.username)
        .all()
    )
    
    return jsonify({"users": [user.to_dict() for user in users]})


@team_chat_bp.route("/api/chat/direct-message/<int:user_id>", methods=["POST"])
@login_required
@module_enabled("team_chat")
def api_create_direct_message(user_id):
    """Create or find existing direct message channel with a user"""
    # CSRF token is validated automatically for form submissions
    # Get target user
    target_user = User.query.get_or_404(user_id)
    
    if target_user.id == current_user.id:
        return jsonify({"error": _("Cannot create direct message with yourself")}), 400
    
    if not target_user.is_active:
        return jsonify({"error": _("User is not active")}), 400
    
    # Check if direct message channel already exists
    # Direct messages have type='direct' and exactly 2 members
    existing_channels = (
        ChatChannel.query.join(ChatChannelMember)
        .filter(
            ChatChannel.channel_type == "direct",
            ChatChannel.is_archived == False,
            ChatChannelMember.user_id == current_user.id
        )
        .all()
    )
    
    # Check each channel to see if it's a direct message with target_user
    for channel in existing_channels:
        members = [m.user_id for m in channel.members.all()]
        if len(members) == 2 and target_user.id in members:
            # Found existing direct message channel
            return jsonify({
                "success": True,
                "channel_id": channel.id,
                "channel": channel.to_dict()
            })
    
    # Create new direct message channel
    channel = ChatChannel(
        name=f"{current_user.display_name} & {target_user.display_name}",
        channel_type="direct",
        created_by=current_user.id,
    )
    db.session.add(channel)
    db.session.flush()
    
    # Add both users as members
    member1 = ChatChannelMember(channel_id=channel.id, user_id=current_user.id)
    member2 = ChatChannelMember(channel_id=channel.id, user_id=target_user.id)
    db.session.add(member1)
    db.session.add(member2)
    
    db.session.commit()
    
    return jsonify({
        "success": True,
        "channel_id": channel.id,
        "channel": channel.to_dict()
    })
