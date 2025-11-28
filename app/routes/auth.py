from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    current_app,
    send_from_directory,
)
from flask_login import login_user, logout_user, login_required, current_user
from app import db, log_event, track_event
from app.models import User
from app.config import Config
from app.utils.db import safe_commit
from flask_babel import gettext as _
from app import oauth, limiter
from app.utils.posthog_segmentation import identify_user_with_segments, set_super_properties
from app.utils.posthog_funnels import track_onboarding_started


auth_bp = Blueprint("auth", __name__)

# Allowed file extensions for user avatars (avoid SVG due to XSS risk)
ALLOWED_AVATAR_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def allowed_avatar_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_AVATAR_EXTENSIONS


def get_avatar_upload_folder() -> str:
    """Get the upload folder path for user avatars and ensure it exists."""
    import os

    # Store avatars in /data volume to persist between container updates
    upload_folder = os.path.join(current_app.config.get("UPLOAD_FOLDER", "/data/uploads"), "avatars")
    os.makedirs(upload_folder, exist_ok=True)
    return upload_folder


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])  # rate limit login attempts
def login():
    """Login page. Local username login is allowed only if AUTH_METHOD != 'oidc'."""
    if request.method == "GET":
        try:
            current_app.logger.info("GET /login from %s", request.headers.get("X-Forwarded-For") or request.remote_addr)
        except Exception:
            pass

    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    # Get authentication method
    try:
        auth_method = (getattr(Config, "AUTH_METHOD", "local") or "local").strip().lower()
    except Exception:
        auth_method = "local"

    # Determine if password authentication is required
    requires_password = auth_method in ("local", "both")

    # If OIDC-only mode, redirect to OIDC login start
    if auth_method == "oidc":
        return redirect(url_for("auth.login_oidc", next=request.args.get("next")))

    if request.method == "POST":
        try:
            username = request.form.get("username", "").strip().lower()
            password = request.form.get("password", "")
            current_app.logger.info(
                "POST /login (username=%s, auth_method=%s) from %s",
                username or "<empty>",
                auth_method,
                request.headers.get("X-Forwarded-For") or request.remote_addr,
            )

            if not username:
                log_event("auth.login_failed", reason="empty_username", auth_method=auth_method)
                flash(_("Username is required"), "error")
                return render_template(
                    "auth/login.html",
                    allow_self_register=Config.ALLOW_SELF_REGISTER,
                    auth_method=auth_method,
                    requires_password=requires_password,
                )

            # Normalize admin usernames from config
            try:
                admin_usernames = [u.strip().lower() for u in (Config.ADMIN_USERNAMES or [])]
            except Exception:
                admin_usernames = ["admin"]

            # Check if user exists
            user = User.query.filter_by(username=username).first()
            current_app.logger.info("User lookup for '%s': %s", username, "found" if user else "not found")

            if not user:
                # Check if self-registration is allowed
                if Config.ALLOW_SELF_REGISTER:
                    # If password auth is required, validate password during self-registration
                    if requires_password:
                        if not password:
                            flash(_("Password is required to create an account."), "error")
                            return render_template(
                                "auth/login.html",
                                allow_self_register=Config.ALLOW_SELF_REGISTER,
                                auth_method=auth_method,
                                requires_password=requires_password,
                            )
                        if len(password) < 8:
                            flash(_("Password must be at least 8 characters long."), "error")
                            return render_template(
                                "auth/login.html",
                                allow_self_register=Config.ALLOW_SELF_REGISTER,
                                auth_method=auth_method,
                                requires_password=requires_password,
                            )

                    # Create new user, promote to admin if username is configured as admin
                    role = "admin" if username in admin_usernames else "user"
                    user = User(username=username, role=role)
                    # Set password if password auth is required
                    if requires_password and password:
                        user.set_password(password)
                    db.session.add(user)
                    if not safe_commit("self_register_user", {"username": username}):
                        current_app.logger.error("Self-registration failed for '%s' due to DB error", username)
                        flash(
                            _("Could not create your account due to a database error. Please try again later."), "error"
                        )
                        return render_template(
                            "auth/login.html",
                            allow_self_register=Config.ALLOW_SELF_REGISTER,
                            auth_method=auth_method,
                            requires_password=requires_password,
                        )
                    current_app.logger.info("Created new user '%s'", username)

                    # Track onboarding started for new user
                    track_onboarding_started(
                        user.id, {"auth_method": auth_method, "self_registered": True, "is_admin": role == "admin"}
                    )

                    flash(_("Welcome! Your account has been created."), "success")
                else:
                    log_event("auth.login_failed", username=username, reason="user_not_found", auth_method=auth_method)
                    flash(_("User not found. Please contact an administrator."), "error")
                    return render_template(
                        "auth/login.html",
                        allow_self_register=Config.ALLOW_SELF_REGISTER,
                        auth_method=auth_method,
                        requires_password=requires_password,
                    )
            else:
                # If existing user matches admin usernames, ensure admin role
                if username in admin_usernames and user.role != "admin":
                    user.role = "admin"
                    if not safe_commit("promote_admin_user", {"username": username}):
                        current_app.logger.error("Failed to promote '%s' to admin due to DB error", username)
                        flash(_("Could not update your account role due to a database error."), "error")
                        return render_template(
                            "auth/login.html",
                            allow_self_register=Config.ALLOW_SELF_REGISTER,
                            auth_method=auth_method,
                            requires_password=requires_password,
                        )

            # Check if user is active
            if not user.is_active:
                log_event("auth.login_failed", user_id=user.id, reason="account_disabled", auth_method=auth_method)
                flash(_("Account is disabled. Please contact an administrator."), "error")
                return render_template(
                    "auth/login.html",
                    allow_self_register=Config.ALLOW_SELF_REGISTER,
                    auth_method=auth_method,
                    requires_password=requires_password,
                )

            # Handle password authentication based on mode
            if requires_password:
                # Password authentication is required
                if user.has_password:
                    # User has password set - verify it
                    if not password:
                        log_event(
                            "auth.login_failed", user_id=user.id, reason="password_required", auth_method=auth_method
                        )
                        flash(_("Password is required"), "error")
                        return render_template(
                            "auth/login.html",
                            allow_self_register=Config.ALLOW_SELF_REGISTER,
                            auth_method=auth_method,
                            requires_password=requires_password,
                        )

                    if not user.check_password(password):
                        log_event(
                            "auth.login_failed", user_id=user.id, reason="invalid_password", auth_method=auth_method
                        )
                        flash(_("Invalid username or password"), "error")
                        return render_template(
                            "auth/login.html",
                            allow_self_register=Config.ALLOW_SELF_REGISTER,
                            auth_method=auth_method,
                            requires_password=requires_password,
                        )
                else:
                    # User doesn't have password set - prompt to set one
                    log_event("auth.login_failed", user_id=user.id, reason="no_password_set", auth_method=auth_method)
                    flash(
                        _("No password is set for your account. Please set a password in your profile to continue."),
                        "error",
                    )
                    # Still log them in so they can set password in profile
                    login_user(user, remember=True)
                    return redirect(url_for("auth.edit_profile"))

            # For 'none' mode, no password check needed - just log in
            # Log in the user
            login_user(user, remember=True)
            user.update_last_login()
            current_app.logger.info("User '%s' logged in successfully", user.username)

            # Track successful login
            log_event("auth.login", user_id=user.id, auth_method=auth_method)
            track_event(user.id, "auth.login", {"auth_method": auth_method})

            # Identify user with comprehensive segmentation properties
            identify_user_with_segments(user.id, user)

            # Set super properties (included in all events)
            set_super_properties(user.id, user)

            # Redirect to intended page or dashboard
            next_page = request.args.get("next")
            if not next_page or not next_page.startswith("/"):
                next_page = url_for("main.dashboard")
            current_app.logger.info("Redirecting '%s' to %s", user.username, next_page)

            flash(_("Welcome back, %(username)s!", username=user.username), "success")
            return redirect(next_page)
        except Exception as e:
            current_app.logger.exception("Login error: %s", e)
            flash(_("Unexpected error during login. Please try again or check server logs."), "error")
            return render_template(
                "auth/login.html",
                allow_self_register=Config.ALLOW_SELF_REGISTER,
                auth_method=auth_method,
                requires_password=requires_password,
            )

    return render_template(
        "auth/login.html",
        allow_self_register=Config.ALLOW_SELF_REGISTER,
        auth_method=auth_method,
        requires_password=requires_password,
    )


