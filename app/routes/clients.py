from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify, Response, make_response
from flask_babel import gettext as _
from flask_login import login_required, current_user
import app as app_module
from app import db, log_event, track_event
from app.models import Client, Project, Contact, TimeEntry, CustomFieldDefinition, ClientAttachment, Settings
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from app.utils.db import safe_commit
from app.utils.permissions import admin_or_permission_required
from app.utils.timezone import convert_app_datetime_to_user
from app.utils.email import send_client_portal_password_setup_email
from app.utils.module_registry import ModuleRegistry
from app.services.client_service import ClientService
from sqlalchemy.orm import joinedload
from sqlalchemy import or_
import csv
import io
import json

_client_service = ClientService()

clients_bp = Blueprint("clients", __name__)


def _wants_json_response() -> bool:
    try:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return True
        if request.is_json:
            return True
        return request.accept_mimetypes["application/json"] > request.accept_mimetypes["text/html"]
    except Exception:
        return False


@clients_bp.before_request
def _enforce_clients_module():
    """When Clients is disabled, allow admins only; block non-admin access."""
    if not current_user or not getattr(current_user, "is_authenticated", False):
        # Let @login_required handle unauthenticated access.
        return None

    settings = Settings.get_settings()
    if ModuleRegistry.is_enabled("clients", settings, current_user):
        return None

    # Non-admin users: block access. For AJAX/JSON requests, return JSON; otherwise redirect.
    if _wants_json_response():
        return jsonify(
            {"error": "module_disabled", "message": _("Clients module is disabled by the administrator.")}
        ), 403

    flash(_("Clients module is disabled by the administrator."), "warning")
    return redirect(url_for("main.dashboard"))


@clients_bp.route("/clients")
@login_required
def list_clients():
    """List all clients"""
    status = request.args.get("status", "active")
    search = request.args.get("search", "").strip()

    # Validate search input with length limits
    from app.utils.validation import sanitize_input
    if search:
        # Limit search input to prevent long queries and potential DoS
        search = sanitize_input(search, max_length=200)
        if len(search) > 200:
            flash(_("Search query is too long. Maximum 200 characters."), "warning")
            search = search[:200]

    query = Client.query
    if status == "active":
        query = query.filter_by(status="active")
    elif status == "inactive":
        query = query.filter_by(status="inactive")

    # Determine database type for search strategy
    is_postgres = False
    try:
        from sqlalchemy import inspect
        engine = db.engine
        is_postgres = 'postgresql' in str(engine.url).lower()
    except Exception:
        pass

    if search:
        # Escape special LIKE characters to prevent SQL injection
        # Note: SQLAlchemy parameterized queries already protect against SQL injection,
        # but we still escape % and _ for LIKE patterns to get expected search behavior
        search_escaped = search.replace('%', '\\%').replace('_', '\\_')
        like = f"%{search_escaped}%"
        search_conditions = [
            Client.name.ilike(like),
            Client.description.ilike(like),
            Client.contact_person.ilike(like),
            Client.email.ilike(like),
        ]
        
        # Add custom fields to search based on database type
        if is_postgres:
            # PostgreSQL: Use JSONB operators for efficient search
            try:
                from sqlalchemy import cast, String
                active_definitions = CustomFieldDefinition.get_active_definitions()
                for definition in active_definitions:
                    # PostgreSQL JSONB path query: custom_fields->>'field_key' ILIKE pattern
                    search_conditions.append(
                        db.cast(Client.custom_fields[definition.field_key].astext, String).ilike(like)
                    )
            except Exception as e:
                # If JSONB search fails, log and continue without custom field search in DB
                current_app.logger.warning(f"Could not add JSONB search conditions: {e}")
        
        query = query.filter(db.or_(*search_conditions))

    clients = query.order_by(Client.name).all()
    
    # For SQLite and other non-PostgreSQL databases, filter by custom fields in Python
    # (PostgreSQL already handles this in the query above)
    if search and not is_postgres:
        try:
            search_lower = search.lower()
            filtered_clients = []
            active_definitions = CustomFieldDefinition.get_active_definitions()
            
            for client in clients:
                # Check if matches standard fields (already in results) or custom fields
                matched_standard = any([
                    (client.name and search_lower in client.name.lower()),
                    (client.description and search_lower in (client.description or "").lower()),
                    (client.contact_person and search_lower in (client.contact_person or "").lower()),
                    (client.email and search_lower in (client.email or "").lower()),
                ])
                
                matched_custom = False
                if client.custom_fields:
                    for definition in active_definitions:
                        field_value = client.custom_fields.get(definition.field_key)
                        if field_value and search_lower in str(field_value).lower():
                            matched_custom = True
                            break
                
                if matched_standard or matched_custom:
                    filtered_clients.append(client)
            
            clients = filtered_clients
        except Exception:
            # If filtering fails, just use the original results
            pass

    # Get custom field definitions for the template
    custom_field_definitions = CustomFieldDefinition.get_active_definitions()
    
    # Get link templates for custom fields (for clickable values)
    from app.models import LinkTemplate
    from sqlalchemy.exc import ProgrammingError
    link_templates_by_field = {}
    try:
        for template in LinkTemplate.get_active_templates():
            link_templates_by_field[template.field_key] = template
    except ProgrammingError as e:
        # Handle case where link_templates table doesn't exist (migration not run)
        if "does not exist" in str(e.orig) or "relation" in str(e.orig).lower():
            current_app.logger.warning(
                "link_templates table does not exist. Run migration: flask db upgrade"
            )
            link_templates_by_field = {}
        else:
            raise

    # Check if this is an AJAX request
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        # Return only the clients list HTML for AJAX requests
        response = make_response(render_template(
            "clients/_clients_list.html",
            clients=clients,
            status=status,
            search=search,
            custom_field_definitions=custom_field_definitions,
            link_templates_by_field=link_templates_by_field,
        ))
        response.headers["Content-Type"] = "text/html; charset=utf-8"
        return response

    return render_template("clients/list.html", clients=clients, status=status, search=search, custom_field_definitions=custom_field_definitions, link_templates_by_field=link_templates_by_field)


