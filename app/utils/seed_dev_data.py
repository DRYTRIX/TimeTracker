"""
Development-only seed: populate the database with lots of test data.

This module must only be run when FLASK_ENV=development. It creates
clients, projects, tasks, time entries, expenses, comments, inventory
(warehouses, stock items, movements), and finance data (currencies,
tax rules, invoices, payments) for realistic local testing.
"""

import os
from datetime import datetime, timedelta, date, time
from decimal import Decimal

from app import db
from app.models import (
    User,
    Client,
    Project,
    Task,
    TimeEntry,
    Expense,
    ExpenseCategory,
    Comment,
    Warehouse,
    StockItem,
    WarehouseStock,
    StockMovement,
    Currency,
    TaxRule,
    Invoice,
    InvoiceItem,
    Payment,
)


# Default password for seeded dev users (development only)
DEV_USER_PASSWORD = "dev"


def _ensure_development():
    """Raise if not in development environment."""
    flask_env = os.getenv("FLASK_ENV", "production")
    if flask_env != "development":
        raise RuntimeError(
            "Seed is only allowed when FLASK_ENV=development. "
            f"Current FLASK_ENV={flask_env!r}. "
            "Set FLASK_ENV=development and try again."
        )


# Deterministic data for reproducible seeds
CLIENT_NAMES = [
    "Acme Corp", "Beta Industries", "Gamma Labs", "Delta Solutions", "Epsilon Ltd",
    "Zeta Consulting", "Eta Design", "Theta Systems", "Iota Media", "Kappa Finance",
    "Lambda Software", "Mu Analytics", "Nu Robotics", "Xi Healthcare", "Omicron Retail",
    "Pi Networks", "Rho Logistics", "Sigma Legal", "Tau Construction", "Upsilon Foods",
    "Phi Education", "Chi Marketing", "Psi Energy", "Omega Manufacturing",
]

PROJECT_NAME_PARTS = [
    "Website", "Mobile App", "API", "Dashboard", "Integration", "Migration",
    "Redesign", "Maintenance", "Consulting", "Audit", "Training", "Support",
    "Phase 1", "Phase 2", "Q1 Campaign", "Q2 Campaign", "Backend", "Frontend",
]

TASK_NAME_TEMPLATES = [
    "Requirements review", "Design mockups", "Implementation", "Code review",
    "Testing", "Documentation", "Deployment", "Bug fixes", "Refactoring",
    "Meeting", "Research", "Sprint planning", "Retrospective", "Client call",
    "API design", "Database schema", "UI components", "E2E tests",
]

EXPENSE_CATEGORIES_SEED = [
    ("Travel", "travel", "#3b82f6"),
    ("Meals", "meals", "#22c55e"),
    ("Accommodation", "accommodation", "#8b5cf6"),
    ("Supplies", "supplies", "#f59e0b"),
    ("Software", "software", "#06b6d4"),
    ("Equipment", "equipment", "#ec4899"),
    ("Other", "other", "#6b7280"),
]

TAG_LISTS = [
    "dev,backend", "frontend,ui", "meeting", "urgent", "review", "bugfix",
    "feature", "docs", "testing", "sprint",
]

# Inventory seed data
WAREHOUSE_NAMES = [
    ("Main Warehouse", "WH-MAIN"),
    ("Secondary Storage", "WH-SEC"),
    ("Office Supplies", "WH-OFF"),
]