@auth_bp.route("/logout")
@login_required
def logout():
    """Logout the current user"""
    username = current_user.username
    user_id = current_user.id

    # Track logout event before logging out
    log_event("auth.logout", user_id=user_id)
    track_event(user_id, "auth.logout", {})

    # Try OIDC end-session if enabled and configured
    try:
        auth_method = (getattr(Config, "AUTH_METHOD", "local") or "local").strip().lower()
    except Exception:
        auth_method = "local"

    id_token = session.pop("oidc_id_token", None)
    logout_user()
    # Ensure both possible session keys are cleared for compatibility
    try:
        session.pop("_user_id", None)
        session.pop("user_id", None)
    except Exception:
        pass
    flash(_("Goodbye, %(username)s!", username=username), "info")

    if auth_method in ("oidc", "both"):
        # Only perform RP-Initiated Logout if OIDC_POST_LOGOUT_REDIRECT_URI is explicitly configured
        post_logout = getattr(Config, "OIDC_POST_LOGOUT_REDIRECT_URI", None)
        if post_logout:
            client = oauth.create_client("oidc")
            if client:
                try:
                    # Build end-session URL if provider supports it
                    metadata = client.load_server_metadata()
                    end_session_endpoint = metadata.get("end_session_endpoint") or metadata.get("revocation_endpoint")
                    if end_session_endpoint:
                        params = {}
                        if id_token:
                            params["id_token_hint"] = id_token
                        params["post_logout_redirect_uri"] = post_logout
                        from urllib.parse import urlencode

                        return redirect(f"{end_session_endpoint}?{urlencode(params)}")
                except Exception:
                    pass

    return redirect(url_for("auth.login"))


