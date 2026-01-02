"""Client Portal Routes

Provides a simplified interface for clients to view their projects,
invoices, and time entries. Uses separate authentication from regular users.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, session, jsonify, current_app, send_from_directory
from flask_babel import gettext as _
from app import db
from app.models import Client, Project, Invoice, TimeEntry, User, Quote, Issue, Contact, Comment, ClientAttachment, ProjectAttachment, Activity
from app.models.client_time_approval import ClientTimeApproval
from app.services.client_approval_service import ClientApprovalService
from app.services.payment_gateway_service import PaymentGatewayService
from app.services.client_notification_service import ClientNotificationService
from app.utils.db import safe_commit
from datetime import datetime, timedelta
from sqlalchemy import func
from functools import wraps

client_portal_bp = Blueprint("client_portal", __name__)


def get_current_client():
    """Get the currently logged-in client from session (either Client or User portal access)"""
    # Check for Client portal authentication
    client_id = session.get("client_portal_id")
    if client_id:
        return Client.query.get(client_id)

    # Check for User portal authentication
    user_id = session.get("_user_id")
    if user_id:
        user = User.query.get(user_id)
        if user and user.is_client_portal_user:
            return user.client  # Return the Client object linked to the user

    return None


# Make get_current_client available to templates
@client_portal_bp.app_context_processor
def inject_get_current_client():
    """Make get_current_client available in templates"""
    return dict(get_current_client=get_current_client)


def check_client_portal_access():
    """Helper function to check if client has portal access - returns 403 for users without access, redirects to login if not authenticated

    Returns:
        Client: The Client object if access is granted
        Response: A redirect response if authentication is needed
        None: If 403 is raised (abort is called)
    """
    # Check for Client portal authentication
    client_id = session.get("client_portal_id")
    if client_id:
        client = Client.query.get(client_id)
        if not client:
            flash(_("Please log in to access the client portal."), "error")
            return redirect(url_for("client_portal.login", next=request.url))

        if not client.has_portal_access:
            flash(_("Client portal access is not enabled for your account."), "error")
            session.pop("client_portal_id", None)  # Clear invalid session
            return redirect(url_for("client_portal.login"))

        if not client.is_active:
            flash(_("Your client account is inactive."), "error")
            session.pop("client_portal_id", None)  # Clear invalid session
            return redirect(url_for("client_portal.login"))

        return client

    # Check for User portal authentication
    user_id = session.get("_user_id")
    if user_id:
        try:
            # Convert to int if it's a string (session stores it as string)
            if isinstance(user_id, str):
                user_id = int(user_id)
            # Query with options to ensure we get fresh data and load relationships
            from sqlalchemy.orm import joinedload

            user = User.query.options(joinedload(User.client)).get(user_id)
        except (ValueError, TypeError):
            # Invalid user_id format
            flash(_("Please log in to access the client portal."), "error")
            return redirect(url_for("client_portal.login", next=request.url))
        except Exception:
            # If there's a session error, try to rollback and retry
            try:
                db.session.rollback()
                user = User.query.options(joinedload(User.client)).get(user_id)
            except Exception:
                db.session.rollback()
                flash(_("Please log in to access the client portal."), "error")
                return redirect(url_for("client_portal.login", next=request.url))

        if not user:
            flash(_("Please log in to access the client portal."), "error")
            return redirect(url_for("client_portal.login", next=request.url))

        # Check portal access directly to ensure we have the latest values
        if not (user.client_portal_enabled and user.client_id is not None):
            # User is logged in but doesn't have portal access - return 403
            abort(403)

        if not user.is_active:
            abort(403)

        # Ensure client relationship is loaded - query directly if not loaded
        if not user.client and user.client_id:
            # Query the client directly if relationship not loaded
            client = Client.query.get(user.client_id)
            if not client:
                abort(403)
            return client

        if not user.client:
            abort(403)

        return user.client

    # No authentication at all - redirect to login
    flash(_("Please log in to access the client portal."), "error")
    return redirect(url_for("client_portal.login", next=request.url))


def get_portal_data(client):
    """Get portal data for a client, handling both Client and User authentication"""
    # Check if this is a User accessing via client portal
    user_id = session.get("_user_id")
    if user_id:
        try:
            # Convert to int if it's a string
            if isinstance(user_id, str):
                user_id = int(user_id)
            db.session.rollback()
            user = User.query.get(user_id)
            if user and user.is_client_portal_user and user.client_id == client.id:
                # Use User's get_client_portal_data method
                return user.get_client_portal_data()
        except Exception:
            db.session.rollback()
            # Fall through to Client method

    # Otherwise use Client's get_portal_data method
    return client.get_portal_data()


@client_portal_bp.route("/client-portal/login", methods=["GET", "POST"])
def login():
    """Client portal login page"""
    if request.method == "GET":
        # If already logged in, redirect to dashboard
        if get_current_client():
            return redirect(url_for("client_portal.dashboard"))
        return render_template("client_portal/login.html")

    # POST - handle login
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    if not username or not password:
        flash(_("Username and password are required."), "error")
        return render_template("client_portal/login.html")

    # Authenticate client
    client = Client.authenticate_portal(username, password)

    if not client:
        flash(_("Invalid username or password."), "error")
        return render_template("client_portal/login.html")

    # Log in the client
    session["client_portal_id"] = client.id
    session.permanent = True

    flash(_("Welcome, %(client_name)s!", client_name=client.name), "success")

    # Redirect to intended page or dashboard
    next_page = request.form.get("next") or request.args.get("next")
    if not next_page or not next_page.startswith("/client-portal"):
        next_page = url_for("client_portal.dashboard")

    return redirect(next_page)


@client_portal_bp.route("/client-portal/logout")
def logout():
    """Client portal logout"""
    session.pop("client_portal_id", None)
    flash(_("You have been logged out."), "info")
    return redirect(url_for("client_portal.login"))


@client_portal_bp.route("/client-portal/set-password", methods=["GET", "POST"])
def set_password():
    """Set or reset password using token from email"""
    token = request.args.get("token")

    if not token:
        flash(_("Invalid or missing password setup token."), "error")
        return redirect(url_for("client_portal.login"))

    # Find client by token
    client = Client.find_by_password_token(token)

    if not client:
        flash(_("Invalid or expired password setup token. Please request a new one."), "error")
        return redirect(url_for("client_portal.login"))

    if request.method == "POST":
        password = request.form.get("password", "").strip()
        password_confirm = request.form.get("password_confirm", "").strip()

        # Validate password
        if not password:
            flash(_("Password is required."), "error")
            return render_template("client_portal/set_password.html", client=client, token=token)

        if len(password) < 8:
            flash(_("Password must be at least 8 characters long."), "error")
            return render_template("client_portal/set_password.html", client=client, token=token)

        if password != password_confirm:
            flash(_("Passwords do not match."), "error")
            return render_template("client_portal/set_password.html", client=client, token=token)

        # Set password
        client.set_portal_password(password)
        client.clear_password_setup_token()

        if not safe_commit("client_set_password", {"client_id": client.id}):
            flash(_("Could not set password due to a database error."), "error")
            return render_template("client_portal/set_password.html", client=client, token=token)

        flash(_("Password set successfully! You can now log in to the portal."), "success")
        return redirect(url_for("client_portal.login"))

    return render_template("client_portal/set_password.html", client=client, token=token)


@client_portal_bp.route("/client-portal")
@client_portal_bp.route("/client-portal/dashboard")
def dashboard():
    """Client portal dashboard showing overview of projects, invoices, and time entries"""
    result = check_client_portal_access()
    if not isinstance(result, Client):  # It's a redirect response
        return result
    client = result
    portal_data = get_portal_data(client)

    if not portal_data:
        flash(_("Unable to load client portal data."), "error")
        return redirect(url_for("client_portal.login"))

    # Calculate statistics
    total_projects = len(portal_data["projects"])
    total_invoices = len(portal_data["invoices"])
    total_time_entries = len(portal_data["time_entries"])

    # Calculate total hours
    total_hours = sum(entry.duration_hours for entry in portal_data["time_entries"])

    # Calculate invoice totals
    total_invoice_amount = sum(inv.total_amount for inv in portal_data["invoices"])
    paid_invoice_amount = sum(inv.total_amount for inv in portal_data["invoices"] if inv.payment_status == "fully_paid")
    unpaid_invoice_amount = sum(
        inv.outstanding_amount for inv in portal_data["invoices"] if inv.payment_status != "fully_paid"
    )

    # Get recent activity (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_time_entries = [entry for entry in portal_data["time_entries"] if entry.start_time >= thirty_days_ago]

    # Group time entries by project
    project_hours = {}
    for entry in portal_data["time_entries"]:
        if not entry.project:
            continue
        project_id = entry.project.id
        if project_id not in project_hours:
            project_hours[project_id] = {"project": entry.project, "hours": 0.0}
        project_hours[project_id]["hours"] += entry.duration_hours

    # Get pending approvals count
    approval_service = ClientApprovalService()
    pending_approvals = approval_service.get_pending_approvals_for_client(client.id)
    pending_approvals_count = len(pending_approvals)

    # Get unread notifications count
    notification_service = ClientNotificationService()
    unread_notifications_count = notification_service.get_unread_count(client.id)

    return render_template(
        "client_portal/dashboard.html",
        client=client,
        projects=portal_data["projects"],
        invoices=portal_data["invoices"],
        time_entries=portal_data["time_entries"],
        total_projects=total_projects,
        total_invoices=total_invoices,
        total_time_entries=total_time_entries,
        total_hours=round(total_hours, 2),
        total_invoice_amount=total_invoice_amount,
        paid_invoice_amount=paid_invoice_amount,
        unpaid_invoice_amount=unpaid_invoice_amount,
        recent_time_entries=recent_time_entries,
        project_hours=list(project_hours.values()),
        pending_approvals_count=pending_approvals_count,
        unread_notifications_count=unread_notifications_count,
    )


@client_portal_bp.route("/client-portal/projects")
def projects():
    """List all projects for the client"""
    result = check_client_portal_access()
    if not isinstance(result, Client):
        return result
    client = result
    portal_data = get_portal_data(client)

    if not portal_data:
        flash(_("Unable to load client portal data."), "error")
        return redirect(url_for("client_portal.dashboard"))

    # Calculate hours per project
    project_stats = []
    for project in portal_data["projects"]:
        project_entries = [entry for entry in portal_data["time_entries"] if entry.project_id == project.id]
        total_hours = sum(entry.duration_hours for entry in project_entries)

        project_stats.append(
            {"project": project, "total_hours": round(total_hours, 2), "entry_count": len(project_entries)}
        )

    return render_template("client_portal/projects.html", client=client, project_stats=project_stats)


@client_portal_bp.route("/client-portal/invoices")
def invoices():
    """List all invoices for the client"""
    result = check_client_portal_access()
    if not isinstance(result, Client):
        return result
    client = result
    portal_data = get_portal_data(client)

    if not portal_data:
        flash(_("Unable to load client portal data."), "error")
        return redirect(url_for("client_portal.dashboard"))

    # Filter invoices by status if requested
    status_filter = request.args.get("status", "all")
    filtered_invoices = portal_data["invoices"]

    if status_filter == "paid":
        filtered_invoices = [inv for inv in filtered_invoices if inv.payment_status == "fully_paid"]
    elif status_filter == "unpaid":
        filtered_invoices = [inv for inv in filtered_invoices if inv.payment_status in ["unpaid", "partially_paid"]]
    elif status_filter == "overdue":
        filtered_invoices = [inv for inv in filtered_invoices if inv.is_overdue]

    return render_template(
        "client_portal/invoices.html", client=client, invoices=filtered_invoices, status_filter=status_filter
    )


@client_portal_bp.route("/client-portal/invoices/<int:invoice_id>")
def view_invoice(invoice_id):
    """View a specific invoice"""
    result = check_client_portal_access()
    if not isinstance(result, Client):
        return result
    client = result

    # Verify invoice belongs to this client
    invoice = Invoice.query.get_or_404(invoice_id)
    if invoice.client_id != client.id:
        flash(_("Invoice not found."), "error")
        abort(404)

    return render_template("client_portal/invoice_detail.html", client=client, invoice=invoice)


@client_portal_bp.route("/client-portal/quotes")
def quotes():
    """List all quotes visible to the client"""
    result = check_client_portal_access()
    if not isinstance(result, Client):
        return result
    client = result

    # Get quotes visible to client
    quotes_list = (
        Quote.query.filter_by(client_id=client.id, visible_to_client=True).order_by(Quote.created_at.desc()).all()
    )

    return render_template("client_portal/quotes.html", client=client, quotes=quotes_list)


@client_portal_bp.route("/client-portal/quotes/<int:quote_id>")
def view_quote(quote_id):
    """View a specific quote"""
    result = check_client_portal_access()
    if not isinstance(result, Client):
        return result
    client = result

    # Verify quote belongs to this client and is visible
    quote = Quote.query.get_or_404(quote_id)
    if quote.client_id != client.id or not quote.visible_to_client:
        flash(_("Quote not found."), "error")
        abort(404)

    return render_template("client_portal/quote_detail.html", client=client, quote=quote)


@client_portal_bp.route("/client-portal/time-entries")
def time_entries():
    """List time entries for the client's projects"""
    result = check_client_portal_access()
    if not isinstance(result, Client):
        return result
    client = result
    portal_data = get_portal_data(client)

    if not portal_data:
        flash(_("Unable to load client portal data."), "error")
        return redirect(url_for("client_portal.dashboard"))

    # Filter by project if requested
    project_id = request.args.get("project_id", type=int)
    filtered_entries = portal_data["time_entries"]

    if project_id:
        filtered_entries = [entry for entry in filtered_entries if entry.project_id == project_id]

    # Filter by date range if requested
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")

    if date_from:
        try:
            date_from_dt = datetime.strptime(date_from, "%Y-%m-%d")
            filtered_entries = [entry for entry in filtered_entries if entry.start_time.date() >= date_from_dt.date()]
        except ValueError:
            pass

    if date_to:
        try:
            date_to_dt = datetime.strptime(date_to, "%Y-%m-%d")
            filtered_entries = [entry for entry in filtered_entries if entry.start_time.date() <= date_to_dt.date()]
        except ValueError:
            pass

    return render_template(
        "client_portal/time_entries.html",
        client=client,
        projects=portal_data["projects"],
        time_entries=filtered_entries,
        selected_project_id=project_id,
        date_from=date_from,
        date_to=date_to,
    )