STOCK_ITEM_SEED = [
    ("LAPTOP-001", "Laptop Pro 15", "Electronics", 899.00, 1099.00),
    ("MONITOR-01", "24\" Monitor", "Electronics", 180.00, 249.00),
    ("KEYB-001", "Wireless Keyboard", "Peripherals", 45.00, 69.00),
    ("MOUSE-001", "Wireless Mouse", "Peripherals", 25.00, 39.00),
    ("CABLE-HDMI", "HDMI Cable 2m", "Cables", 8.00, 14.00),
    ("DESK-001", "Standing Desk", "Furniture", 350.00, 499.00),
    ("CHAIR-01", "Ergonomic Chair", "Furniture", 280.00, 399.00),
    ("NOTEBOOK", "A4 Notebook Pack", "Office", 4.50, 8.00),
    ("PEN-PACK", "Pen Set (10)", "Office", 12.00, 19.00),
    ("HEADPH-01", "Headphones", "Electronics", 60.00, 89.00),
    ("WEBCAM-1", "HD Webcam", "Electronics", 55.00, 79.00),
    ("DOCK-001", "USB-C Dock", "Peripherals", 120.00, 169.00),
    ("USB-32G", "USB Stick 32GB", "Storage", 10.00, 18.00),
    ("SCREEN-P", "Screen Protector", "Accessories", 15.00, 24.00),
    ("BAG-001", "Laptop Bag", "Accessories", 35.00, 54.00),
]


def _make_time_entry(user_id, project_id, task_id, client_id, day_offset, hour_start, duration_minutes, notes=None, tags=None):
    """Create a closed time entry (with end_time) for a given day (naive local datetimes)."""
    from app.utils.timezone import get_timezone_obj
    tz = get_timezone_obj()
    base_date = (datetime.now(tz) - timedelta(days=day_offset)).date()
    start_naive = datetime.combine(base_date, time(hour_start, 0))
    end_naive = start_naive + timedelta(minutes=duration_minutes)
    entry = TimeEntry(
        user_id=user_id,
        project_id=project_id,
        task_id=task_id,
        client_id=client_id,
        start_time=start_naive,
        end_time=end_naive,
        notes=notes,
        tags=tags,
        source="manual",
        billable=True,
        paid=False,
    )
    entry.calculate_duration()
    return entry