@auth_bp.route("/profile")
@login_required
def profile():
    """User profile page"""
    return render_template("auth/profile.html")


@auth_bp.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    """Edit user profile"""
    # Get authentication method to determine if password fields should be shown
    try:
        auth_method = (getattr(Config, "AUTH_METHOD", "local") or "local").strip().lower()
    except Exception:
        auth_method = "local"

    requires_password = auth_method in ("local", "both")

    if request.method == "POST":
        # Update real name if provided
        full_name = request.form.get("full_name", "").strip()
        current_user.full_name = full_name or None
        # Update preferred language
        preferred_language = (request.form.get("preferred_language") or "").strip().lower()
        available = (current_app.config.get("LANGUAGES") or {}).keys()
        if preferred_language in available:
            current_user.preferred_language = preferred_language
            # Also set session so it applies immediately
            session["preferred_language"] = preferred_language

        # Handle password update if password auth is required
        if requires_password:
            password = request.form.get("password", "").strip()
            password_confirm = request.form.get("password_confirm", "").strip()

            if password:
                # Validate password
                if len(password) < 8:
                    flash(_("Password must be at least 8 characters long."), "error")
                    return redirect(url_for("auth.edit_profile"))

                if password != password_confirm:
                    flash(_("Passwords do not match."), "error")
                    return redirect(url_for("auth.edit_profile"))

                # Set the new password
                current_user.set_password(password)
                current_app.logger.info("User '%s' updated password", current_user.username)

        # Handle avatar upload if provided
        try:
            file = request.files.get("avatar")
        except Exception:
            file = None

        if file and getattr(file, "filename", ""):
            filename = file.filename
            if not allowed_avatar_file(filename):
                flash(_("Invalid avatar file type. Allowed: PNG, JPG, JPEG, GIF, WEBP"), "error")
                return redirect(url_for("auth.edit_profile"))
            # Validate image content with Pillow
            try:
                from PIL import Image

                file.stream.seek(0)
                img = Image.open(file.stream)
                img.verify()
                file.stream.seek(0)
            except Exception:
                flash(_("Invalid image file."), "error")
                return redirect(url_for("auth.edit_profile"))

            # Generate unique filename and save
            import uuid
            import os

            ext = filename.rsplit(".", 1)[1].lower()
            unique_name = f"avatar_{current_user.id}_{uuid.uuid4().hex[:8]}.{ext}"
            folder = get_avatar_upload_folder()
            file_path = os.path.join(folder, unique_name)
            try:
                file.save(file_path)
            except Exception:
                flash(_("Failed to save avatar on server."), "error")
                return redirect(url_for("auth.edit_profile"))

            # Remove old avatar if exists
            try:
                old_filename = getattr(current_user, "avatar_filename", None)
                if old_filename:
                    old_path = os.path.join(folder, old_filename)
                    if os.path.exists(old_path):
                        try:
                            os.remove(old_path)
                        except OSError:
                            pass
            except Exception:
                pass

            current_user.avatar_filename = unique_name
        try:
            db.session.commit()
            flash(_("Profile updated successfully"), "success")
        except Exception:
            db.session.rollback()
            flash(_("Could not update your profile due to a database error."), "error")
        return redirect(url_for("auth.profile"))

    return render_template("auth/edit_profile.html", requires_password=requires_password)


