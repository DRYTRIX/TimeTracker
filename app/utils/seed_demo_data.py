"""
Production-safe sample data for DEMO_MODE public demos.

Creates a small set of clients, projects, and time entries so visitors
see a populated app instead of an empty dashboard. Idempotent via
installation.json flag `demo_sample_data_seeded`.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from app import db
from app.models import Client, Project, Settings, TimeEntry, User
from app.utils.installation import get_installation_config


def seed_demo_sample_data(app) -> bool:
    """
    Seed browseable demo sample data when DEMO_MODE is enabled.

    Returns True if demo seeding ran or was already complete, False if skipped.
    """
    if not app.config.get("DEMO_MODE"):
        return False

    installation_config = get_installation_config()

    # Mark setup complete so / never redirects to the first-run wizard
    if not installation_config.is_setup_complete():
        installation_config.mark_setup_complete(telemetry_enabled=False)

    if installation_config.is_demo_sample_data_seeded():
        return True

    demo_username = (app.config.get("DEMO_USERNAME") or "demo").strip().lower()
    demo_user = User.query.filter_by(username=demo_username).first()
    if not demo_user:
        return False

    settings = Settings.get_settings()
    if settings:
        if not (settings.company_name or "").strip() or settings.company_name == "Your Company Name":
            settings.company_name = "Demo Company"
            settings.company_email = settings.company_email or "demo@example.com"
            settings.currency = settings.currency or "EUR"

    # Avoid clobbering a curated demo DB that already has projects
    if Project.query.count() > 0:
        installation_config.mark_demo_sample_data_seeded()
        return True

    clients_spec = [
        "Acme Design",
        "Nordic Consulting",
        "Bright Labs",
    ]
    clients = []
    for name in clients_spec:
        c = Client(name=name, created_by=demo_user.id)
        c.status = "active"
        db.session.add(c)
        clients.append(c)
    db.session.flush()

    projects = []
    project_specs = [
        (0, "Website redesign", "Marketing site rebuild", Decimal("95.00")),
        (0, "Brand guidelines", "Visual identity package", Decimal("110.00")),
        (1, "Monthly retainer", "Ongoing consulting hours", Decimal("120.00")),
        (2, "iOS MVP", "First release of the mobile app", Decimal("130.00")),
    ]
    for client_idx, name, description, rate in project_specs:
        p = Project(
            name=name,
            client_id=clients[client_idx].id,
            description=description,
            billable=True,
            status="active",
            hourly_rate=rate,
            created_by=demo_user.id,
        )
        db.session.add(p)
        projects.append(p)
    db.session.flush()

    now = datetime.utcnow()
    entry_specs = [
        (0, 2.5, "Homepage layout and hero"),
        (0, 1.75, "Responsive nav polish"),
        (1, 3.0, "Typography and color tokens"),
        (2, 4.0, "Weekly status call + deliverables"),
        (2, 2.25, "Report drafting"),
        (3, 5.0, "Auth flow and onboarding screens"),
        (3, 3.5, "API client scaffolding"),
    ]
    for i, (project_idx, hours, notes) in enumerate(entry_specs):
        start = now - timedelta(days=(6 - i), hours=9)
        end = start + timedelta(hours=hours)
        entry = TimeEntry(
            user_id=demo_user.id,
            project_id=projects[project_idx].id,
            client_id=projects[project_idx].client_id,
            start_time=start,
            end_time=end,
            notes=notes,
            billable=True,
            source="manual",
        )
        entry.calculate_duration()
        db.session.add(entry)

    db.session.commit()
    installation_config.mark_demo_sample_data_seeded()
    print("Seeded DEMO_MODE sample clients, projects, and time entries")
    return True