@client_portal_bp.route("/client-portal/issues")
def issues():
    """List all issues reported by the client"""
    result = check_client_portal_access()
    if not isinstance(result, Client):
        return result
    client = result
    
    # Check if issue reporting is enabled
    if not client.has_portal_access or not client.portal_issues_enabled:
        flash(_("Issue reporting is not available."), "error")
        return redirect(url_for("client_portal.dashboard"))
    
    # Get all issues for this client
    issues_list = Issue.get_issues_by_client(client.id)
    
    # Filter by status if requested
    status_filter = request.args.get("status", "all")
    if status_filter != "all":
        issues_list = [issue for issue in issues_list if issue.status == status_filter]
    
    # Get projects for filter dropdown
    portal_data = get_portal_data(client)
    projects = portal_data["projects"] if portal_data else []
    
    return render_template(
        "client_portal/issues.html",
        client=client,
        issues=issues_list,
        status_filter=status_filter,
        projects=projects,
    )


@client_portal_bp.route("/client-portal/issues/new", methods=["GET", "POST"])
def new_issue():
    """Create a new issue report"""
    result = check_client_portal_access()
    if not isinstance(result, Client):
        return result
    client = result
    
    # Check if issue reporting is enabled
    if not client.has_portal_access or not client.portal_issues_enabled:
        flash(_("Issue reporting is not available."), "error")
        return redirect(url_for("client_portal.dashboard"))
    
    # Get projects for dropdown
    portal_data = get_portal_data(client)
    projects = portal_data["projects"] if portal_data else []
    
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        project_id = request.form.get("project_id", type=int)
        priority = request.form.get("priority", "medium")
        submitter_name = request.form.get("submitter_name", "").strip()
        submitter_email = request.form.get("submitter_email", "").strip()
        
        # Validate
        if not title:
            flash(_("Title is required."), "error")
            return render_template(
                "client_portal/new_issue.html",
                client=client,
                projects=projects,
                title=title,
                description=description,
                project_id=project_id,
                priority=priority,
                submitter_name=submitter_name,
                submitter_email=submitter_email,
            )
        
        # Validate project belongs to client
        if project_id:
            project = Project.query.get(project_id)
            if not project or project.client_id != client.id:
                flash(_("Invalid project selected."), "error")
                return render_template(
                    "client_portal/new_issue.html",
                    client=client,
                    projects=projects,
                    title=title,
                    description=description,
                    project_id=project_id,
                    priority=priority,
                    submitter_name=submitter_name,
                    submitter_email=submitter_email,
                )
        
        # Create issue
        issue = Issue(
            client_id=client.id,
            title=title,
            description=description if description else None,
            project_id=project_id,
            priority=priority,
            status="open",
            submitted_by_client=True,
            client_submitter_name=submitter_name if submitter_name else None,
            client_submitter_email=submitter_email if submitter_email else None,
        )
        
        db.session.add(issue)
        
        if not safe_commit("client_create_issue", {"client_id": client.id, "issue_id": issue.id}):
            flash(_("Could not create issue due to a database error."), "error")
            return render_template(
                "client_portal/new_issue.html",
                client=client,
                projects=projects,
                title=title,
                description=description,
                project_id=project_id,
                priority=priority,
                submitter_name=submitter_name,
                submitter_email=submitter_email,
            )
        
        flash(_("Issue reported successfully. We will review it shortly."), "success")
        return redirect(url_for("client_portal.issues"))
    
    return render_template("client_portal/new_issue.html", client=client, projects=projects)