@clients_bp.route("/clients/create", methods=["GET", "POST"])
@login_required
def create_client():
    """Create a new client"""
    # Detect AJAX/JSON request while preserving classic form behavior
    try:
        # Consider classic HTML forms regardless of Accept header
        is_classic_form = request.mimetype in ("application/x-www-form-urlencoded", "multipart/form-data")
    except Exception:
        is_classic_form = False

    try:
        wants_json = (
            request.headers.get("X-Requested-With") == "XMLHttpRequest"
            or request.is_json
            or (
                not is_classic_form
                and (request.accept_mimetypes["application/json"] > request.accept_mimetypes["text/html"])
            )
        )
    except Exception:
        wants_json = False

    # Check permissions
    if not current_user.is_admin and not current_user.has_permission("create_clients"):
        if wants_json:
            return jsonify({"error": "forbidden", "message": _("You do not have permission to create clients")}), 403
        flash(_("You do not have permission to create clients"), "error")
        return redirect(url_for("clients.list_clients"))

    if request.method == "POST":
        from app.utils.validation import sanitize_input, validate_email as validate_email_format

        name = sanitize_input(request.form.get("name", "").strip(), max_length=200)
        description = sanitize_input(request.form.get("description", "").strip(), max_length=2000)
        contact_person = sanitize_input(request.form.get("contact_person", "").strip(), max_length=200)
        email = request.form.get("email", "").strip()
        phone = sanitize_input(request.form.get("phone", "").strip(), max_length=50)
        address = sanitize_input(request.form.get("address", "").strip(), max_length=500)
        default_hourly_rate = request.form.get("default_hourly_rate", "").strip()
        prepaid_hours_input = request.form.get("prepaid_hours_monthly", "").strip()
        prepaid_reset_day_input = request.form.get("prepaid_reset_day", "").strip()
        try:
            current_app.logger.info(
                "POST /clients/create user=%s name=%s email=%s",
                current_user.username,
                name or "<empty>",
                email or "<empty>",
            )
        except Exception:
            pass

        # Validate required fields
        if not name:
            if wants_json:
                return jsonify({"error": "validation_error", "messages": ["Client name is required"]}), 400
            flash(_("Client name is required"), "error")
            try:
                current_app.logger.warning("Validation failed: missing client name")
            except Exception:
                pass
            return render_template("clients/create.html")

        # Check if client name already exists
        if _client_service.get_by_name(name):
            if wants_json:
                return (
                    jsonify({"error": "validation_error", "messages": ["A client with this name already exists"]}),
                    400,
                )
            flash(_("A client with this name already exists"), "error")
            try:
                current_app.logger.warning("Validation failed: duplicate client name '%s'", name)
            except Exception:
                pass
            return render_template("clients/create.html")

        # Validate email format if provided
        if email:
            try:
                email = validate_email_format(email)
            except Exception:
                if wants_json:
                    return jsonify({"error": "validation_error", "messages": ["Invalid email address"]}), 400
                flash(_("Invalid email address"), "error")
                return render_template("clients/create.html")

        # Validate hourly rate
        try:
            default_hourly_rate = Decimal(default_hourly_rate) if default_hourly_rate else None
        except (InvalidOperation, ValueError):
            if wants_json:
                return jsonify({"error": "validation_error", "messages": ["Invalid hourly rate format"]}), 400
            flash(_("Invalid hourly rate format"), "error")
            try:
                current_app.logger.warning("Validation failed: invalid hourly rate '%s'", default_hourly_rate)
            except Exception:
                pass
            return render_template("clients/create.html")

        try:
            prepaid_hours_monthly = Decimal(prepaid_hours_input) if prepaid_hours_input else None
            if prepaid_hours_monthly is not None and prepaid_hours_monthly < 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            message = _("Prepaid hours must be a positive number.")
            if wants_json:
                return jsonify({"error": "validation_error", "messages": [message]}), 400
            flash(message, "error")
            return render_template("clients/create.html")

        try:
            prepaid_reset_day = int(prepaid_reset_day_input) if prepaid_reset_day_input else 1
        except ValueError:
            prepaid_reset_day = 1

        if prepaid_reset_day < 1 or prepaid_reset_day > 28:
            message = _("Prepaid reset day must be between 1 and 28.")
            if wants_json:
                return jsonify({"error": "validation_error", "messages": [message]}), 400
            flash(message, "error")
            return render_template("clients/create.html")

        # Parse custom fields from global definitions
        # Format: custom_field_<field_key> = value
        custom_fields = {}
        active_definitions = CustomFieldDefinition.get_active_definitions()
        
        for definition in active_definitions:
            field_value = request.form.get(f"custom_field_{definition.field_key}", "").strip()
            if field_value:
                custom_fields[definition.field_key] = field_value
            elif definition.is_mandatory:
                # Validate mandatory fields
                if wants_json:
                    return jsonify({"error": "validation_error", "messages": [_("Custom field '%(field)s' is required", field=definition.label)]}), 400
                flash(_("Custom field '%(field)s' is required", field=definition.label), "error")
                return render_template("clients/create.html", custom_field_definitions=active_definitions)

        # Create client
        client = Client(
            name=name,
            description=description,
            contact_person=contact_person,
            email=email,
            phone=phone,
            address=address,
            default_hourly_rate=default_hourly_rate,
            prepaid_hours_monthly=prepaid_hours_monthly,
            prepaid_reset_day=prepaid_reset_day,
        )
        if custom_fields:
            client.custom_fields = custom_fields

        db.session.add(client)
        if not safe_commit("create_client", {"name": name}):
            if wants_json:
                return (
                    jsonify({"error": "db_error", "message": "Could not create client due to a database error."}),
                    500,
                )
            flash(_("Could not create client due to a database error. Please check server logs."), "error")
            return render_template("clients/create.html")

        # Log client creation
        app_module.log_event("client.created", user_id=current_user.id, client_id=client.id)
        app_module.track_event(current_user.id, "client.created", {"client_id": client.id})

        # Invalidate dashboard cache so single-client state updates (Issue #467)
        try:
            from app.utils.cache import get_cache
            cache = get_cache()
            if cache:
                cache.delete(f"dashboard:{current_user.id}")
        except Exception:
            pass

        if wants_json:
            return (
                jsonify(
                    {
                        "id": client.id,
                        "name": client.name,
                        "default_hourly_rate": (
                            float(client.default_hourly_rate) if client.default_hourly_rate is not None else None
                        ),
                        "prepaid_hours_monthly": (
                            float(client.prepaid_hours_monthly) if client.prepaid_hours_monthly is not None else None
                        ),
                        "prepaid_reset_day": client.prepaid_reset_day,
                    }
                ),
                201,
            )

        flash(f'Client "{name}" created successfully', "success")
        return redirect(url_for("clients.view_client", client_id=client.id))

    # Load active custom field definitions for the form
    custom_field_definitions = CustomFieldDefinition.get_active_definitions()
    return render_template("clients/create.html", custom_field_definitions=custom_field_definitions)


