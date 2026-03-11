"""
Centralized blueprint registration for the Flask app.
Extracted from app/__init__.py to reduce bootstrap module size and clarify structure.
"""


def register_all_blueprints(app, logger=None):
    """Import and register all route blueprints. Optional blueprints are wrapped in try/except."""
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.projects import projects_bp
    from app.routes.timer import timer_bp
    from app.routes.reports import reports_bp
    from app.routes.admin import admin_bp
    from app.routes.api import api_bp
    from app.routes.api_v1 import api_v1_bp
    from app.routes.api_v1_time_entries import api_v1_time_entries_bp
    from app.routes.api_v1_projects import api_v1_projects_bp
    from app.routes.api_v1_tasks import api_v1_tasks_bp
    from app.routes.api_v1_clients import api_v1_clients_bp
    from app.routes.api_v1_invoices import api_v1_invoices_bp
    from app.routes.api_v1_expenses import api_v1_expenses_bp
    from app.routes.api_v1_payments import api_v1_payments_bp
    from app.routes.api_v1_mileage import api_v1_mileage_bp
    from app.routes.api_v1_deals import api_v1_deals_bp
    from app.routes.api_v1_leads import api_v1_leads_bp
    from app.routes.api_v1_contacts import api_v1_contacts_bp
    from app.routes.api_docs import api_docs_bp, swaggerui_blueprint
    from app.routes.analytics import analytics_bp
    from app.routes.tasks import tasks_bp
    from app.routes.issues import issues_bp
    from app.routes.invoices import invoices_bp
    from app.routes.recurring_invoices import recurring_invoices_bp
    from app.routes.payments import payments_bp
    from app.routes.clients import clients_bp
    from app.routes.client_notes import client_notes_bp
    from app.routes.comments import comments_bp
    from app.routes.kanban import kanban_bp
    from app.routes.setup import setup_bp
    from app.routes.user import user_bp
    from app.routes.time_entry_templates import time_entry_templates_bp
    from app.routes.saved_filters import saved_filters_bp
    from app.routes.settings import settings_bp
    from app.routes.weekly_goals import weekly_goals_bp
    from app.routes.expenses import expenses_bp
    from app.routes.permissions import permissions_bp
    from app.routes.calendar import calendar_bp
    from app.routes.expense_categories import expense_categories_bp
    from app.routes.mileage import mileage_bp
    from app.routes.per_diem import per_diem_bp
    from app.routes.budget_alerts import budget_alerts_bp
    from app.routes.import_export import import_export_bp
    from app.routes.webhooks import webhooks_bp
    from app.routes.client_portal import client_portal_bp
    from app.routes.quotes import quotes_bp
    from app.routes.inventory import inventory_bp
    from app.routes.contacts import contacts_bp
    from app.routes.deals import deals_bp
    from app.routes.leads import leads_bp
    from app.routes.kiosk import kiosk_bp
    from app.routes.link_templates import link_templates_bp
    from app.routes.custom_field_definitions import custom_field_definitions_bp
    from app.routes.custom_reports import custom_reports_bp
    from app.routes.salesman_reports import salesman_reports_bp

    try:
        from app.routes.audit_logs import audit_logs_bp
        app.register_blueprint(audit_logs_bp)
    except Exception as e:
        if logger:
            logger.warning("Could not register audit_logs blueprint: %s", e)

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(timer_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(api_v1_bp)
    app.register_blueprint(api_v1_time_entries_bp)
    app.register_blueprint(api_v1_projects_bp)
    app.register_blueprint(api_v1_tasks_bp)
    app.register_blueprint(api_v1_clients_bp)
    app.register_blueprint(api_v1_invoices_bp)
    app.register_blueprint(api_v1_expenses_bp)
    app.register_blueprint(api_v1_payments_bp)
    app.register_blueprint(api_v1_mileage_bp)
    app.register_blueprint(api_v1_deals_bp)
    app.register_blueprint(api_v1_leads_bp)
    app.register_blueprint(api_v1_contacts_bp)
    app.register_blueprint(api_docs_bp)
    app.register_blueprint(swaggerui_blueprint)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(issues_bp)
    app.register_blueprint(invoices_bp)
    app.register_blueprint(recurring_invoices_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(clients_bp)
    app.register_blueprint(client_notes_bp)
    app.register_blueprint(client_portal_bp)
    app.register_blueprint(comments_bp)
    app.register_blueprint(kanban_bp)
    app.register_blueprint(setup_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(time_entry_templates_bp)
    app.register_blueprint(saved_filters_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(weekly_goals_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(permissions_bp)
    app.register_blueprint(calendar_bp)
    app.register_blueprint(expense_categories_bp)
    app.register_blueprint(mileage_bp)
    app.register_blueprint(per_diem_bp)
    app.register_blueprint(budget_alerts_bp)
    app.register_blueprint(import_export_bp)
    app.register_blueprint(webhooks_bp)
    app.register_blueprint(quotes_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(kiosk_bp)
    app.register_blueprint(contacts_bp)
    app.register_blueprint(deals_bp)
    app.register_blueprint(leads_bp)
    app.register_blueprint(link_templates_bp)
    app.register_blueprint(custom_field_definitions_bp)
    app.register_blueprint(custom_reports_bp)
    app.register_blueprint(salesman_reports_bp)

    _register_optional_blueprints(app, logger)


def _register_optional_blueprints(app, logger=None):
    """Register optional/feature blueprints that may be missing in minimal installs."""
    optional = [
        ("app.routes.project_templates", "project_templates_bp"),
        ("app.routes.invoice_approvals", "invoice_approvals_bp"),
        ("app.routes.payment_gateways", "payment_gateways_bp"),
        ("app.routes.scheduled_reports", "scheduled_reports_bp"),
        ("app.routes.integrations", "integrations_bp"),
        ("app.routes.push_notifications", "push_bp"),
        ("app.routes.gantt", "gantt_bp"),
        ("app.routes.workflows", "workflows_bp"),
        ("app.routes.time_approvals", "time_approvals_bp"),
        ("app.routes.activity_feed", "activity_feed_bp"),
        ("app.routes.workforce", "workforce_bp"),
        ("app.routes.recurring_tasks", "recurring_tasks_bp"),
        ("app.routes.team_chat", "team_chat_bp"),
        ("app.routes.client_portal_customization", "client_portal_customization_bp"),
    ]
    for module_path, attr in optional:
        try:
            mod = __import__(module_path, fromlist=[attr])
            bp = getattr(mod, attr)
            app.register_blueprint(bp)
        except Exception as e:
            if logger:
                logger.warning("Could not register %s blueprint: %s", module_path.split(".")[-1], e)