@client_portal_bp.route("/client-portal/issues/<int:issue_id>")
def view_issue(issue_id):
    """View a specific issue"""
    result = check_client_portal_access()
    if not isinstance(result, Client):
        return result
    client = result
    
    # Check if issue reporting is enabled
    if not client.has_portal_access or not client.portal_issues_enabled:
        flash(_("Issue reporting is not available."), "error")
        return redirect(url_for("client_portal.dashboard"))
    
    # Verify issue belongs to this client
    issue = Issue.query.get_or_404(issue_id)
    if issue.client_id != client.id:
        flash(_("Issue not found."), "error")
        abort(404)
    
    return render_template("client_portal/issue_detail.html", client=client, issue=issue)


# ==================== Time Entry Approvals ====================

@client_portal_bp.route("/client-portal/approvals")
def time_entry_approvals():
    """List pending time entry approvals for the client"""
    result = check_client_portal_access()
    if not isinstance(result, Client):
        return result
    client = result
    
    approval_service = ClientApprovalService()
    from app.models.client_time_approval import ClientApprovalStatus
    
    # Get pending approvals
    pending_approvals = approval_service.get_pending_approvals_for_client(client.id)
    
    # Get all approvals (pending, approved, rejected)
    all_approvals = (
        db.session.query(ClientTimeApproval)
        .filter_by(client_id=client.id)
        .order_by(ClientTimeApproval.requested_at.desc())
        .limit(100)
        .all()
    )
    
    # Get status filter
    status_filter = request.args.get("status", "pending")
    if status_filter == "pending":
        approvals = pending_approvals
    elif status_filter == "approved":
        approvals = [a for a in all_approvals if a.status == ClientApprovalStatus.APPROVED]
    elif status_filter == "rejected":
        approvals = [a for a in all_approvals if a.status == ClientApprovalStatus.REJECTED]
    else:
        approvals = all_approvals
    
    return render_template(
        "client_portal/approvals.html",
        client=client,
        approvals=approvals,
        pending_count=len(pending_approvals),
        status_filter=status_filter,
    )