@clients_bp.route("/clients/<int:client_id>")
@login_required
def view_client(client_id):
    """View client details and projects"""
    client = Client.query.get_or_404(client_id)

    # Get projects for this client
    projects = Project.query.filter_by(client_id=client.id).order_by(Project.name).all()

    # Get contacts for this client (if CRM tables exist)
    contacts = []
    primary_contact = None
    try:
        from app.models import Contact

        contacts = Contact.get_active_contacts(client_id)
        primary_contact = Contact.get_primary_contact(client_id)
    except Exception as e:
        # CRM tables might not exist yet if migration 063 hasn't run
        current_app.logger.warning(f"Could not load contacts for client {client_id}: {e}")
        contacts = []
        primary_contact = None

    prepaid_overview = None
    if client.prepaid_plan_enabled:
        today = datetime.utcnow()
        month_start = client.prepaid_month_start(today)
        consumed_hours = client.get_prepaid_consumed_hours(month_start).quantize(Decimal("0.01"))
        remaining_hours = client.get_prepaid_remaining_hours(month_start).quantize(Decimal("0.01"))
        prepaid_overview = {
            "month_start": month_start,
            "month_label": month_start.strftime("%Y-%m-%d") if month_start else "",
            "plan_hours": float(client.prepaid_hours_decimal),
            "consumed_hours": float(consumed_hours),
            "remaining_hours": float(remaining_hours),
        }

    # Get link templates for custom fields (for clickable values)
    from app.models import LinkTemplate
    from sqlalchemy.exc import ProgrammingError
    link_templates_by_field = {}
    try:
        for template in LinkTemplate.get_active_templates():
            link_templates_by_field[template.field_key] = template
    except ProgrammingError as e:
        # Handle case where link_templates table doesn't exist (migration not run)
        if "does not exist" in str(e.orig) or "relation" in str(e.orig).lower():
            current_app.logger.warning(
                "link_templates table does not exist. Run migration: flask db upgrade"
            )
            link_templates_by_field = {}
        else:
            raise

    # Get custom field definitions for friendly names
    custom_field_definitions_by_key = {}
    try:
        for definition in CustomFieldDefinition.get_active_definitions():
            custom_field_definitions_by_key[definition.field_key] = definition
    except ProgrammingError as e:
        # Handle case where custom_field_definitions table doesn't exist (migration not run)
        if "does not exist" in str(e.orig) or "relation" in str(e.orig).lower():
            current_app.logger.warning(
                "custom_field_definitions table does not exist. Run migration: flask db upgrade"
            )
            custom_field_definitions_by_key = {}
        else:
            raise

    # Get recent time entries for this client
    # Include entries directly linked to client and entries through projects
    project_ids = [p.id for p in projects]
    
    # Query time entries: either directly linked to client or through client's projects
    conditions = [TimeEntry.client_id == client.id]  # Direct client entries
    
    if project_ids:
        conditions.append(TimeEntry.project_id.in_(project_ids))  # Project entries
    
    time_entries_query = TimeEntry.query.filter(
        TimeEntry.end_time.isnot(None)  # Only completed entries
    ).filter(
        or_(*conditions)
    ).options(
        joinedload(TimeEntry.user),
        joinedload(TimeEntry.project),
        joinedload(TimeEntry.task)
    ).order_by(
        TimeEntry.start_time.desc()
    ).limit(20)  # Limit to most recent 20 entries
    
    recent_time_entries = time_entries_query.all()

    # Get attachments for this client (if attachments table exists)
    attachments = []
    try:
        attachments = ClientAttachment.get_client_attachments(client_id)
    except ProgrammingError as e:
        # Handle case where client_attachments table doesn't exist (migration not run)
        if "does not exist" in str(e.orig) or "relation" in str(e.orig).lower():
            current_app.logger.warning(
                "client_attachments table does not exist. Run migration: flask db upgrade"
            )
            attachments = []
        else:
            raise
    except Exception as e:
        # Handle any other errors gracefully
        current_app.logger.warning(f"Could not load attachments for client {client_id}: {e}")
        attachments = []

    return render_template(
        "clients/view.html",
        client=client,
        projects=projects,
        contacts=contacts,
        primary_contact=primary_contact,
        prepaid_overview=prepaid_overview,
        attachments=attachments,
        recent_time_entries=recent_time_entries,
        link_templates_by_field=link_templates_by_field,
        custom_field_definitions_by_key=custom_field_definitions_by_key,
    )


