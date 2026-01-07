"""
Routes for integration management.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app import db
from app.models import Integration, IntegrationCredential
from app.services.integration_service import IntegrationService
from app.utils.db import safe_commit
import secrets
import logging
import os

# Import registry to ensure connectors are registered
try:
    from app.integrations import registry  # noqa: F401
except ImportError:
    pass

logger = logging.getLogger(__name__)

integrations_bp = Blueprint("integrations", __name__)


def has_setup_wizard(provider):
    """Check if a setup wizard template exists for the given provider."""
    from flask import current_app
    template_path = f"integrations/wizard_{provider}.html"
    template_dir = os.path.join(current_app.root_path, "templates")
    template_file = os.path.join(template_dir, template_path)
    return os.path.exists(template_file)


@integrations_bp.route("/integrations")
@login_required
def list_integrations():
    """List all integrations accessible to the current user (global + per-user)."""
    service = IntegrationService()
    integrations = service.list_integrations(current_user.id)
    available_providers = service.get_available_providers()

    from flask import current_app
    
    return render_template(
        "integrations/list.html",
        integrations=integrations,
        available_providers=available_providers,
        current_user=current_user,
        config=current_app.config,
        has_setup_wizard=has_setup_wizard,
    )


@integrations_bp.route("/integrations/<provider>/connect", methods=["GET", "POST"])
@login_required
def connect_integration(provider):
    """Start OAuth flow for connecting an integration."""
    service = IntegrationService()

    # Check if provider is available
    if provider not in service._connector_registry:
        flash(_("Integration provider not available."), "error")
        return redirect(url_for("integrations.list_integrations"))

    # Trello doesn't use OAuth - redirect to manage page
    if provider == "trello":
        if not current_user.is_admin:
            flash(_("Trello integration must be configured by an administrator."), "error")
            return redirect(url_for("integrations.list_integrations"))
        return redirect(url_for("integrations.manage_integration", provider=provider))

    # CalDAV doesn't use OAuth - redirect to setup form
    if provider == "caldav_calendar":
        return redirect(url_for("integrations.caldav_setup"))

    # Google Calendar and CalDAV are per-user, all others are global
    is_global = provider not in ("google_calendar", "caldav_calendar")

    if is_global:
        # For global integrations, check if one exists
        integration = service.get_global_integration(provider)
        if not integration:
            # Create global integration (admin only)
            if not current_user.is_admin:
                flash(_("Only administrators can set up global integrations."), "error")
                return redirect(url_for("integrations.list_integrations"))
            result = service.create_integration(provider, user_id=None, is_global=True)
            if not result["success"]:
                flash(result["message"], "error")
                return redirect(url_for("integrations.list_integrations"))
            integration = result["integration"]
    else:
        # Per-user integration (Google Calendar)
        existing = Integration.query.filter_by(provider=provider, user_id=current_user.id, is_global=False).first()
        if existing:
            integration = existing
        else:
            result = service.create_integration(provider, user_id=current_user.id, is_global=False)
            if not result["success"]:
                flash(result["message"], "error")
                return redirect(url_for("integrations.list_integrations"))
            integration = result["integration"]

    # Get connector
    connector = service.get_connector(integration)
    if not connector:
        flash(_("Could not initialize connector."), "error")
        return redirect(url_for("integrations.list_integrations"))

    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    session[f"integration_oauth_state_{integration.id}"] = state

    # Get authorization URL - automatically redirects to OAuth provider (Google, etc.)
    try:
        redirect_uri = url_for("integrations.oauth_callback", provider=provider, _external=True)
        auth_url = connector.get_authorization_url(redirect_uri, state=state)
        # Automatically redirect to Google OAuth - user will authorize there
        return redirect(auth_url)
    except ValueError as e:
        # OAuth credentials not configured yet
        if provider == "google_calendar":
            if current_user.is_admin:
                flash(
                    _("Google Calendar OAuth credentials need to be configured first. Redirecting to setup..."), "info"
                )
                return redirect(url_for("integrations.manage_integration", provider=provider))
            else:
                flash(_("Google Calendar integration needs to be configured by an administrator first."), "warning")
        elif current_user.is_admin:
            flash(_("OAuth credentials not configured. Please configure them first."), "error")
            return redirect(url_for("integrations.manage_integration", provider=provider))
        else:
            flash(_("Integration not configured. Please ask an administrator to set up OAuth credentials."), "error")
        return redirect(url_for("integrations.list_integrations"))


@integrations_bp.route("/integrations/<provider>/callback")
@login_required
def oauth_callback(provider):
    """Handle OAuth callback."""
    service = IntegrationService()

    code = request.args.get("code")
    state = request.args.get("state")
    error = request.args.get("error")

    if error:
        flash(_("Authorization failed: %(error)s", error=error), "error")
        return redirect(url_for("integrations.list_integrations"))

    if not code:
        flash(_("Authorization code not received."), "error")
        return redirect(url_for("integrations.list_integrations"))

    # Find integration (global or per-user)
    is_global = provider != "google_calendar"
    if is_global:
        integration = service.get_global_integration(provider)
    else:
        integration = Integration.query.filter_by(provider=provider, user_id=current_user.id, is_global=False).first()

    if not integration:
        flash(_("Integration not found."), "error")
        return redirect(url_for("integrations.list_integrations"))

    # Verify state
    session_key = f"integration_oauth_state_{integration.id}"
    expected_state = session.get(session_key)
    if not expected_state or state != expected_state:
        flash(_("Invalid state parameter. Please try again."), "error")
        return redirect(url_for("integrations.list_integrations"))

    session.pop(session_key, None)

    # Get connector
    connector = service.get_connector(integration)
    if not connector:
        flash(_("Could not initialize connector."), "error")
        return redirect(url_for("integrations.list_integrations"))

    try:
        # Exchange code for tokens
        redirect_uri = url_for("integrations.oauth_callback", provider=provider, _external=True)
        tokens = connector.exchange_code_for_tokens(code, redirect_uri)

        # Save credentials
        service.save_credentials(
            integration_id=integration.id,
            access_token=tokens.get("access_token"),
            refresh_token=tokens.get("refresh_token"),
            expires_at=tokens.get("expires_at"),
            token_type=tokens.get("token_type", "Bearer"),
            scope=tokens.get("scope"),
            extra_data=tokens.get("extra_data", {}),
        )

        # Test connection (use None for user_id if global)
        test_result = service.test_connection(integration.id, current_user.id if not integration.is_global else None)
        if test_result.get("success"):
            flash(_("Integration connected successfully!"), "success")
        else:
            flash(
                _(
                    "Integration connected but connection test failed: %(message)s",
                    message=test_result.get("message", "Unknown error"),
                ),
                "warning",
            )

        # Redirect to manage page
        return redirect(url_for("integrations.manage_integration", provider=provider))

    except Exception as e:
        logger.error(f"Error in OAuth callback for {provider}: {e}")
        flash(_("Error connecting integration: %(error)s", error=str(e)), "error")
        return redirect(url_for("integrations.list_integrations"))


@integrations_bp.route("/integrations/<provider>/manage", methods=["GET", "POST"])
@login_required
def manage_integration(provider):
    """Manage an integration: configure OAuth credentials (admin) and connection management (all users)."""
    from app.models import Settings
    
    # Ensure registry is loaded
    try:
        from app.integrations import registry  # noqa: F401
    except ImportError:
        pass
    
    service = IntegrationService()

    # Get connector class if available, otherwise use defaults
    connector_class = service._connector_registry.get(provider)
    if not connector_class:
        # Provider not in registry - create a minimal connector class info
        class MinimalConnector:
            display_name = provider.replace("_", " ").title()
            description = ""
            icon = "plug"
        connector_class = MinimalConnector
        
        # Log warning but continue
        logger.warning(f"Provider {provider} not found in registry, using defaults")
    
    settings = Settings.get_settings()

    # Get or create integration
    is_global = provider not in ("google_calendar", "caldav_calendar")
    integration = None
    if is_global:
        integration = service.get_global_integration(provider)
        if not integration and current_user.is_admin:
            # Create global integration (admin only)
            result = service.create_integration(provider, user_id=None, is_global=True)
            if result["success"]:
                integration = result["integration"]
    else:
        # Per-user integration
        integration = Integration.query.filter_by(provider=provider, user_id=current_user.id, is_global=False).first()

    # Handle POST (OAuth credential updates - admin only for global integrations)
    if request.method == "POST":
        if is_global and not current_user.is_admin:
            flash(_("Only administrators can configure global integrations."), "error")
            return redirect(url_for("integrations.manage_integration", provider=provider))
        
        # Check if this is an OAuth credential update (admin section)
        if request.form.get("action") == "update_credentials":
            # Update OAuth credentials in Settings
            if provider == "trello":
                # Trello uses API key + secret, not OAuth
                api_key = request.form.get("trello_api_key", "").strip()
                api_secret = request.form.get("trello_api_secret", "").strip()
                
                # Validate required fields
                if not api_key:
                    flash(_("Trello API Key is required."), "error")
                    return redirect(url_for("integrations.manage_integration", provider=provider))
                
                # Check if we have existing credentials - if not, secret is required
                existing_creds = settings.get_integration_credentials("trello")
                if not existing_creds.get("api_secret") and not api_secret:
                    flash(_("Trello API Secret is required for new setup."), "error")
                    return redirect(url_for("integrations.manage_integration", provider=provider))
                
                if api_key:
                    settings.trello_api_key = api_key
                if api_secret:
                    settings.trello_api_secret = api_secret
                # Also save token if provided (for backward compatibility)
                token = request.form.get("trello_token", "").strip()
                if token and integration:
                    service.save_credentials(
                        integration_id=integration.id,
                        access_token=token,
                        refresh_token=None,
                        expires_at=None,
                        token_type="Bearer",
                        scope="read,write",
                        extra_data={"api_key": api_key},
                    )
            else:
                # OAuth-based integrations
                client_id = request.form.get(f"{provider}_client_id", "").strip()
                client_secret = request.form.get(f"{provider}_client_secret", "").strip()
                
                # Validate required fields
                if not client_id:
                    flash(_("OAuth Client ID is required."), "error")
                    return redirect(url_for("integrations.manage_integration", provider=provider))
                
                # Check if we have existing credentials - if not, secret is required
                existing_creds = settings.get_integration_credentials(provider)
                if not existing_creds.get("client_secret") and not client_secret:
                    flash(_("OAuth Client Secret is required for new setup."), "error")
                    return redirect(url_for("integrations.manage_integration", provider=provider))

                # Map provider names to Settings attributes - support all known providers
                attr_map = {
                    "jira": ("jira_client_id", "jira_client_secret"),
                    "slack": ("slack_client_id", "slack_client_secret"),
                    "github": ("github_client_id", "github_client_secret"),
                    "google_calendar": ("google_calendar_client_id", "google_calendar_client_secret"),
                    "outlook_calendar": ("outlook_calendar_client_id", "outlook_calendar_client_secret"),
                    "microsoft_teams": ("microsoft_teams_client_id", "microsoft_teams_client_secret"),
                    "asana": ("asana_client_id", "asana_client_secret"),
                    "gitlab": ("gitlab_client_id", "gitlab_client_secret"),
                    "quickbooks": ("quickbooks_client_id", "quickbooks_client_secret"),
                    "xero": ("xero_client_id", "xero_client_secret"),
                }

                if provider in attr_map:
                    id_attr, secret_attr = attr_map[provider]
                    if client_id:
                        try:
                            setattr(settings, id_attr, client_id)
                        except AttributeError:
                            logger.warning(f"Settings attribute {id_attr} does not exist, skipping")
                    if client_secret:
                        try:
                            setattr(settings, secret_attr, client_secret)
                        except AttributeError:
                            logger.warning(f"Settings attribute {secret_attr} does not exist, skipping")
                else:
                    logger.warning(f"Provider {provider} not in attr_map, cannot save OAuth credentials")

                # Handle special fields (save even if empty to allow clearing)
                if provider == "outlook_calendar":
                    tenant_id = request.form.get("outlook_calendar_tenant_id", "").strip()
                    try:
                        # Allow empty value (will use "common" as default)
                        settings.outlook_calendar_tenant_id = tenant_id if tenant_id else ""
                    except AttributeError:
                        logger.warning("Settings attribute outlook_calendar_tenant_id does not exist, skipping")
                elif provider == "microsoft_teams":
                    tenant_id = request.form.get("microsoft_teams_tenant_id", "").strip()
                    try:
                        # Allow empty value (will use "common" as default)
                        settings.microsoft_teams_tenant_id = tenant_id if tenant_id else ""
                    except AttributeError:
                        logger.warning("Settings attribute microsoft_teams_tenant_id does not exist, skipping")
                elif provider == "gitlab":
                    instance_url = request.form.get("gitlab_instance_url", "").strip()
                    if instance_url:
                        # Validate URL format
                        try:
                            from urllib.parse import urlparse
                            parsed = urlparse(instance_url)
                            if not parsed.scheme or not parsed.netloc:
                                flash(_("GitLab Instance URL must be a valid URL (e.g., https://gitlab.com)."), "error")
                                return redirect(url_for("integrations.manage_integration", provider=provider))
                        except Exception:
                            flash(_("GitLab Instance URL format is invalid."), "error")
                            return redirect(url_for("integrations.manage_integration", provider=provider))
                        
                        try:
                            settings.gitlab_instance_url = instance_url
                        except AttributeError:
                            logger.warning("Settings attribute gitlab_instance_url does not exist, skipping")
                    else:
                        # Set default if empty
                        try:
                            if not settings.gitlab_instance_url:
                                settings.gitlab_instance_url = "https://gitlab.com"
                        except AttributeError:
                            pass

            if safe_commit("update_integration_credentials", {"provider": provider}):
                flash(_("Integration credentials updated successfully."), "success")
                if provider == "google_calendar":
                    flash(
                        _("Users can now connect their Google Calendar. They will be automatically redirected to Google for authorization."),
                        "info",
                    )
                return redirect(url_for("integrations.manage_integration", provider=provider))
            else:
                flash(_("Failed to update credentials."), "error")
        
        # Check if this is a CalDAV credential update (non-OAuth)
        elif request.form.get("action") == "update_caldav_credentials":
            # CalDAV uses username/password, not OAuth
            if provider != "caldav_calendar":
                flash(_("This action is only available for CalDAV integrations."), "error")
                return redirect(url_for("integrations.manage_integration", provider=provider))
            
            # Get the integration to update (should be per-user)
            integration_to_update = integration
            if not integration_to_update:
                flash(_("Integration not found. Please connect the integration first."), "error")
                return redirect(url_for("integrations.manage_integration", provider=provider))
            
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()
            
            # Validate required fields
            if not username:
                flash(_("Username is required."), "error")
                return redirect(url_for("integrations.manage_integration", provider=provider))
            
            # Check if we have existing credentials - if not, password is required
            existing_creds = IntegrationCredential.query.filter_by(integration_id=integration_to_update.id).first()
            if not existing_creds and not password:
                flash(_("Password is required for new setup."), "error")
                return redirect(url_for("integrations.manage_integration", provider=provider))
            
            # Use existing password if new password not provided
            password_to_save = password if password else (existing_creds.access_token if existing_creds else "")
            
            if not password_to_save:
                flash(_("Password is required."), "error")
                return redirect(url_for("integrations.manage_integration", provider=provider))
            
            # Save credentials (password in access_token, username in extra_data)
            result = service.save_credentials(
                integration_id=integration_to_update.id,
                access_token=password_to_save,
                refresh_token=None,
                expires_at=None,
                token_type="Basic",
                scope="caldav",
                extra_data={"username": username},
            )
            
            if result.get("success"):
                flash(_("CalDAV credentials updated successfully."), "success")
                return redirect(url_for("integrations.manage_integration", provider=provider))
            else:
                flash(_("Failed to update CalDAV credentials: %(message)s", message=result.get("message", "Unknown error")), "error")
        
        # Check if this is an integration config update
        elif request.form.get("action") == "update_config":
            # Get the integration to update
            integration_to_update = integration if integration else user_integration
            if not integration_to_update:
                flash(_("Integration not found. Please connect the integration first."), "error")
                return redirect(url_for("integrations.manage_integration", provider=provider))
            
            # Get config schema from connector
            config_schema = {}
            if connector_class and hasattr(connector_class, "get_config_schema"):
                try:
                    # Need a temporary instance to call get_config_schema
                    temp_connector = connector_class(integration_to_update, None)
                    config_schema = temp_connector.get_config_schema()
                except Exception as e:
                    logger.warning(f"Could not get config schema for {provider}: {e}")
            
            # Update config from form
            if not integration_to_update.config:
                integration_to_update.config = {}
            
            # Process config fields from schema
            if config_schema and "fields" in config_schema:
                for field in config_schema["fields"]:
                    field_name = field.get("name")
                    if not field_name:
                        continue
                    
                    field_type = field.get("type", "string")
                    
                    if field_type == "boolean":
                        # Checkboxes: present = True, absent = False
                        value = field_name in request.form
                    elif field_type == "array":
                        # Array fields - get all selected values
                        values = request.form.getlist(field_name)
                        value = values if values else field.get("default", [])
                    elif field_type == "select":
                        # Select fields - single value
                        value = request.form.get(field_name, "").strip()
                        if not value:
                            value = field.get("default")
                    elif field_type == "number":
                        # Number fields - convert to int/float
                        value_str = request.form.get(field_name, "").strip()
                        if value_str:
                            try:
                                # Try int first, then float
                                if "." in value_str:
                                    value = float(value_str)
                                else:
                                    value = int(value_str)
                            except ValueError:
                                flash(_("Invalid number for field %(field)s", field=field.get("label", field_name)), "error")
                                continue
                        else:
                            # Empty value - use None if not required, otherwise use default
                            if field.get("required", False):
                                flash(_("Field %(field)s is required", field=field.get("label", field_name)), "error")
                                continue
                            value = None
                    elif field_type == "json":
                        # JSON fields - parse if provided
                        value_str = request.form.get(field_name, "").strip()
                        if value_str:
                            try:
                                import json
                                value = json.loads(value_str)
                            except json.JSONDecodeError:
                                flash(_("Invalid JSON for field %(field)s", field=field.get("label", field_name)), "error")
                                continue
                        else:
                            value = None
                    else:
                        # String/url/text fields
                        value = request.form.get(field_name, "").strip()
                        if not value and field.get("required", False):
                            flash(_("Field %(field)s is required", field=field.get("label", field_name)), "error")
                            continue
                        if not value:
                            value = field.get("default")
                    
                    # Update config field
                    # For optional number fields, explicitly set to None if empty
                    if field_type == "number" and value is None and not field.get("required", False):
                        integration_to_update.config[field_name] = None
                    elif value is not None and value != "":
                        integration_to_update.config[field_name] = value
                    elif field_type in ("boolean", "array"):
                        # Always set boolean and array fields
                        integration_to_update.config[field_name] = value
                    elif field_type == "number" and value is None:
                        # Required number field that's empty - already flashed error above
                        continue
            
            # Ensure config is marked as modified
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(integration_to_update, "config")
            
            if safe_commit("update_integration_config", {"integration_id": integration_to_update.id}):
                flash(_("Integration configuration updated successfully."), "success")
                return redirect(url_for("integrations.manage_integration", provider=provider))
            else:
                flash(_("Failed to update configuration."), "error")

    # Get current credentials for display (always get from Settings model, not .env)
    # This ensures we're showing what's in the database - Settings model prioritizes DB over .env
    current_creds = {}
    if current_user.is_admin:
        current_creds = settings.get_integration_credentials(provider)
        # For Trello, ensure api_secret is included (it should already be in the dict)
        if provider == "trello" and "api_secret" not in current_creds:
            if hasattr(settings, "trello_api_secret"):
                current_creds["api_secret"] = settings.trello_api_secret or ""
    
    # Get user's existing integration for this provider (if per-user)
    user_integration = None
    if not is_global:
        user_integration = Integration.query.filter_by(provider=provider, user_id=current_user.id, is_global=False).first()
    
    # Get connector if integration exists
    connector = None
    connector_error = None
    if integration or user_integration:
        integration_to_check = integration if integration else user_integration
        try:
            connector = service.get_connector(integration_to_check)
        except Exception as e:
            logger.error(f"Error initializing connector for integration: {e}", exc_info=True)
            connector_error = str(e)
    
    credentials = None
    if integration:
        credentials = IntegrationCredential.query.filter_by(integration_id=integration.id).first()
    elif user_integration:
        credentials = IntegrationCredential.query.filter_by(integration_id=user_integration.id).first()

    # Get display info from connector class or use defaults
    display_name = getattr(connector_class, "display_name", None) or provider.replace("_", " ").title()
    description = getattr(connector_class, "description", None) or ""
    
    # Get config schema from connector
    config_schema = {}
    current_config = {}
    active_integration = integration if integration else user_integration
    
    if active_integration:
        current_config = active_integration.config or {}
        if connector:
            try:
                config_schema = connector.get_config_schema()
            except Exception as e:
                logger.warning(f"Could not get config schema for {provider}: {e}")
        elif connector_class and hasattr(connector_class, "get_config_schema"):
            try:
                temp_connector = connector_class(active_integration, None)
                config_schema = temp_connector.get_config_schema()
            except Exception as e:
                logger.warning(f"Could not get config schema for {provider}: {e}")
    
    return render_template(
        "integrations/manage.html",
        provider=provider,
        connector_class=connector_class,
        connector=connector,
        connector_error=connector_error,
        integration=integration,
        user_integration=user_integration,
        active_integration=active_integration,
        credentials=credentials,
        current_creds=current_creds,
        display_name=display_name,
        description=description,
        is_global=is_global,
        config_schema=config_schema,
        current_config=current_config,
        has_setup_wizard=has_setup_wizard,
    )


@integrations_bp.route("/integrations/<int:integration_id>")
@login_required
def view_integration(integration_id):
    """View integration details."""
    service = IntegrationService()
    # Allow viewing global integrations for all users, per-user only for owner (or admin)
    integration = service.get_integration(integration_id, current_user.id if not current_user.is_admin else None, allow_admin_override=current_user.is_admin)

    if not integration:
        flash(_("Integration not found."), "error")
        return redirect(url_for("integrations.list_integrations"))

    # Try to get connector, but handle errors gracefully
    connector = None
    connector_error = None
    try:
        connector = service.get_connector(integration)
    except Exception as e:
        logger.error(f"Error initializing connector for integration {integration_id}: {e}", exc_info=True)
        connector_error = str(e)
    
    credentials = IntegrationCredential.query.filter_by(integration_id=integration_id).first()

    # Get recent sync events
    from app.models import IntegrationEvent

    recent_events = (
        IntegrationEvent.query.filter_by(integration_id=integration_id)
        .order_by(IntegrationEvent.created_at.desc())
        .limit(20)
        .all()
    )

    return render_template(
        "integrations/view.html",
        integration=integration,
        connector=connector,
        connector_error=connector_error,
        credentials=credentials,
        recent_events=recent_events,
    )


@integrations_bp.route("/integrations/<int:integration_id>/test", methods=["POST"])
@login_required
def test_integration(integration_id):
    """Test integration connection."""
    service = IntegrationService()
    # For per-user integrations, pass user_id; for admins, allow override to test any integration
    # For global integrations, user_id should be None
    integration = service.get_integration(
        integration_id, 
        current_user.id if not current_user.is_admin else None,
        allow_admin_override=current_user.is_admin
    )
    if not integration:
        flash(_("Integration not found."), "error")
        return redirect(url_for("integrations.list_integrations"))

    # For test_connection, pass user_id for per-user integrations, None for global
    # For per-user integrations, use the integration's user_id (which matches current_user for non-admins)
    # For global integrations, pass None
    # Admins can test any integration, so pass None with allow_admin_override=True
    if integration.is_global:
        test_user_id = None
        allow_admin_override = False
    elif current_user.is_admin:
        # Admin testing any integration - pass None to allow override in service
        test_user_id = None
        allow_admin_override = True
    else:
        # Non-admin testing their own per-user integration
        test_user_id = current_user.id
        allow_admin_override = False
    
    result = service.test_connection(integration_id, test_user_id, allow_admin_override=allow_admin_override)

    if result.get("success"):
        flash(_("Connection test successful!"), "success")
    else:
        flash(_("Connection test failed: %(message)s", message=result.get("message", "Unknown error")), "error")

    return redirect(url_for("integrations.view_integration", integration_id=integration_id))


@integrations_bp.route("/integrations/<int:integration_id>/delete", methods=["POST"])
@login_required
def delete_integration(integration_id):
    """Delete an integration."""
    service = IntegrationService()
    integration = service.get_integration(integration_id, current_user.id if not current_user.is_admin else None, allow_admin_override=current_user.is_admin)
    if not integration:
        flash(_("Integration not found."), "error")
        return redirect(url_for("integrations.list_integrations"))

    result = service.delete_integration(integration_id, current_user.id)

    if result["success"]:
        flash(_("Integration deleted successfully."), "success")
    else:
        flash(result["message"], "error")

    return redirect(url_for("integrations.list_integrations"))


@integrations_bp.route("/integrations/<int:integration_id>/sync", methods=["POST"])
@login_required
def sync_integration(integration_id):
    """Trigger a sync for an integration."""
    service = IntegrationService()
    integration = service.get_integration(integration_id, current_user.id if not current_user.is_admin else None, allow_admin_override=current_user.is_admin)

    if not integration:
        flash(_("Integration not found."), "error")
        return redirect(url_for("integrations.list_integrations"))

    connector = service.get_connector(integration)
    if not connector:
        flash(_("Connector not available."), "error")
        return redirect(url_for("integrations.view_integration", integration_id=integration_id))

    try:
        sync_result = connector.sync_data()
        
        # Update integration status
        from datetime import datetime
        integration.last_sync_at = datetime.utcnow()
        if sync_result.get("success"):
            integration.last_sync_status = "success"
            integration.last_error = None
            message = sync_result.get("message", "Sync completed successfully.")
            if sync_result.get("synced_count"):
                message += f" Synced {sync_result['synced_count']} items."
            flash(_("Sync completed successfully. %(details)s", details=message), "success")
        else:
            integration.last_sync_status = "error"
            integration.last_error = sync_result.get("message", "Unknown error")
            flash(_("Sync failed: %(message)s", message=sync_result.get("message", "Unknown error")), "error")
        
        # Log sync event
        service._log_event(
            integration_id,
            "sync",
            sync_result.get("success", False),
            sync_result.get("message"),
            {"synced_count": sync_result.get("synced_count")} if sync_result.get("success") and sync_result.get("synced_count") else None
        )
        
        if not safe_commit("update_integration_sync_status", {"integration_id": integration_id}):
            logger.warning(f"Could not update sync status for integration {integration_id}")
    except Exception as e:
        logger.error(f"Error syncing integration {integration_id}: {e}", exc_info=True)
        integration.last_sync_status = "error"
        integration.last_error = str(e)
        from datetime import datetime
        integration.last_sync_at = datetime.utcnow()
        safe_commit("update_integration_sync_status_error", {"integration_id": integration_id})
        flash(_("Error during sync: %(error)s", error=str(e)), "error")

    return redirect(url_for("integrations.view_integration", integration_id=integration_id))


@integrations_bp.route("/integrations/caldav_calendar/setup", methods=["GET", "POST"])
@login_required
def caldav_setup():
    """Setup CalDAV integration (non-OAuth, uses username/password)."""
    from app.models import Project

    service = IntegrationService()

    # Get or create integration
    existing = Integration.query.filter_by(provider="caldav_calendar", user_id=current_user.id, is_global=False).first()
    if existing:
        integration = existing
    else:
        result = service.create_integration("caldav_calendar", user_id=current_user.id, is_global=False)
        if not result["success"]:
            flash(result["message"], "error")
            return redirect(url_for("integrations.list_integrations"))
        integration = result["integration"]

    # Try to get connector, but don't fail if credentials are missing (user is setting up)
    connector = None
    try:
        connector = service.get_connector(integration)
    except Exception as e:
        logger.debug(f"Could not initialize CalDAV connector (may be normal during setup): {e}")

    # Get user's active projects for default project selection
    projects = Project.query.filter_by(status="active").order_by(Project.name).all()

    if request.method == "POST":
        server_url = request.form.get("server_url", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        calendar_url = request.form.get("calendar_url", "").strip()
        calendar_name = request.form.get("calendar_name", "").strip()
        default_project_id = request.form.get("default_project_id", "").strip()
        verify_ssl = request.form.get("verify_ssl") == "on"
        auto_sync = request.form.get("auto_sync") == "on"
        lookback_days_str = request.form.get("lookback_days", "90") or "90"

        # Validation
        errors = []
        
        if not server_url and not calendar_url:
            errors.append(_("Either server URL or calendar URL is required."))
        
        # Validate URL format if provided
        if server_url:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(server_url)
                if not parsed.scheme or not parsed.netloc:
                    errors.append(_("Server URL must be a valid URL (e.g., https://mail.example.com/dav)."))
            except Exception:
                errors.append(_("Server URL format is invalid."))
        
        if calendar_url:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(calendar_url)
                if not parsed.scheme or not parsed.netloc:
                    errors.append(_("Calendar URL must be a valid URL."))
            except Exception:
                errors.append(_("Calendar URL format is invalid."))
        
        # Check if we need to update credentials (username provided or password provided)
        existing_creds = IntegrationCredential.query.filter_by(integration_id=integration.id).first()
        needs_creds_update = username or password or not existing_creds
        
        if needs_creds_update:
            if not username:
                # Try to get existing username if password is being updated
                if existing_creds and existing_creds.extra_data:
                    username = existing_creds.extra_data.get("username", "")
                if not username:
                    errors.append(_("Username is required."))
            if not password and not existing_creds:
                errors.append(_("Password is required for new setup."))
        
        # Validate project if provided (optional)
        if default_project_id:
            try:
                project_id_int = int(default_project_id)
                project = Project.query.filter_by(id=project_id_int, status="active").first()
                if not project:
                    errors.append(_("Selected project not found or is not active."))
            except ValueError:
                errors.append(_("Invalid project selected."))
        
        try:
            lookback_days = int(lookback_days_str)
            if lookback_days < 1 or lookback_days > 365:
                errors.append(_("Lookback days must be between 1 and 365."))
        except ValueError:
            errors.append(_("Lookback days must be a valid number."))
            lookback_days = 90

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template(
                "integrations/caldav_setup.html",
                integration=integration,
                connector=connector,
                projects=projects,
            )

        # Update config
        if not integration.config:
            integration.config = {}
        integration.config["server_url"] = server_url if server_url else None
        integration.config["calendar_url"] = calendar_url if calendar_url else None
        integration.config["calendar_name"] = calendar_name if calendar_name else None
        integration.config["verify_ssl"] = verify_ssl
        integration.config["sync_direction"] = "calendar_to_time_tracker"  # MVP: import only
        integration.config["lookback_days"] = lookback_days
        # Save default_project_id only if provided (optional)
        if default_project_id:
            integration.config["default_project_id"] = int(default_project_id)
        else:
            integration.config["default_project_id"] = None
        integration.config["auto_sync"] = auto_sync

        # Save credentials (only if username/password provided)
        if username and (password or existing_creds):
            # Use existing password if new password not provided
            password_to_save = password if password else (existing_creds.access_token if existing_creds else "")
            if password_to_save:
                result = service.save_credentials(
                    integration_id=integration.id,
                    access_token=password_to_save,
                    refresh_token=None,
                    expires_at=None,
                    token_type="Basic",
                    scope="caldav",
                    extra_data={"username": username},
                )
                if not result.get("success"):
                    flash(_("Failed to save credentials: %(message)s", message=result.get("message", "Unknown error")), "error")
                    return render_template(
                        "integrations/caldav_setup.html",
                        integration=integration,
                        connector=connector,
                        projects=projects,
                    )

        # Ensure integration is active if credentials exist
        credentials_check = IntegrationCredential.query.filter_by(integration_id=integration.id).first()
        if credentials_check:
            integration.is_active = True

        if safe_commit("caldav_setup", {"integration_id": integration.id}):
            flash(_("CalDAV integration configured successfully."), "success")
            return redirect(url_for("integrations.view_integration", integration_id=integration.id))
        else:
            flash(_("Failed to save CalDAV configuration."), "error")

    return render_template(
        "integrations/caldav_setup.html",
        integration=integration,
        connector=connector,
        projects=projects,
    )


@integrations_bp.route("/integrations/<provider>/webhook", methods=["POST"])
def integration_webhook(provider):
    """Handle incoming webhooks from integration providers."""
    service = IntegrationService()

    # Check if provider is available
    if provider not in service._connector_registry:
        logger.warning(f"Webhook received for unknown provider: {provider}")
        return jsonify({"error": "Unknown provider"}), 404

    # Get webhook payload - preserve raw body for signature verification (GitHub, etc.)
    raw_body = request.data  # Raw bytes for signature verification
    payload = request.get_json(silent=True) or request.form.to_dict()
    headers = dict(request.headers)

    # Find active integrations for this provider
    # Note: For webhooks, we might need to identify which integration based on payload
    integrations = Integration.query.filter_by(provider=provider, is_active=True).all()

    if not integrations:
        logger.warning(f"No active integrations found for provider: {provider}")
        return jsonify({"error": "No active integration found"}), 404

    results = []
    for integration in integrations:
        try:
            connector = service.get_connector(integration)
            if not connector:
                continue

            # Handle webhook - pass raw body for signature verification
            result = connector.handle_webhook(payload, headers, raw_body=raw_body)
            results.append(
                {
                    "integration_id": integration.id,
                    "success": result.get("success", False),
                    "message": result.get("message", ""),
                }
            )

            # Log event
            if result.get("success"):
                service._log_event(
                    integration.id,
                    "webhook_received",
                    True,
                    f"Webhook processed successfully",
                    {"provider": provider, "event_type": payload.get("event_type", "unknown")},
                )
        except Exception as e:
            logger.error(f"Error handling webhook for integration {integration.id}: {e}", exc_info=True)
            results.append({"integration_id": integration.id, "success": False, "message": str(e)})

    # Return success if at least one integration processed the webhook
    if any(r["success"] for r in results):
        return jsonify({"success": True, "results": results}), 200
    else:
        return jsonify({"success": False, "results": results}), 500


@integrations_bp.route("/integrations/<provider>/wizard", methods=["GET", "POST"])
@login_required
def setup_wizard(provider):
    """Setup wizard for integration configuration."""
    # Check if wizard exists
    if not has_setup_wizard(provider):
        flash(_("Setup wizard not available for this integration."), "error")
        return redirect(url_for("integrations.list_integrations"))
    
    service = IntegrationService()
    
    # Check if provider is available
    if provider not in service._connector_registry:
        flash(_("Integration provider not available."), "error")
        return redirect(url_for("integrations.list_integrations"))
    
    # Get connector class
    connector_class = service._connector_registry.get(provider)
    if not connector_class:
        flash(_("Connector class not found."), "error")
        return redirect(url_for("integrations.list_integrations"))
    
    # Get display info
    display_name = getattr(connector_class, "display_name", None) or provider.replace("_", " ").title()
    description = getattr(connector_class, "description", None) or ""
    
    # Get or create integration
    is_global = provider not in ("google_calendar", "caldav_calendar")
    integration = None
    if is_global:
        integration = service.get_global_integration(provider)
        if not integration and current_user.is_admin:
            result = service.create_integration(provider, user_id=None, is_global=True)
            if result["success"]:
                integration = result["integration"]
    else:
        integration = Integration.query.filter_by(provider=provider, user_id=current_user.id, is_global=False).first()
    
    # Check permissions
    if is_global and not current_user.is_admin:
        flash(_("Only administrators can configure global integrations."), "error")
        return redirect(url_for("integrations.list_integrations"))
    
    # Handle POST - save wizard data
    if request.method == "POST":
        wizard_step = int(request.form.get("wizard_step", 1))
        
        # Get current config or create new
        if integration:
            if not integration.config:
                integration.config = {}
            current_config = integration.config
        else:
            current_config = {}
        
        # Update config based on wizard step and form data
        # This is a generic handler - specific wizards will override with their own logic
        config_schema = {}
        if connector_class and hasattr(connector_class, "get_config_schema"):
            try:
                temp_integration = integration if integration else Integration(provider=provider, config={})
                temp_connector = connector_class(temp_integration, None)
                config_schema = temp_connector.get_config_schema()
            except Exception as e:
                logger.warning(f"Could not get config schema for {provider}: {e}")
        
        # Process form fields based on config schema
        if config_schema and "fields" in config_schema:
            for field in config_schema["fields"]:
                field_name = field.get("name")
                if not field_name:
                    continue
                
                field_type = field.get("type", "string")
                
                if field_type == "boolean":
                    value = field_name in request.form
                elif field_type == "array":
                    values = request.form.getlist(field_name)
                    value = values if values else field.get("default", [])
                elif field_type in ("select", "string", "url", "text", "password", "number"):
                    value = request.form.get(field_name, "").strip()
                    if not value:
                        value = field.get("default")
                elif field_type == "json":
                    value_str = request.form.get(field_name, "").strip()
                    if value_str:
                        try:
                            import json
                            value = json.loads(value_str)
                        except json.JSONDecodeError:
                            flash(_("Invalid JSON for field %(field)s", field=field.get("label", field_name)), "error")
                            continue
                    else:
                        value = None
                else:
                    value = request.form.get(field_name, "").strip()
                
                if value is not None:
                    current_config[field_name] = value
        
        # Save OAuth credentials if provided (admin only for global)
        if is_global and current_user.is_admin:
            from app.models import Settings
            settings = Settings.get_settings()
            
            client_id = request.form.get(f"{provider}_client_id", "").strip()
            client_secret = request.form.get(f"{provider}_client_secret", "").strip()
            
            if client_id:
                attr_map = {
                    "jira": ("jira_client_id", "jira_client_id"),
                    "slack": ("slack_client_id", "slack_client_secret"),
                    "github": ("github_client_id", "github_client_secret"),
                    "gitlab": ("gitlab_client_id", "gitlab_client_secret"),
                    "quickbooks": ("quickbooks_client_id", "quickbooks_client_secret"),
                    "xero": ("xero_client_id", "xero_client_secret"),
                    "asana": ("asana_client_id", "asana_client_secret"),
                    "outlook_calendar": ("outlook_calendar_client_id", "outlook_calendar_client_secret"),
                    "microsoft_teams": ("microsoft_teams_client_id", "microsoft_teams_client_secret"),
                }
                
                if provider in attr_map:
                    id_attr, secret_attr = attr_map[provider]
                    if hasattr(settings, id_attr):
                        setattr(settings, id_attr, client_id)
                    if client_secret and hasattr(settings, secret_attr):
                        setattr(settings, secret_attr, client_secret)
        
        # Create integration if it doesn't exist
        if not integration:
            result = service.create_integration(
                provider,
                user_id=None if is_global else current_user.id,
                is_global=is_global
            )
            if result["success"]:
                integration = result["integration"]
            else:
                flash(result["message"], "error")
                return redirect(url_for("integrations.setup_wizard", provider=provider))
        
        # Update integration config
        integration.config = current_config
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(integration, "config")
        
        # If this is the last step, save and redirect
        # Individual wizard templates will handle determining the last step
        if safe_commit("save_wizard_config", {"provider": provider}):
            # Check if this was the final step (wizard template should set this)
            if request.form.get("wizard_final_step") == "true":
                flash(_("Integration configured successfully!"), "success")
                return jsonify({
                    "success": True,
                    "redirect_url": url_for("integrations.manage_integration", provider=provider)
                })
            else:
                return jsonify({"success": True})
        else:
            return jsonify({"success": False, "message": _("Failed to save configuration.")})
    
    # GET - render wizard
    current_config = integration.config if integration and integration.config else {}
    config_schema = {}
    
    if connector_class and hasattr(connector_class, "get_config_schema"):
        try:
            temp_integration = integration if integration else Integration(provider=provider, config={})
            temp_connector = connector_class(temp_integration, None)
            config_schema = temp_connector.get_config_schema()
        except Exception as e:
            logger.warning(f"Could not get config schema for {provider}: {e}")
    
    # Determine step labels based on provider
    step_labels_map = {
        "jira": [_("OAuth Setup"), _("Connection Test"), _("Sync Config"), _("Advanced"), _("Review")],
        "gitlab": [_("Instance"), _("OAuth"), _("Repositories"), _("Sync Settings"), _("Review")],
        "quickbooks": [_("OAuth"), _("Company"), _("Sync Config"), _("Mappings"), _("Review")],
        "xero": [_("OAuth"), _("Tenant"), _("Sync Config"), _("Mappings"), _("Review")],
        "github": [_("OAuth"), _("Repositories"), _("Sync Config"), _("Webhooks"), _("Review")],
        "asana": [_("OAuth"), _("Workspace"), _("Projects"), _("Sync Config"), _("Review")],
        "trello": [_("API Keys"), _("Connection Test"), _("Review")],
        "outlook_calendar": [_("Tenant ID"), _("OAuth"), _("Review")],
        "microsoft_teams": [_("Tenant ID"), _("OAuth"), _("Review")],
    }
    
    step_labels = step_labels_map.get(provider, [])
    total_steps = len(step_labels) if step_labels else 5  # Default to 5 if not specified
    
    # Get test connection URL if available
    test_connection_url = None
    if provider in ["jira", "gitlab", "trello"]:
        test_connection_url = url_for("integrations.test_connection_wizard", provider=provider)
    
    wizard_title = _("%(name)s Setup Wizard", name=display_name)
    wizard_subtitle = _("Guided step-by-step configuration for %(name)s", name=display_name)
    
    return render_template(
        f"integrations/wizard_{provider}.html",
        provider=provider,
        display_name=display_name,
        description=description,
        connector_class=connector_class,
        integration=integration,
        current_config=current_config,
        config_schema=config_schema,
        is_global=is_global,
        wizard_title=wizard_title,
        wizard_subtitle=wizard_subtitle,
        wizard_save_url=url_for("integrations.setup_wizard", provider=provider),
        total_steps=total_steps,
        step_labels=step_labels,
        test_connection_url=test_connection_url,
    )


@integrations_bp.route("/integrations/<provider>/wizard/test-connection", methods=["POST"])
@login_required
def test_connection_wizard(provider):
    """Test connection from wizard."""
    from flask import request as flask_request
    
    service = IntegrationService()
    
    # Get integration
    is_global = provider not in ("google_calendar", "caldav_calendar")
    if is_global:
        integration = service.get_global_integration(provider)
    else:
        integration = Integration.query.filter_by(provider=provider, user_id=current_user.id, is_global=False).first()
    
    if not integration:
        return jsonify({"success": False, "error": _("Integration not found")}), 404
    
    # Get connector
    connector = service.get_connector(integration)
    if not connector:
        return jsonify({"success": False, "error": _("Connector not available")}), 400
    
    # Test connection
    try:
        result = connector.test_connection()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Connection test error for {provider}: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500