@auth_bp.route("/profile/avatar/remove", methods=["POST"])
@login_required
def remove_avatar():
    """Remove the current user's avatar file and clear the field."""
    try:
        import os

        folder = get_avatar_upload_folder()
        if current_user.avatar_filename:
            path = os.path.join(folder, current_user.avatar_filename)
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass
        current_user.avatar_filename = None
        db.session.commit()
        flash(_("Avatar removed"), "success")
    except Exception:
        db.session.rollback()
        flash(_("Failed to remove avatar."), "error")
    return redirect(url_for("auth.edit_profile"))


# Public route to serve uploaded avatars from the static uploads directory
@auth_bp.route("/uploads/avatars/<path:filename>")
def serve_uploaded_avatar(filename):
    folder = get_avatar_upload_folder()
    return send_from_directory(folder, filename)


@auth_bp.route("/profile/theme", methods=["POST"])
@login_required
def update_theme_preference():
    """Persist user theme preference (light|dark|system)."""
    try:
        value = (request.json.get("theme") if request.is_json else request.form.get("theme") or "").strip().lower()
    except Exception:
        value = (request.form.get("theme") or "").strip().lower()

    if value not in ("light", "dark", "system"):
        return ({"error": "invalid theme value"}, 400)

    # Store None for system to allow fallback to system preference
    current_user.theme_preference = None if value == "system" else value
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return ({"error": "failed to save preference"}, 500)

    return ({"ok": True, "theme": value}, 200)


# --- OIDC placeholders (optional integration) ---
@auth_bp.route("/login/oidc")
def login_oidc():
    """Start OIDC login using Authlib."""
    try:
        auth_method = (getattr(Config, "AUTH_METHOD", "local") or "local").strip().lower()
    except Exception:
        auth_method = "local"

    if auth_method not in ("oidc", "both"):
        return redirect(url_for("auth.login"))

    client = oauth.create_client("oidc")
    if not client:
        flash(_("Single Sign-On is not configured yet. Please contact an administrator."), "warning")
        return redirect(url_for("auth.login"))

    # Preserve next redirect
    next_page = request.args.get("next")
    if next_page and next_page.startswith("/"):
        session["oidc_next"] = next_page

    # Determine redirect URI
    redirect_uri = getattr(Config, "OIDC_REDIRECT_URI", None) or url_for("auth.oidc_callback", _external=True)
    # Trigger authorization code flow (with PKCE via client_kwargs)
    return client.authorize_redirect(redirect_uri)