@client_portal_bp.route("/client-portal/approvals/<int:approval_id>")
def view_approval(approval_id):
    """View a specific time entry approval"""
    result = check_client_portal_access()
    if not isinstance(result, Client):
        return result
    client = result
    
    from app.models.client_time_approval import ClientTimeApproval
    approval = ClientTimeApproval.query.get_or_404(approval_id)
    
    # Verify approval belongs to this client
    if approval.client_id != client.id:
        flash(_("Approval not found."), "error")
        abort(404)
    
    return render_template("client_portal/approval_detail.html", client=client, approval=approval)


@client_portal_bp.route("/client-portal/approvals/<int:approval_id>/approve", methods=["POST"])
def approve_time_entry(approval_id):
    """Approve a time entry"""
    result = check_client_portal_access()
    if not isinstance(result, Client):
        return result
    client = result
    
    from app.models.client_time_approval import ClientTimeApproval
    approval = ClientTimeApproval.query.get_or_404(approval_id)
    
    # Verify approval belongs to this client
    if approval.client_id != client.id:
        flash(_("Approval not found."), "error")
        abort(404)
    
    # Get contact ID (use primary contact or first active contact)
    contact = Contact.get_primary_contact(client.id) or Contact.get_active_contacts(client.id)[0] if Contact.get_active_contacts(client.id) else None
    if not contact:
        flash(_("No contact found for approval."), "error")
        return redirect(url_for("client_portal.time_entry_approvals"))
    
    comment = request.form.get("comment", "").strip()
    
    approval_service = ClientApprovalService()
    result = approval_service.approve(approval_id, contact.id, comment)
    
    if result["success"]:
        flash(_("Time entry approved successfully."), "success")
    else:
        flash(_("Error approving time entry: %(error)s", error=result.get("message", "Unknown error")), "error")
    
    return redirect(url_for("client_portal.view_approval", approval_id=approval_id))