@clients_bp.route("/clients/<int:client_id>/edit", methods=["GET", "POST"])
@login_required
def edit_client(client_id):
    """Edit client details"""
    client = Client.query.get_or_404(client_id)

    # Check permissions
    if not current_user.is_admin and not current_user.has_permission("edit_clients"):
        flash(_("You do not have permission to edit clients"), "error")
        return redirect(url_for("clients.view_client", client_id=client_id))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        contact_person = request.form.get("contact_person", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        default_hourly_rate = request.form.get("default_hourly_rate", "").strip()
        prepaid_hours_input = request.form.get("prepaid_hours_monthly", "").strip()
        prepaid_reset_day_input = request.form.get("prepaid_reset_day", "").strip()

        # Validate required fields
        if not name:
            flash(_("Client name is required"), "error")
            custom_field_definitions = CustomFieldDefinition.get_active_definitions()
            return render_template("clients/edit.html", client=client, custom_field_definitions=custom_field_definitions)

        # Check if client name already exists (excluding current client)
        existing = Client.query.filter_by(name=name).first()
        if existing and existing.id != client.id:
            flash(_("A client with this name already exists"), "error")
            custom_field_definitions = CustomFieldDefinition.get_active_definitions()
            return render_template("clients/edit.html", client=client, custom_field_definitions=custom_field_definitions)

        # Validate hourly rate
        try:
            default_hourly_rate = Decimal(default_hourly_rate) if default_hourly_rate else None
        except (InvalidOperation, ValueError):
            flash(_("Invalid hourly rate format"), "error")
            custom_field_definitions = CustomFieldDefinition.get_active_definitions()
            return render_template("clients/edit.html", client=client, custom_field_definitions=custom_field_definitions)

        try:
            prepaid_hours_monthly = Decimal(prepaid_hours_input) if prepaid_hours_input else None
            if prepaid_hours_monthly is not None and prepaid_hours_monthly < 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            flash(_("Prepaid hours must be a positive number."), "error")
            custom_field_definitions = CustomFieldDefinition.get_active_definitions()
            return render_template("clients/edit.html", client=client, custom_field_definitions=custom_field_definitions)

        try:
            prepaid_reset_day = (
                int(prepaid_reset_day_input) if prepaid_reset_day_input else client.prepaid_reset_day or 1
            )
        except ValueError:
            prepaid_reset_day = client.prepaid_reset_day or 1

        if prepaid_reset_day < 1 or prepaid_reset_day > 28:
            flash(_("Prepaid reset day must be between 1 and 28."), "error")
            custom_field_definitions = CustomFieldDefinition.get_active_definitions()
            return render_template("clients/edit.html", client=client, custom_field_definitions=custom_field_definitions)

        # Handle portal settings
        portal_enabled = request.form.get("portal_enabled") == "on"
        portal_issues_enabled = request.form.get("portal_issues_enabled") == "on"
        portal_username = request.form.get("portal_username", "").strip()
        portal_password = request.form.get("portal_password", "").strip()

        # Validate portal settings
        if portal_enabled:
            if not portal_username:
                flash(_("Portal username is required when enabling portal access."), "error")
                custom_field_definitions = CustomFieldDefinition.get_active_definitions()
                return render_template("clients/edit.html", client=client, custom_field_definitions=custom_field_definitions)

            # Check if portal username is already taken by another client
            existing_client = Client.query.filter_by(portal_username=portal_username).first()
            if existing_client and existing_client.id != client.id:
                flash(_("This portal username is already in use by another client."), "error")
                custom_field_definitions = CustomFieldDefinition.get_active_definitions()
                return render_template("clients/edit.html", client=client, custom_field_definitions=custom_field_definitions)

        # Parse custom fields from global definitions
        # Format: custom_field_<field_key> = value
        custom_fields = {}
        active_definitions = CustomFieldDefinition.get_active_definitions()
        
        for definition in active_definitions:
            field_value = request.form.get(f"custom_field_{definition.field_key}", "").strip()
            if field_value:
                custom_fields[definition.field_key] = field_value
            elif definition.is_mandatory:
                # Validate mandatory fields
                flash(_("Custom field '%(field)s' is required", field=definition.label), "error")
                custom_field_definitions = CustomFieldDefinition.get_active_definitions()
                return render_template("clients/edit.html", client=client, custom_field_definitions=custom_field_definitions)

        # Update client
        client.name = name
        client.description = description
        client.contact_person = contact_person
        client.email = email
        client.phone = phone
        client.address = address
        client.default_hourly_rate = default_hourly_rate
        client.prepaid_hours_monthly = prepaid_hours_monthly
        client.prepaid_reset_day = prepaid_reset_day
        client.portal_enabled = portal_enabled
        client.portal_issues_enabled = portal_issues_enabled if portal_enabled else False
        client.custom_fields = custom_fields if custom_fields else None

        # Update portal credentials
        if portal_enabled:
            client.portal_username = portal_username
            if portal_password:  # Only update password if provided
                client.set_portal_password(portal_password)
        else:
            # Disable portal - clear credentials
            client.portal_username = None
            client.portal_password_hash = None

        client.updated_at = datetime.utcnow()

        if not safe_commit("edit_client", {"client_id": client.id}):
            flash(_("Could not update client due to a database error. Please check server logs."), "error")
            return render_template("clients/edit.html", client=client)

        # Log client update
        app_module.log_event("client.updated", user_id=current_user.id, client_id=client.id)
        app_module.track_event(current_user.id, "client.updated", {"client_id": client.id})

        flash(f'Client "{name}" updated successfully', "success")
        return redirect(url_for("clients.view_client", client_id=client.id))

    # Load active custom field definitions for the form
    custom_field_definitions = CustomFieldDefinition.get_active_definitions()
    return render_template("clients/edit.html", client=client, custom_field_definitions=custom_field_definitions)


@clients_bp.route("/clients/<int:client_id>/send-portal-password-email", methods=["POST"])
@login_required
def send_portal_password_email(client_id):
    """Send password setup email to client"""
    client = Client.query.get_or_404(client_id)

    # Check permissions
    if not current_user.is_admin and not current_user.has_permission("edit_clients"):
        flash(_("You do not have permission to send portal emails"), "error")
        return redirect(url_for("clients.view_client", client_id=client_id))

    # Check if portal is enabled and username is set
    if not client.portal_enabled:
        flash(_("Client portal is not enabled for this client."), "error")
        return redirect(url_for("clients.edit_client", client_id=client_id))

    if not client.portal_username:
        flash(_("Portal username is not set for this client."), "error")
        return redirect(url_for("clients.edit_client", client_id=client_id))

    if not client.email:
        flash(_("Client email address is not set. Cannot send password setup email."), "error")
        return redirect(url_for("clients.edit_client", client_id=client_id))

    # Generate password setup token
    token = client.generate_password_setup_token(expires_hours=24)

    if not safe_commit("client_generate_password_token", {"client_id": client.id}):
        flash(_("Could not generate password setup token due to a database error."), "error")
        return redirect(url_for("clients.edit_client", client_id=client_id))

    # Send email
    try:
        # Ensure we're using latest database email settings
        from app.utils.email import reload_mail_config
        from app.models import Settings

        settings = Settings.get_settings()
        if settings.mail_enabled:
            reload_mail_config(current_app._get_current_object())

        success = send_client_portal_password_setup_email(client, token)
        if success:
            flash(_("Password setup email sent successfully to %(email)s", email=client.email), "success")
        else:
            # Check email configuration to provide better error message
            db_config = settings.get_mail_config()
            if db_config:
                mail_server = db_config.get("MAIL_SERVER")
            else:
                mail_server = current_app.config.get("MAIL_SERVER")

            if not mail_server or mail_server == "localhost":
                flash(
                    _(
                        "Email server is not configured. Please configure email settings in Admin → Email Configuration or set MAIL_SERVER environment variable."
                    ),
                    "error",
                )
            else:
                flash(
                    _(
                        "Failed to send password setup email. Please check email configuration and server logs for details."
                    ),
                    "error",
                )
    except Exception as e:
        current_app.logger.error(f"Error sending password setup email: {e}")
        flash(_("An error occurred while sending the email: %(error)s", error=str(e)), "error")

    return redirect(url_for("clients.edit_client", client_id=client_id))


@clients_bp.route("/clients/<int:client_id>/archive", methods=["POST"])
@login_required
def archive_client(client_id):
    """Archive a client"""
    client = Client.query.get_or_404(client_id)

    # Check permissions
    if not current_user.is_admin and not current_user.has_permission("edit_clients"):
        flash(_("You do not have permission to archive clients"), "error")
        return redirect(url_for("clients.view_client", client_id=client_id))

    if client.status == "inactive":
        flash(_("Client is already inactive"), "info")
    else:
        client.archive()
        db.session.commit()
        app_module.log_event("client.archived", user_id=current_user.id, client_id=client.id)
        app_module.track_event(current_user.id, "client.archived", {"client_id": client.id})
        flash(f'Client "{client.name}" archived successfully', "success")
        try:
            from app.utils.cache import get_cache
            c = get_cache()
            if c:
                c.delete(f"dashboard:{current_user.id}")
        except Exception:
            pass

    return redirect(url_for("clients.list_clients"))


@clients_bp.route("/clients/<int:client_id>/activate", methods=["POST"])
@login_required
def activate_client(client_id):
    """Activate a client"""
    client = Client.query.get_or_404(client_id)

    # Check permissions
    if not current_user.is_admin and not current_user.has_permission("edit_clients"):
        flash(_("You do not have permission to activate clients"), "error")
        return redirect(url_for("clients.view_client", client_id=client_id))

    if client.status == "active":
        flash(_("Client is already active"), "info")
    else:
        client.activate()
        db.session.commit()
        flash(f'Client "{client.name}" activated successfully', "success")
        try:
            from app.utils.cache import get_cache
            c = get_cache()
            if c:
                c.delete(f"dashboard:{current_user.id}")
        except Exception:
            pass

    return redirect(url_for("clients.list_clients"))


@clients_bp.route("/clients/<int:client_id>/delete", methods=["POST"])
@login_required
def delete_client(client_id):
    """Delete a client (only if no projects or invoices exist)"""
    from app.models.invoice import Invoice
    from app.models.client_notification import ClientNotification, ClientNotificationPreferences
    
    client = Client.query.get_or_404(client_id)

    # Check permissions
    if not current_user.is_admin and not current_user.has_permission("delete_clients"):
        flash(_("You do not have permission to delete clients"), "error")
        return redirect(url_for("clients.view_client", client_id=client_id))

    # Check if client has projects
    if client.projects.count() > 0:
        flash(_("Cannot delete client with existing projects. Please delete all projects first."), "error")
        return redirect(url_for("clients.view_client", client_id=client_id))

    # Check if client has invoices
    invoice_count = Invoice.query.filter_by(client_id=client_id).count()
    if invoice_count > 0:
        flash(_("Cannot delete client with existing invoices. Please delete all invoices first before deleting the client."), "error")
        return redirect(url_for("clients.view_client", client_id=client_id))

    client_name = client.name
    client_id_for_log = client.id
    
    # Manually delete notifications and preferences to avoid SQLAlchemy update issues
    # The database CASCADE will handle this, but we delete explicitly to prevent SQLAlchemy
    # from trying to update the foreign key to NULL
    ClientNotification.query.filter_by(client_id=client_id).delete()
    ClientNotificationPreferences.query.filter_by(client_id=client_id).delete()
    
    db.session.delete(client)
    if not safe_commit("delete_client", {"client_id": client.id}):
        flash(_("Could not delete client due to a database error. Please check server logs."), "error")
        return redirect(url_for("clients.view_client", client_id=client.id))

    # Log client deletion
    app_module.log_event("client.deleted", user_id=current_user.id, client_id=client_id_for_log)
    app_module.track_event(current_user.id, "client.deleted", {"client_id": client_id_for_log})

    try:
        from app.utils.cache import get_cache
        c = get_cache()
        if c:
            c.delete(f"dashboard:{current_user.id}")
    except Exception:
        pass

    flash(f'Client "{client_name}" deleted successfully', "success")
    return redirect(url_for("clients.list_clients"))


@clients_bp.route("/clients/bulk-delete", methods=["POST"])
@login_required
def bulk_delete_clients():
    """Delete multiple clients at once"""
    from app.models.invoice import Invoice
    from app.models.client_notification import ClientNotification, ClientNotificationPreferences
    
    # Check permissions
    if not current_user.is_admin and not current_user.has_permission("delete_clients"):
        flash(_("You do not have permission to delete clients"), "error")
        return redirect(url_for("clients.list_clients"))

    client_ids = request.form.getlist("client_ids[]")

    if not client_ids:
        flash(_("No clients selected for deletion"), "warning")
        return redirect(url_for("clients.list_clients"))

    deleted_count = 0
    skipped_count = 0
    errors = []

    for client_id_str in client_ids:
        try:
            client_id = int(client_id_str)
            client = Client.query.get(client_id)

            if not client:
                continue

            # Check for projects
            if client.projects.count() > 0:
                skipped_count += 1
                errors.append(f"'{client.name}': Has projects")
                continue

            # Check for invoices
            invoice_count = Invoice.query.filter_by(client_id=client_id).count()
            if invoice_count > 0:
                skipped_count += 1
                errors.append(f"'{client.name}': Has {invoice_count} invoice(s). Please delete all invoices first.")
                continue

            # Manually delete notifications and preferences to avoid SQLAlchemy update issues
            ClientNotification.query.filter_by(client_id=client_id).delete()
            ClientNotificationPreferences.query.filter_by(client_id=client_id).delete()

            # Delete the client
            client_id_for_log = client.id
            client_name = client.name

            db.session.delete(client)
            deleted_count += 1

            # Log the deletion
            app_module.log_event("client.deleted", user_id=current_user.id, client_id=client_id_for_log)
            app_module.track_event(current_user.id, "client.deleted", {"client_id": client_id_for_log})

        except Exception as e:
            skipped_count += 1
            errors.append(f"ID {client_id_str}: {str(e)}")

    # Commit all deletions
    if deleted_count > 0:
        if not safe_commit("bulk_delete_clients", {"count": deleted_count}):
            flash(_("Could not delete clients due to a database error. Please check server logs."), "error")
            return redirect(url_for("clients.list_clients"))

    # Show appropriate messages
    if deleted_count > 0:
        flash(f'Successfully deleted {deleted_count} client{"s" if deleted_count != 1 else ""}', "success")
        try:
            from app.utils.cache import get_cache
            c = get_cache()
            if c:
                c.delete(f"dashboard:{current_user.id}")
        except Exception:
            pass

    if skipped_count > 0:
        flash(
            f'Skipped {skipped_count} client{"s" if skipped_count != 1 else ""}: {", ".join(errors[:3])}{"..." if len(errors) > 3 else ""}',
            "warning",
        )

    if deleted_count == 0 and skipped_count == 0:
        flash(_("No clients were deleted"), "info")

    return redirect(url_for("clients.list_clients"))


@clients_bp.route("/clients/bulk-status-change", methods=["POST"])
@login_required
def bulk_status_change():
    """Change status for multiple clients at once"""
    # Check permissions
    if not current_user.is_admin and not current_user.has_permission("edit_clients"):
        flash(_("You do not have permission to change client status"), "error")
        return redirect(url_for("clients.list_clients"))

    client_ids = request.form.getlist("client_ids[]")
    new_status = request.form.get("new_status", "").strip()

    if not client_ids:
        flash(_("No clients selected"), "warning")
        return redirect(url_for("clients.list_clients"))

    if new_status not in ["active", "inactive"]:
        flash(_("Invalid status"), "error")
        return redirect(url_for("clients.list_clients"))

    updated_count = 0
    errors = []

    for client_id_str in client_ids:
        try:
            client_id = int(client_id_str)
            client = Client.query.get(client_id)

            if not client:
                continue

            # Update status
            client.status = new_status
            client.updated_at = datetime.utcnow()
            updated_count += 1

            # Log the status change
            app_module.log_event(f"client.status_changed_{new_status}", user_id=current_user.id, client_id=client.id)
            app_module.track_event(
                current_user.id, "client.status_changed", {"client_id": client.id, "new_status": new_status}
            )

        except Exception as e:
            errors.append(f"ID {client_id_str}: {str(e)}")

    # Commit all changes
    if updated_count > 0:
        if not safe_commit("bulk_status_change_clients", {"count": updated_count, "status": new_status}):
            flash(_("Could not update client status due to a database error. Please check server logs."), "error")
            return redirect(url_for("clients.list_clients"))

    # Show appropriate messages
    status_labels = {"active": "active", "inactive": "inactive"}
    if updated_count > 0:
        flash(
            f'Successfully marked {updated_count} client{"s" if updated_count != 1 else ""} as {status_labels.get(new_status, new_status)}',
            "success",
        )

    if errors:
        flash(
            f'Some clients could not be updated: {", ".join(errors[:3])}{"..." if len(errors) > 3 else ""}', "warning"
        )

    if updated_count == 0:
        flash(_("No clients were updated"), "info")

    return redirect(url_for("clients.list_clients"))


@clients_bp.route("/clients/export")
@login_required
def export_clients():
    """Export clients to CSV with custom fields and contacts"""
    status = request.args.get("status", "active")
    search = request.args.get("search", "").strip()

    query = Client.query.options(joinedload(Client.contacts))
    if status == "active":
        query = query.filter_by(status="active")
    elif status == "inactive":
        query = query.filter_by(status="inactive")

    if search:
        like = f"%{search}%"
        query = query.filter(
            db.or_(
                Client.name.ilike(like),
                Client.description.ilike(like),
                Client.contact_person.ilike(like),
                Client.email.ilike(like),
            )
        )

    clients = query.order_by(Client.name).all()

    # Collect all custom field names and determine max contacts
    all_custom_fields = set()
    max_contacts = 0
    for client in clients:
        if client.custom_fields:
            all_custom_fields.update(client.custom_fields.keys())
        contacts_count = len([c for c in client.contacts if c.is_active]) if hasattr(client, 'contacts') else 0
        max_contacts = max(max_contacts, contacts_count)

    # Sort custom fields for consistent column order
    sorted_custom_fields = sorted(all_custom_fields)

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Build header row
    header = [
        "name",
        "description",
        "contact_person",
        "email",
        "phone",
        "address",
        "default_hourly_rate",
        "status",
        "prepaid_hours_monthly",
        "prepaid_reset_day",
    ]
    
    # Add custom field columns
    for field_name in sorted_custom_fields:
        header.append(f"custom_field_{field_name}")
    
    # Add contact columns (up to max_contacts, but at least 3 slots)
    max_contact_slots = max(max_contacts, 3)
    for i in range(1, max_contact_slots + 1):
        header.extend([
            f"contact_{i}_first_name",
            f"contact_{i}_last_name",
            f"contact_{i}_email",
            f"contact_{i}_phone",
            f"contact_{i}_mobile",
            f"contact_{i}_title",
            f"contact_{i}_department",
            f"contact_{i}_role",
            f"contact_{i}_is_primary",
            f"contact_{i}_address",
            f"contact_{i}_notes",
            f"contact_{i}_tags",
        ])

    writer.writerow(header)

    # Write client data
    for client in clients:
        row = [
            client.name,
            client.description or "",
            client.contact_person or "",
            client.email or "",
            client.phone or "",
            client.address or "",
            str(client.default_hourly_rate) if client.default_hourly_rate else "",
            client.status,
            str(client.prepaid_hours_monthly) if client.prepaid_hours_monthly else "",
            str(client.prepaid_reset_day) if client.prepaid_reset_day else "",
        ]
        
        # Add custom field values
        for field_name in sorted_custom_fields:
            value = ""
            if client.custom_fields and field_name in client.custom_fields:
                value = str(client.custom_fields[field_name])
            row.append(value)
        
        # Add contacts
        active_contacts = [c for c in client.contacts if c.is_active] if hasattr(client, 'contacts') else []
        for i in range(max_contact_slots):
            if i < len(active_contacts):
                contact = active_contacts[i]
                row.extend([
                    contact.first_name or "",
                    contact.last_name or "",
                    contact.email or "",
                    contact.phone or "",
                    contact.mobile or "",
                    contact.title or "",
                    contact.department or "",
                    contact.role or "",
                    "true" if contact.is_primary else "false",
                    contact.address or "",
                    contact.notes or "",
                    contact.tags or "",
                ])
            else:
                # Empty contact slot
                row.extend([""] * 12)
        
        writer.writerow(row)

    # Create response
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename=clients_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        },
    )