def run_seed(extra_users=4, clients_count=20, projects_per_client=4, tasks_per_project=12,
             time_entries_per_task_approx=8, days_back=120, expense_categories=True,
             expenses_count=50, comments_count=80, warehouses_count=3, stock_items_count=15,
             stock_movements_count=40, currencies=True, tax_rules_count=2, invoices_count=25,
             payments_per_invoice_approx=1):
    """
    Seed the database with development test data.

    Only runs when FLASK_ENV=development. Creates:
    - Extra dev users (if extra_users > 0)
    - Many clients and projects
    - Tasks per project
    - Time entries spread over the last days_back days
    - Expense categories and expenses
    - Comments on tasks
    - Inventory: warehouses, stock items, warehouse stock levels, stock movements
    - Finance: currencies, tax rules, invoices with line items, payments

    Returns a dict with counts of created entities.
    """
    _ensure_development()

    counts = {
        "users": 0,
        "clients": 0,
        "projects": 0,
        "tasks": 0,
        "time_entries": 0,
        "expense_categories": 0,
        "expenses": 0,
        "comments": 0,
        "warehouses": 0,
        "stock_items": 0,
        "warehouse_stock": 0,
        "stock_movements": 0,
        "currencies": 0,
        "tax_rules": 0,
        "invoices": 0,
        "invoice_items": 0,
        "payments": 0,
    }

    # Ensure we have at least one user (admin from reset-dev-db or init_db)
    users = list(User.query.filter_by(is_active=True).all())
    if not users:
        admin_username = os.getenv("ADMIN_USERNAMES", "admin").split(",")[0].strip().lower()
        admin = User(username=admin_username, role="admin")
        admin.is_active = True
        admin.set_password(DEV_USER_PASSWORD)
        db.session.add(admin)
        db.session.flush()
        users = [admin]
        counts["users"] += 1

    # Create extra dev users
    for i in range(extra_users):
        uname = f"devuser{i + 1}"
        if User.query.filter_by(username=uname).first():
            continue
        u = User(username=uname, role="user", full_name=f"Dev User {i + 1}")
        u.is_active = True
        u.set_password(DEV_USER_PASSWORD)
        db.session.add(u)
        counts["users"] += 1
    db.session.flush()
    users = list(User.query.filter_by(is_active=True).all())

    # Clients
    existing_client_names = {c.name for c in Client.query.all()}
    clients_to_use = []
    for name in CLIENT_NAMES[:clients_count]:
        if name in existing_client_names:
            clients_to_use.append(Client.query.filter_by(name=name).first())
            continue
        c = Client(
            name=name,
            description=f"Seed client: {name}",
            contact_person=f"Contact at {name}",
            email=f"contact@{name.lower().replace(' ', '')}.example.com",
            phone="+1 555 000 0000",
            address="123 Seed Street, Dev City",
            default_hourly_rate=Decimal("85.00"),
        )
        db.session.add(c)
        counts["clients"] += 1
        clients_to_use.append(c)
    db.session.flush()
    if not clients_to_use:
        clients_to_use = Client.query.limit(clients_count).all()

    # Projects per client
    projects_to_use = []
    for client in clients_to_use:
        for pidx in range(projects_per_client):
            pname = f"{PROJECT_NAME_PARTS[pidx % len(PROJECT_NAME_PARTS)]} - {client.name}"
            if Project.query.filter_by(name=pname).first():
                continue
            code = f"{client.name[:2].upper()}{pidx:02d}" if pidx < 100 else None
            proj = Project(
                name=pname,
                client_id=client.id,
                description=f"Seed project for {client.name}",
                billable=True,
                hourly_rate=client.default_hourly_rate or Decimal("85.00"),
                status="active",
                code=code,
            )
            proj.estimated_hours = round(40 + (pidx * 10), 1)
            db.session.add(proj)
            counts["projects"] += 1
            projects_to_use.append(proj)
    db.session.flush()
    if not projects_to_use:
        projects_to_use = Project.query.limit(clients_count * projects_per_client).all()

    # Tasks per project
    tasks_to_use = []
    for proj in projects_to_use:
        creator = users[proj.id % len(users)]
        for tidx in range(tasks_per_project):
            tname = f"{TASK_NAME_TEMPLATES[tidx % len(TASK_NAME_TEMPLATES)]} ({tidx + 1})"
            statuses = ["todo", "in_progress", "review", "done", "done", "done"]
            status = statuses[tidx % len(statuses)]
            task = Task(
                project_id=proj.id,
                name=tname,
                description=f"Seed task for {proj.name}",
                status=status,
                priority=["low", "medium", "high", "urgent"][tidx % 4],
                estimated_hours=round(2 + (tidx % 8), 1),
                created_by=creator.id,
                assigned_to=users[(proj.id + tidx) % len(users)].id if users else None,
            )
            db.session.add(task)
            counts["tasks"] += 1
            tasks_to_use.append(task)
    db.session.flush()
    if not tasks_to_use:
        tasks_to_use = Task.query.limit(len(projects_to_use) * tasks_per_project).all()

    # Time entries: spread over past days_back, across users/projects/tasks
    te_count_target = min(
        len(tasks_to_use) * time_entries_per_task_approx,
        1500,
    )
    te_created = 0
    for i in range(te_count_target):
        task = tasks_to_use[i % len(tasks_to_use)]
        proj = task.project
        user = users[i % len(users)]
        day_offset = i % days_back
        hour_start = 8 + (i % 8)
        duration_minutes = [15, 30, 45, 60, 90, 120][i % 6]
        notes = f"Seed entry {i + 1}"
        tags = TAG_LISTS[i % len(TAG_LISTS)]
        entry = _make_time_entry(
            user_id=user.id,
            project_id=proj.id,
            task_id=task.id,
            client_id=proj.client_id,
            day_offset=day_offset,
            hour_start=hour_start,
            duration_minutes=duration_minutes,
            notes=notes,
            tags=tags,
        )
        db.session.add(entry)
        te_created += 1
        if te_created % 200 == 0:
            db.session.flush()
    counts["time_entries"] = te_created

    # Expense categories
    if expense_categories:
        for name, code, color in EXPENSE_CATEGORIES_SEED:
            if ExpenseCategory.query.filter_by(name=name).first():
                continue
            cat = ExpenseCategory(name=name, code=code, color=color)
            db.session.add(cat)
            counts["expense_categories"] += 1
        db.session.flush()
    categories = list(ExpenseCategory.query.all())

    # Expenses
    for i in range(expenses_count):
        user = users[i % len(users)]
        proj = projects_to_use[i % len(projects_to_use)] if projects_to_use else None
        client = proj.client_obj if proj else (clients_to_use[i % len(clients_to_use)] if clients_to_use else None)
        cat_name, cat_code, _ = EXPENSE_CATEGORIES_SEED[i % len(EXPENSE_CATEGORIES_SEED)]
        expense_date = date.today() - timedelta(days=i % 90)
        amt = Decimal(str(round(10 + (i % 200), 2)))
        exp = Expense(
            user_id=user.id,
            project_id=proj.id if proj else None,
            client_id=client.id if client else None,
            title=f"Seed expense {i + 1}",
            category=cat_code,
            amount=amt,
            currency_code="EUR",
            expense_date=expense_date,
            status="approved",
        )
        db.session.add(exp)
        counts["expenses"] += 1
    db.session.flush()

    # Comments on tasks
    comment_texts = [
        "Looks good, please proceed.",
        "Can we align this with the spec?",
        "Done from my side.",
        "Blocked by backend API.",
        "Reviewed and approved.",
        "Minor tweaks requested.",
        "Ready for QA.",
    ]
    for i in range(comments_count):
        task = tasks_to_use[i % len(tasks_to_use)]
        author = users[i % len(users)]
        text = comment_texts[i % len(comment_texts)]
        c = Comment(
            content=text,
            task_id=task.id,
            user_id=author.id,
            is_internal=True,
        )
        db.session.add(c)
        counts["comments"] += 1

    db.session.flush()

    # --- Inventory: warehouses, stock items, warehouse stock, stock movements ---
    creator = users[0]
    warehouses_to_use = []
    for name, code in WAREHOUSE_NAMES[:warehouses_count]:
        if Warehouse.query.filter_by(code=code).first():
            warehouses_to_use.append(Warehouse.query.filter_by(code=code).first())
            continue
        wh = Warehouse(name=name, code=code, created_by=creator.id, address="123 Seed Street, Dev City")
        db.session.add(wh)
        counts["warehouses"] += 1
        warehouses_to_use.append(wh)
    db.session.flush()
    if not warehouses_to_use:
        warehouses_to_use = Warehouse.query.limit(warehouses_count).all()

    stock_items_to_use = []
    for sku, name, category, cost, price in STOCK_ITEM_SEED[:stock_items_count]:
        if StockItem.query.filter_by(sku=sku).first():
            stock_items_to_use.append(StockItem.query.filter_by(sku=sku).first())
            continue
        item = StockItem(
            sku=sku,
            name=name,
            created_by=creator.id,
            category=category,
            unit="pcs",
            default_cost=Decimal(str(cost)),
            default_price=Decimal(str(price)),
            currency_code="EUR",
        )
        db.session.add(item)
        counts["stock_items"] += 1
        stock_items_to_use.append(item)
    db.session.flush()
    if not stock_items_to_use:
        stock_items_to_use = StockItem.query.limit(stock_items_count).all()

    for wh in warehouses_to_use:
        for item in stock_items_to_use:
            if WarehouseStock.query.filter_by(warehouse_id=wh.id, stock_item_id=item.id).first():
                continue
            qty = (wh.id + item.id) % 50 + 10
            ws = WarehouseStock(
                warehouse_id=wh.id,
                stock_item_id=item.id,
                quantity_on_hand=Decimal(str(qty)),
                quantity_reserved=0,
                location=f"A-{item.id % 10}",
            )
            db.session.add(ws)
            counts["warehouse_stock"] += 1
    db.session.flush()

    for i in range(stock_movements_count):
        item = stock_items_to_use[i % len(stock_items_to_use)]
        wh = warehouses_to_use[i % len(warehouses_to_use)]
        user = users[i % len(users)]
        movement_type = ["adjustment", "purchase", "adjustment", "return"][i % 4]
        qty = (i % 20) + 1 if movement_type in ("purchase", "return") else (i % 5) - 2
        if movement_type == "adjustment" and qty == 0:
            qty = 1
        mov = StockMovement(
            movement_type=movement_type,
            stock_item_id=item.id,
            warehouse_id=wh.id,
            quantity=qty,
            moved_by=user.id,
            reason=f"Seed movement {i + 1}",
        )
        db.session.add(mov)
        counts["stock_movements"] += 1
    db.session.flush()

    # --- Finance: currencies, tax rules, invoices, invoice items, payments ---
    if currencies:
        for code, name, symbol in [("EUR", "Euro", "€"), ("USD", "US Dollar", "$")]:
            if Currency.query.get(code):
                continue
            cur = Currency(code=code, name=name, symbol=symbol, decimal_places=2, is_active=True)
            db.session.add(cur)
            counts["currencies"] += 1
        db.session.flush()

    for i in range(tax_rules_count):
        name = "VAT 21%" if i == 0 else "VAT 6%"
        if TaxRule.query.filter_by(name=name).first():
            continue
        tr = TaxRule()
        tr.name = name
        tr.rate_percent = Decimal("21") if i == 0 else Decimal("6")
        tr.country = "BE"
        tr.tax_code = "VAT"
        tr.active = True
        db.session.add(tr)
        counts["tax_rules"] += 1
    db.session.flush()

    invoice_number_base = 1000
    for i in range(invoices_count):
        proj = projects_to_use[i % len(projects_to_use)]
        client = proj.client_obj
        inv_num = f"INV-SEED-{invoice_number_base + i}"
        if Invoice.query.filter_by(invoice_number=inv_num).first():
            continue
        issue_d = date.today() - timedelta(days=30 + (i % 60))
        due_d = issue_d + timedelta(days=30)
        inv = Invoice(
            invoice_number=inv_num,
            project_id=proj.id,
            client_name=client.name,
            due_date=due_d,
            created_by=users[i % len(users)].id,
            client_id=client.id,
            issue_date=issue_d,
            tax_rate=Decimal("21"),
            currency_code="EUR",
        )
        db.session.add(inv)
        db.session.flush()
        # Add 1–3 line items per invoice
        for j in range(1 + (i % 3)):
            desc = f"Seed line {j + 1} - {proj.name}"
            qty = Decimal(str(1 + (i + j) % 5))
            unit_price = proj.hourly_rate or Decimal("85")
            item = InvoiceItem(inv.id, desc, qty, unit_price)
            db.session.add(item)
            counts["invoice_items"] += 1
        inv.calculate_totals()
        inv.status = ["draft", "sent", "sent", "paid", "paid"][i % 5]
        if inv.status == "paid":
            inv.payment_status = "fully_paid"
            inv.amount_paid = inv.total_amount
            inv.payment_date = due_d - timedelta(days=i % 10)
        counts["invoices"] += 1
    db.session.flush()

    # Record Payment rows for paid/partially paid invoices
    paid_invoices = [inv for inv in Invoice.query.filter(Invoice.status.in_(["paid", "sent"])).all() if inv.total_amount and inv.total_amount > 0]
    for inv in paid_invoices[: min(20, len(paid_invoices))]:
        num_payments = min(1 + (inv.id % 2), payments_per_invoice_approx)
        amount_per = (inv.total_amount or 0) / num_payments
        for k in range(num_payments):
            p = Payment()
            p.invoice_id = inv.id
            p.amount = amount_per
            p.currency = inv.currency_code or "EUR"
            p.payment_date = (inv.payment_date or inv.due_date) - timedelta(days=k * 5)
            p.method = "bank_transfer"
            p.reference = f"SEED-{inv.id}-{k}"
            p.status = "completed"
            p.received_by = inv.created_by
            db.session.add(p)
            counts["payments"] += 1

    db.session.commit()
    return counts