@client_portal_bp.route("/client-portal/approvals/<int:approval_id>/reject", methods=["POST"])
def reject_time_entry(approval_id):
    """Reject a time entry"""
    result = check_client_portal_access()
    if not isinstance(result, Client):
        return result
    client = result
    
    from app.models.client_time_approval import ClientTimeApproval
    approval = ClientTimeApproval.query.get_or_404(approval_id)
    
    # Verify approval belongs to this client
    if approval.client_id != client.id:
        flash(_("Approval not found."), "error")
        abort(404)
    
    reason = request.form.get("reason", "").strip()
    if not reason:
        flash(_("Rejection reason is required."), "error")
        return redirect(url_for("client_portal.view_approval", approval_id=approval_id))
    
    # Get contact ID
    contact = Contact.get_primary_contact(client.id) or Contact.get_active_contacts(client.id)[0] if Contact.get_active_contacts(client.id) else None
    if not contact:
        flash(_("No contact found for approval."), "error")
        return redirect(url_for("client_portal.time_entry_approvals"))
    
    approval_service = ClientApprovalService()
    result = approval_service.reject(approval_id, contact.id, reason)
    
    if result["success"]:
        flash(_("Time entry rejected."), "info")
    else:
        flash(_("Error rejecting time entry: %(error)s", error=result.get("message", "Unknown error")), "error")
    
    return redirect(url_for("client_portal.view_approval", approval_id=approval_id))