@clients_bp.route("/api/clients")
@login_required
def api_clients():
    """API endpoint to get clients for dropdowns"""
    clients = Client.get_active_clients()
    return {
        "clients": [
            {
                "id": c.id,
                "name": c.name,
                "default_rate": float(c.default_hourly_rate) if c.default_hourly_rate else None,
            }
            for c in clients
        ]
    }


# Client attachment routes
@clients_bp.route("/clients/<int:client_id>/attachments/upload", methods=["POST"])
@login_required
@admin_or_permission_required("edit_clients")
def upload_client_attachment(client_id):
    """Upload an attachment to a client"""
    from werkzeug.utils import secure_filename
    from flask import send_file
    import os
    from datetime import datetime

    client = Client.query.get_or_404(client_id)

    # File upload configuration
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "pdf", "doc", "docx", "txt", "xls", "xlsx", "zip", "rar"}
    UPLOAD_FOLDER = "uploads/client_attachments"
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

    def allowed_file(filename):
        return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

    if "file" not in request.files:
        flash(_("No file provided"), "error")
        return redirect(url_for("clients.view_client", client_id=client_id))

    file = request.files["file"]
    if file.filename == "":
        flash(_("No file selected"), "error")
        return redirect(url_for("clients.view_client", client_id=client_id))

    if not allowed_file(file.filename):
        flash(_("File type not allowed"), "error")
        return redirect(url_for("clients.view_client", client_id=client_id))

    # Check file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)

    if file_size > MAX_FILE_SIZE:
        flash(_("File size exceeds maximum allowed size (10 MB)"), "error")
        return redirect(url_for("clients.view_client", client_id=client_id))

    # Save file
    original_filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{client_id}_{timestamp}_{original_filename}"

    # Ensure upload directory exists
    upload_dir = os.path.join(current_app.root_path, "..", UPLOAD_FOLDER)
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, filename)
    file.save(file_path)

    # Get file info
    mime_type = file.content_type or "application/octet-stream"
    description = request.form.get("description", "").strip() or None
    is_visible_to_client = request.form.get("is_visible_to_client", "false").lower() == "true"

    # Create attachment record
    attachment = ClientAttachment(
        client_id=client_id,
        filename=filename,
        original_filename=original_filename,
        file_path=os.path.join(UPLOAD_FOLDER, filename),
        file_size=file_size,
        uploaded_by=current_user.id,
        mime_type=mime_type,
        description=description,
        is_visible_to_client=is_visible_to_client,
    )

    db.session.add(attachment)

    try:
        if not safe_commit("upload_client_attachment", {"client_id": client_id, "attachment_id": attachment.id}):
            flash(_("Could not upload attachment due to a database error. Please check server logs."), "error")
            # Clean up uploaded file
            try:
                os.remove(file_path)
            except OSError as e:
                current_app.logger.warning(f"Failed to remove uploaded file {file_path}: {e}")
            return redirect(url_for("clients.view_client", client_id=client_id))
    except Exception as e:
        # Check if it's a table doesn't exist error
        from sqlalchemy.exc import ProgrammingError
        error_str = str(e)
        if "does not exist" in error_str or "relation" in error_str.lower() or isinstance(e, ProgrammingError):
            flash(_("The attachments feature requires a database migration. Please run: flask db upgrade"), "error")
            current_app.logger.error(f"client_attachments table does not exist. Migration required: {e}")
        else:
            flash(_("Could not upload attachment due to a database error. Please check server logs."), "error")
            current_app.logger.error(f"Error uploading client attachment: {e}")
        # Clean up uploaded file
        try:
            os.remove(file_path)
        except OSError as cleanup_error:
            current_app.logger.warning(f"Failed to remove uploaded file {file_path}: {cleanup_error}")
        return redirect(url_for("clients.view_client", client_id=client_id))

    log_event(
        "client.attachment.uploaded",
        user_id=current_user.id,
        client_id=client_id,
        attachment_id=attachment.id,
        filename=original_filename,
    )
    track_event(
        current_user.id,
        "client.attachment.uploaded",
        {"client_id": client_id, "attachment_id": attachment.id, "filename": original_filename},
    )

    flash(_("Attachment uploaded successfully"), "success")
    return redirect(url_for("clients.view_client", client_id=client_id))