@auth_bp.route("/auth/oidc/callback")
def oidc_callback():
    """Handle OIDC callback: exchange code, map claims, upsert user, log them in."""
    client = oauth.create_client("oidc")
    if not client:
        flash(_("Single Sign-On is not configured."), "error")
        return redirect(url_for("auth.login"))

    try:
        # Exchange authorization code for tokens
        current_app.logger.info("OIDC callback: Starting token exchange")
        token = client.authorize_access_token()
        current_app.logger.info(
            "OIDC callback: Token exchange successful, token keys: %s",
            list(token.keys()) if isinstance(token, dict) else "not-a-dict",
        )

        # Log raw token structure (mask sensitive data)
        if isinstance(token, dict):
            token_info = {
                k: (v[:20] + "..." if isinstance(v, str) and len(v) > 20 else v)
                for k, v in token.items()
                if k not in ["access_token", "id_token", "refresh_token"]
            }
            current_app.logger.debug("OIDC callback: Token info: %s", token_info)

        # Parse ID token claims
        claims = {}
        id_token_parsed = False
        try:
            current_app.logger.info("OIDC callback: Attempting to parse ID token")
            # Authlib already validates and parses the ID token during authorize_access_token()
            # The parsed claims should be available in the token dict under 'userinfo' key
            if isinstance(token, dict) and "userinfo" in token:
                claims = token.get("userinfo", {})
                id_token_parsed = True
                current_app.logger.info(
                    "OIDC callback: ID token claims available from token, claims keys: %s", list(claims.keys())
                )
            else:
                # If not available, parse it manually with nonce from session
                # Authlib stores the nonce in session during authorize_redirect()
                nonce = session.get("_oidc_authlib_nonce_")
                current_app.logger.debug("OIDC callback: Nonce from session: %s", "present" if nonce else "missing")
                parsed = client.parse_id_token(token, nonce=nonce)
                if parsed:
                    claims = parsed
                    id_token_parsed = True
                    current_app.logger.info(
                        "OIDC callback: ID token parsed successfully, claims keys: %s", list(claims.keys())
                    )
                else:
                    current_app.logger.warning("OIDC callback: parse_id_token returned None/empty")
        except Exception as e:
            current_app.logger.error("OIDC callback: Failed to parse ID token: %s - %s", type(e).__name__, str(e))
            # Try to decode the token manually to debug
            try:
                if isinstance(token, dict) and "id_token" in token:
                    import jwt

                    # Decode without verification to inspect claims (for debugging only)
                    unverified = jwt.decode(token["id_token"], options={"verify_signature": False})
                    current_app.logger.info("OIDC callback: Unverified ID token claims: %s", list(unverified.keys()))
                    current_app.logger.debug("OIDC callback: Unverified token content: %s", unverified)
            except Exception as decode_err:
                current_app.logger.error("OIDC callback: Could not decode ID token for debugging: %s", str(decode_err))

        # Fetch userinfo endpoint as fallback or supplement
        userinfo = {}
        userinfo_fetched = False
        try:
            current_app.logger.info("OIDC callback: Fetching userinfo endpoint")
            fetched = client.userinfo(token=token)
            if fetched:
                userinfo = fetched
                userinfo_fetched = True
                current_app.logger.info("OIDC callback: Userinfo fetched successfully, keys: %s", list(userinfo.keys()))
                # If ID token parsing failed but userinfo succeeded, use userinfo for critical fields
                if not id_token_parsed and userinfo:
                    current_app.logger.warning(
                        "OIDC callback: ID token parsing failed, using userinfo as primary source"
                    )
                    claims = userinfo
            else:
                current_app.logger.warning("OIDC callback: userinfo endpoint returned None/empty")
        except Exception as e:
            current_app.logger.error("OIDC callback: Failed to fetch userinfo: %s - %s", type(e).__name__, str(e))

        # Resolve fields from claims/userinfo
        issuer = (claims.get("iss") or userinfo.get("iss") or "").strip()
        sub = (claims.get("sub") or userinfo.get("sub") or "").strip()

        username_claim = getattr(Config, "OIDC_USERNAME_CLAIM", "preferred_username")
        full_name_claim = getattr(Config, "OIDC_FULL_NAME_CLAIM", "name")
        email_claim = getattr(Config, "OIDC_EMAIL_CLAIM", "email")
        groups_claim = getattr(Config, "OIDC_GROUPS_CLAIM", "groups")

        current_app.logger.info(
            "OIDC callback: Looking for claims - username:%s, email:%s, full_name:%s, groups:%s",
            username_claim,
            email_claim,
            full_name_claim,
            groups_claim,
        )

        username = (claims.get(username_claim) or userinfo.get(username_claim) or "").strip().lower()
        email = claims.get(email_claim) or userinfo.get(email_claim) or None
        if email:
            email = email.strip().lower()
        full_name = claims.get(full_name_claim) or userinfo.get(full_name_claim) or None
        if isinstance(full_name, str):
            full_name = full_name.strip()

        groups = userinfo.get(groups_claim) or claims.get(groups_claim) or []
        if isinstance(groups, str):
            groups = [groups]

        current_app.logger.info(
            "OIDC callback: Extracted values - issuer:%s, sub:%s, username:%s, email:%s, groups:%s",
            issuer[:30] if issuer else "empty",
            sub[:20] if sub else "empty",
            username or "empty",
            email or "empty",
            len(groups) if isinstance(groups, list) else "not-list",
        )

        if not issuer or not sub:
            current_app.logger.error(
                "OIDC callback missing issuer/sub - issuer:'%s' sub:'%s' - ID token parsed:%s, userinfo fetched:%s, claims keys:%s, userinfo keys:%s",
                issuer,
                sub,
                id_token_parsed,
                userinfo_fetched,
                list(claims.keys()),
                list(userinfo.keys()),
            )
            flash(
                _("Authentication failed: missing issuer or subject claim. Please check OIDC configuration."), "error"
            )
            return redirect(url_for("auth.login"))

        # Determine a fallback username if not provided
        if not username:
            if email and "@" in email:
                username = email.split("@", 1)[0]
            else:
                username = f"user-{sub[-8:]}"

        # Find or create user
        user = User.query.filter_by(oidc_issuer=issuer, oidc_sub=sub).first()

        if not user and email:
            # Attempt match by email
            user = User.query.filter_by(email=email).first()

        if not user:
            # Attempt match by username
            user = User.query.filter_by(username=username).first()

        if not user:
            # Create if allowed
            if not Config.ALLOW_SELF_REGISTER:
                flash(_("User account does not exist and self-registration is disabled."), "error")
                return redirect(url_for("auth.login"))
            role = "user"
            try:
                user = User(username=username, role=role, email=email, full_name=full_name)
                user.is_active = True
                user.oidc_issuer = issuer
                user.oidc_sub = sub
                db.session.add(user)
                if not safe_commit("oidc_create_user", {"username": username, "email": email}):
                    raise RuntimeError("db commit failed on user create")

                # Track onboarding started for new OIDC user
                track_onboarding_started(
                    user.id,
                    {
                        "auth_method": "oidc",
                        "self_registered": True,
                        "is_admin": role == "admin",
                        "has_email": bool(email),
                    },
                )

                flash(_("Welcome! Your account has been created."), "success")
            except Exception as e:
                current_app.logger.exception("Failed to create user from OIDC claims: %s", e)
                flash(_("Could not create your account due to a database error."), "error")
                return redirect(url_for("auth.login"))
        else:
            # Update linkage and profile fields
            changed = False
            if not user.oidc_issuer or not user.oidc_sub:
                user.oidc_issuer = issuer
                user.oidc_sub = sub
                changed = True
            # Update profile fields when provided
            if email and user.email != email:
                user.email = email
                changed = True
            if full_name and user.full_name != full_name:
                user.full_name = full_name
                changed = True
            if changed:
                if not safe_commit("oidc_update_user", {"user_id": user.id}):
                    current_app.logger.warning("DB commit failed updating user from OIDC; continuing")

        # Admin role mapping based on configured group or emails
        try:
            admin_set = False
            admin_group = getattr(Config, "OIDC_ADMIN_GROUP", None)
            admin_emails = getattr(Config, "OIDC_ADMIN_EMAILS", []) or []
            if admin_group and isinstance(groups, (list, tuple)) and admin_group in groups and user.role != "admin":
                user.role = "admin"
                admin_set = True
            if email and email in [e.strip().lower() for e in admin_emails] and user.role != "admin":
                user.role = "admin"
                admin_set = True
            if admin_set:
                if not safe_commit("oidc_promote_admin", {"user_id": user.id}):
                    current_app.logger.warning("DB commit failed promoting user to admin from OIDC; continuing")
        except Exception:
            pass

        # Check if user is active
        if not user.is_active:
            flash(_("Account is disabled. Please contact an administrator."), "error")
            return redirect(url_for("auth.login"))

        # Persist id_token for possible end-session
        try:
            if isinstance(token, dict) and token.get("id_token"):
                session["oidc_id_token"] = token.get("id_token")
        except Exception:
            pass

        # Login
        login_user(user, remember=True)
        try:
            user.update_last_login()
        except Exception:
            pass

        # Track successful OIDC login
        log_event("auth.login", user_id=user.id, auth_method="oidc")
        track_event(user.id, "auth.login", {"auth_method": "oidc"})

        # Identify user with comprehensive segmentation properties
        identify_user_with_segments(user.id, user)

        # Set super properties (included in all events)
        set_super_properties(user.id, user)

        # Redirect to intended page or dashboard
        next_page = session.pop("oidc_next", None) or request.args.get("next")
        if not next_page or not next_page.startswith("/"):
            next_page = url_for("main.dashboard")
        flash(_("Welcome back, %(username)s!", username=user.username), "success")
        return redirect(next_page)

    except Exception as e:
        current_app.logger.exception("OIDC callback error: %s", e)
        flash(_("Unexpected error during SSO login. Please try again or contact support."), "error")
        return redirect(url_for("auth.login"))