# ==================== Quote Approval ====================

@client_portal_bp.route("/client-portal/quotes/<int:quote_id>/accept", methods=["POST"])
def accept_quote(quote_id):
    """Accept a quote"""
    result = check_client_portal_access()
    if not isinstance(result, Client):
        return result
    client = result
    
    quote = Quote.query.get_or_404(quote_id)
    if quote.client_id != client.id or not quote.visible_to_client:
        flash(_("Quote not found."), "error")
        abort(404)
    
    if quote.status not in ["draft", "sent"]:
        flash(_("This quote cannot be accepted."), "error")
        return redirect(url_for("client_portal.view_quote", quote_id=quote_id))
    
    # Update quote status
    quote.status = "accepted"
    quote.accepted_at = datetime.utcnow()
    quote.accepted_by = None  # Client acceptance, not user
    
    # Notify admin users
    from app.utils.email import send_email
    from app.models import User as UserModel
    
    admins = UserModel.query.filter_by(role="admin", is_active=True).all()
    for admin in admins:
        if admin.email:
            try:
                send_email(
                    to=admin.email,
                    subject=f"Quote {quote.quote_number} Accepted by Client",
                    template="email/quote_accepted.html",
                    quote=quote,
                    client=client,
                )
            except Exception as e:
                current_app.logger.error(f"Error sending quote acceptance email: {e}")
    
    db.session.commit()
    flash(_("Quote accepted successfully. We will contact you shortly."), "success")
    return redirect(url_for("client_portal.view_quote", quote_id=quote_id))


@client_portal_bp.route("/client-portal/quotes/<int:quote_id>/reject", methods=["POST"])
def reject_quote(quote_id):
    """Reject a quote"""
    result = check_client_portal_access()
    if not isinstance(result, Client):
        return result
    client = result
    
    quote = Quote.query.get_or_404(quote_id)
    if quote.client_id != client.id or not quote.visible_to_client:
        flash(_("Quote not found."), "error")
        abort(404)
    
    if quote.status not in ["draft", "sent"]:
        flash(_("This quote cannot be rejected."), "error")
        return redirect(url_for("client_portal.view_quote", quote_id=quote_id))
    
    reason = request.form.get("reason", "").strip()
    
    # Update quote status
    quote.status = "rejected"
    quote.rejected_at = datetime.utcnow()
    quote.rejection_reason = reason
    
    # Notify admin users
    from app.utils.email import send_email
    from app.models import User as UserModel
    
    admins = UserModel.query.filter_by(role="admin", is_active=True).all()
    for admin in admins:
        if admin.email:
            try:
                send_email(
                    to=admin.email,
                    subject=f"Quote {quote.quote_number} Rejected by Client",
                    template="email/quote_rejected.html",
                    quote=quote,
                    client=client,
                    reason=reason,
                )
            except Exception as e:
                current_app.logger.error(f"Error sending quote rejection email: {e}")
    
    db.session.commit()
    flash(_("Quote rejected. We appreciate your feedback."), "info")
    return redirect(url_for("client_portal.quotes"))


# ==================== Invoice Payment ====================

@client_portal_bp.route("/client-portal/invoices/<int:invoice_id>/pay")
def pay_invoice(invoice_id):
    """Pay an invoice via payment gateway"""
    result = check_client_portal_access()
    if not isinstance(result, Client):
        return result
    client = result
    
    invoice = Invoice.query.get_or_404(invoice_id)
    if invoice.client_id != client.id:
        flash(_("Invoice not found."), "error")
        abort(404)
    
    # Check if invoice is already paid
    if invoice.payment_status == "fully_paid":
        flash(_("This invoice is already paid."), "info")
        return redirect(url_for("client_portal.view_invoice", invoice_id=invoice_id))
    
    # Get active payment gateway
    payment_service = PaymentGatewayService()
    gateway = payment_service.get_active_gateway()
    
    if not gateway:
        flash(_("Online payment is not currently available. Please contact us for payment instructions."), "warning")
        return redirect(url_for("client_portal.view_invoice", invoice_id=invoice_id))
    
    # Redirect to payment gateway
    if gateway.provider == "stripe":
        return redirect(url_for("payment_gateways.pay_invoice", invoice_id=invoice_id))
    else:
        flash(_("Payment gateway not yet supported."), "error")
        return redirect(url_for("client_portal.view_invoice", invoice_id=invoice_id))