@clients_bp.route("/clients/attachments/<int:attachment_id>/download")
@login_required
def download_client_attachment(attachment_id):
    """Download a client attachment"""
    from flask import send_file
    import os

    attachment = ClientAttachment.query.get_or_404(attachment_id)
    client = attachment.client

    # Build file path
    file_path = os.path.join(current_app.root_path, "..", attachment.file_path)

    if not os.path.exists(file_path):
        flash(_("File not found"), "error")
        return redirect(url_for("clients.view_client", client_id=client.id))

    return send_file(
        file_path, as_attachment=True, download_name=attachment.original_filename, mimetype=attachment.mime_type
    )


@clients_bp.route("/clients/attachments/<int:attachment_id>/delete", methods=["POST"])
@login_required
@admin_or_permission_required("edit_clients")
def delete_client_attachment(attachment_id):
    """Delete a client attachment"""
    import os

    attachment = ClientAttachment.query.get_or_404(attachment_id)
    client = attachment.client

    # Delete file
    file_path = os.path.join(current_app.root_path, "..", attachment.file_path)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            current_app.logger.error(f"Failed to delete attachment file: {e}")

    # Delete database record
    attachment_id_for_log = attachment.id
    client_id = client.id
    db.session.delete(attachment)

    if not safe_commit("delete_client_attachment", {"attachment_id": attachment_id_for_log}):
        flash(_("Could not delete attachment due to a database error. Please check server logs."), "error")
        return redirect(url_for("clients.view_client", client_id=client_id))

    log_event(
        "client.attachment.deleted", user_id=current_user.id, client_id=client_id, attachment_id=attachment_id_for_log
    )
    track_event(
        current_user.id, "client.attachment.deleted", {"client_id": client_id, "attachment_id": attachment_id_for_log}
    )

    flash(_("Attachment deleted successfully"), "success")
    return redirect(url_for("clients.view_client", client_id=client_id))