# ==================== Project Comments ====================

@client_portal_bp.route("/client-portal/projects/<int:project_id>/comments", methods=["GET", "POST"])
def project_comments(project_id):
    """View and add comments to a project"""
    result = check_client_portal_access()
    if not isinstance(result, Client):
        return result
    client = result
    
    project = Project.query.get_or_404(project_id)
    if project.client_id != client.id:
        flash(_("Project not found."), "error")
        abort(404)
    
    if request.method == "POST":
        comment_text = request.form.get("comment", "").strip()
        if not comment_text:
            flash(_("Comment cannot be empty."), "error")
            return redirect(url_for("client_portal.project_comments", project_id=project_id))
        
        # Get contact for comment author
        contact = Contact.get_primary_contact(client.id) or Contact.get_active_contacts(client.id)[0] if Contact.get_active_contacts(client.id) else None
        if not contact:
            flash(_("No contact found for commenting."), "error")
            return redirect(url_for("client_portal.project_comments", project_id=project_id))
        
        # Create comment with client contact
        comment = Comment(
            content=comment_text,
            client_contact_id=contact.id,
            project_id=project_id,
            is_internal=False,  # Client comments are visible
        )
        db.session.add(comment)
        db.session.commit()
        
        flash(_("Comment added successfully."), "success")
        return redirect(url_for("client_portal.project_comments", project_id=project_id))
    
    # Get all comments for this project (only non-internal or client comments)
    comments = Comment.query.filter(
        Comment.project_id == project_id,
        db.or_(Comment.is_internal == False, Comment.is_client_comment == True)
    ).order_by(Comment.created_at.desc()).all()
    
    return render_template("client_portal/project_comments.html", client=client, project=project, comments=comments)


# ==================== Notifications ====================

@client_portal_bp.route("/client-portal/notifications")
def notifications():
    """View notifications for the client"""
    result = check_client_portal_access()
    if not isinstance(result, Client):
        return result
    client = result
    
    from app.services.client_notification_service import ClientNotificationService
    from app.models.client_notification import ClientNotification
    
    service = ClientNotificationService()
    
    # Get filter
    filter_type = request.args.get("filter", "all")
    unread_only = filter_type == "unread"
    
    notifications_list = service.get_notifications(client.id, limit=100, unread_only=unread_only)
    unread_count = service.get_unread_count(client.id)
    
    return render_template(
        "client_portal/notifications.html",
        client=client,
        notifications=notifications_list,
        unread_count=unread_count,
        filter_type=filter_type,
    )


@client_portal_bp.route("/client-portal/notifications/<int:notification_id>/read", methods=["POST"])
def mark_notification_read(notification_id):
    """Mark a notification as read"""
    result = check_client_portal_access()
    if not isinstance(result, Client):
        return result
    client = result
    
    from app.services.client_notification_service import ClientNotificationService
    service = ClientNotificationService()
    
    success = service.mark_as_read(notification_id, client.id)
    if success:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": "Notification not found"}), 404


@client_portal_bp.route("/client-portal/notifications/mark-all-read", methods=["POST"])
def mark_all_notifications_read():
    """Mark all notifications as read"""
    result = check_client_portal_access()
    if not isinstance(result, Client):
        return result
    client = result
    
    from app.services.client_notification_service import ClientNotificationService
    service = ClientNotificationService()
    
    count = service.mark_all_as_read(client.id)
    flash(_("Marked %(count)d notifications as read.", count=count), "success")
    return redirect(url_for("client_portal.notifications"))


# ==================== Documents ====================

@client_portal_bp.route("/client-portal/documents")
def documents():
    """View documents/files for the client"""
    result = check_client_portal_access()
    if not isinstance(result, Client):
        return result
    client = result
    
    # Get client attachments
    attachments = ClientAttachment.query.filter_by(
        client_id=client.id,
        visible_to_client=True
    ).order_by(ClientAttachment.uploaded_at.desc()).all()
    
    # Get project attachments
    from app.models import ProjectAttachment, Project
    project_ids = [p.id for p in Project.query.filter_by(client_id=client.id).all()]
    project_attachments = []
    if project_ids:
        project_attachments = ProjectAttachment.query.filter(
            ProjectAttachment.project_id.in_(project_ids),
            ProjectAttachment.is_visible_to_client == True
        ).order_by(ProjectAttachment.uploaded_at.desc()).all()
    
    # Add project reference to project attachments for template
    for att in project_attachments:
        if att.project_id:
            att.project = Project.query.get(att.project_id)
    
    # Combine and sort
    all_attachments = list(attachments) + list(project_attachments)
    # Sort by uploaded_at, handling None values
    all_attachments.sort(key=lambda x: x.uploaded_at if x.uploaded_at else datetime.min.replace(tzinfo=None) if hasattr(datetime.min, 'tzinfo') else datetime.min, reverse=True)
    
    return render_template("client_portal/documents.html", client=client, attachments=all_attachments)


@client_portal_bp.route("/client-portal/documents/<int:attachment_id>/download")
def download_attachment(attachment_id):
    """Download a client or project attachment"""
    result = check_client_portal_access()
    if not isinstance(result, Client):
        return result
    client = result
    
    import os
    
    # Try client attachment first
    attachment = ClientAttachment.query.get(attachment_id)
    if attachment and attachment.client_id == client.id and attachment.is_visible_to_client:
        # Get file directory - file_path is relative to static or uploads folder
        if attachment.file_path.startswith('uploads/'):
            file_dir = os.path.join(current_app.root_path, '..', 'uploads')
            filename = os.path.basename(attachment.file_path)
        else:
            file_dir = os.path.join(current_app.root_path, 'static', os.path.dirname(attachment.file_path))
            filename = os.path.basename(attachment.file_path)
        
        return send_from_directory(file_dir, filename, as_attachment=True, download_name=attachment.original_filename)
    
    # Try project attachment
    from app.models import ProjectAttachment, Project
    attachment = ProjectAttachment.query.get(attachment_id)
    if attachment:
        project = Project.query.get(attachment.project_id)
        if project and project.client_id == client.id and attachment.is_visible_to_client:
            # Get file directory
            if attachment.file_path.startswith('uploads/'):
                file_dir = os.path.join(current_app.root_path, '..', 'uploads')
                filename = os.path.basename(attachment.file_path)
            else:
                file_dir = os.path.join(current_app.root_path, 'static', os.path.dirname(attachment.file_path))
                filename = os.path.basename(attachment.file_path)
            
            return send_from_directory(file_dir, filename, as_attachment=True, download_name=attachment.original_filename)
    
    flash(_("Attachment not found or access denied."), "error")
    return redirect(url_for("client_portal.documents"))


# ==================== Reports ====================

@client_portal_bp.route("/client-portal/reports")
def reports():
    """View client-specific reports"""
    result = check_client_portal_access()
    if not isinstance(result, Client):
        return result
    client = result
    
    portal_data = get_portal_data(client)
    
    # Calculate report data
    from datetime import datetime, timedelta
    from decimal import Decimal
    
    # Time tracking summary
    total_hours = sum(entry.duration_hours for entry in portal_data["time_entries"])
    
    # Project hours breakdown
    project_hours = {}
    for entry in portal_data["time_entries"]:
        if entry.project_id:
            if entry.project_id not in project_hours:
                project_hours[entry.project_id] = {
                    "project": entry.project,
                    "hours": 0.0,
                    "billable_hours": 0.0,
                }
            project_hours[entry.project_id]["hours"] += entry.duration_hours
            if entry.billable:
                project_hours[entry.project_id]["billable_hours"] += entry.duration_hours
    
    # Invoice summary
    invoice_summary = {
        "total": sum(inv.total_amount for inv in portal_data["invoices"]),
        "paid": sum(inv.total_amount for inv in portal_data["invoices"] if inv.payment_status == "fully_paid"),
        "unpaid": sum(inv.outstanding_amount for inv in portal_data["invoices"] if inv.payment_status != "fully_paid"),
        "overdue": sum(inv.outstanding_amount for inv in portal_data["invoices"] if inv.is_overdue),
    }
    
    # Recent activity (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_entries = [e for e in portal_data["time_entries"] if e.start_time >= thirty_days_ago]
    
    return render_template(
        "client_portal/reports.html",
        client=client,
        total_hours=round(total_hours, 2),
        project_hours=list(project_hours.values()),
        invoice_summary=invoice_summary,
        recent_entries=recent_entries,
    )


# ==================== Activity Feed ====================

@client_portal_bp.route("/client-portal/activity")
def activity_feed():
    """View project activity feed"""
    result = check_client_portal_access()
    if not isinstance(result, Client):
        return result
    client = result
    
    from app.models import Activity, Project
    
    # Get client's projects
    project_ids = [p.id for p in Project.query.filter_by(client_id=client.id).all()]
    
    # Get activities for these projects
    activities = []
    if project_ids:
        activities = Activity.query.filter(
            Activity.project_id.in_(project_ids)
        ).order_by(Activity.created_at.desc()).limit(50).all()
    
    return render_template("client_portal/activity_feed.html", client=client, activities=activities)
