"""Invoice time links: one table that says which invoice line bills a time entry.

Backfills links from the comma-separated invoice_items.time_entry_ids and from the prepaid
hours ledger. invoice_items.time_entry_ids stays as a cache; only draft lines change, dropping the
entries that went to another invoice or line (so the draft can still be saved).

It also fixes old cancelled invoices, which held on to their hours: their time entries are no
longer paid (unless another invoice now bills them), and their project costs, expenses and
prepaid hours are released. The downgrade drops the table; these fixes are not undone.

Revision ID: 219_add_invoice_time_links
Revises: 218_project_cost_expense_categories
"""

import logging
import warnings
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "219_add_invoice_time_links"
down_revision = "218_project_cost_expense_categories"
branch_labels = None
depends_on = None

logger = logging.getLogger("alembic.runtime.migration")

TABLE = "invoice_time_links"
# One active link with a line per entry, and one without a line (prepaid hours)
ACTIVE_LINE_INDEX = "uq_invoice_time_links_active_line"
ACTIVE_PREPAID_INDEX = "uq_invoice_time_links_active_prepaid"
ACTIVE_LINE_CONDITION = "released_at IS NULL AND invoice_item_id IS NOT NULL"
ACTIVE_PREPAID_CONDITION = "released_at IS NULL AND invoice_item_id IS NULL"
CANCELLED_REASON = "migration: invoice cancelled"
HOURS_PLACES = Decimal("0.0001")


def _has_table(inspector, name):
    try:
        return name in inspector.get_table_names()
    except Exception:
        return False


def _hours(seconds):
    return (Decimal(int(seconds or 0)) / Decimal(3600)).quantize(HOURS_PLACES)


def _parse_ids(csv):
    ids = []
    for part in (csv or "").split(","):
        part = part.strip()
        if part.isdigit() and int(part) not in ids:
            ids.append(int(part))
    return ids


def _as_datetime(value):
    if value is None:
        return datetime.min
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return datetime.min


def build_links(invoices, items, entries, consumptions, now):
    """Work out the link rows to insert.

    invoices: {id: {"status", "issue_date", "created_at"}}
    items: [(item_id, invoice_id, time_entry_ids)]
    entries: {entry_id: duration_seconds}
    consumptions: [(time_entry_id, invoice_id, seconds_consumed)]

    An entry on lines of several invoices keeps its link on the latest issued invoice by date (not
    cancelled, not a draft); a draft keeps it only when no issued invoice has it. The others are
    logged. An entry on several lines of that invoice keeps
    the first line (lowest id); the others are logged. Links of cancelled invoices are released.
    """
    prepaid_seconds = defaultdict(int)  # (entry_id, invoice_id) -> seconds covered by prepaid hours
    for entry_id, invoice_id, seconds in consumptions:
        if invoice_id is not None:
            prepaid_seconds[(entry_id, invoice_id)] += int(seconds or 0)

    # entry_id -> invoice_id -> [(item_id or None, hours)]
    candidates = defaultdict(lambda: defaultdict(list))
    for item_id, invoice_id, csv in items:
        if invoice_id not in invoices:
            continue
        for entry_id in _parse_ids(csv):
            if entry_id not in entries:
                logger.warning("invoice_time_links: invoice item %s lists missing time entry %s", item_id, entry_id)
                continue
            seconds = int(entries[entry_id] or 0) - prepaid_seconds.get((entry_id, invoice_id), 0)
            candidates[entry_id][invoice_id].append((item_id, _hours(max(seconds, 0))))

    for (entry_id, invoice_id), seconds in sorted(prepaid_seconds.items()):
        if invoice_id not in invoices or entry_id not in entries:
            continue
        if invoice_id in candidates.get(entry_id, {}):
            continue  # the entry has a line on that invoice already
        candidates[entry_id][invoice_id].append((None, _hours(seconds)))

    def sort_key(invoice_id):
        inv = invoices[invoice_id]
        return (_as_datetime(inv["issue_date"]), _as_datetime(inv["created_at"]), invoice_id)

    rows = []
    for entry_id in sorted(candidates):
        by_invoice = candidates[entry_id]
        live = [i for i in by_invoice if invoices[i]["status"] != "cancelled"]
        # Issued invoices (not drafts) come first; a draft gets the entry only if no issued invoice has it
        issued = sorted((i for i in live if invoices[i]["status"] != "draft"), key=sort_key)
        drafts = sorted((i for i in live if invoices[i]["status"] == "draft"), key=sort_key)
        winner = issued[-1] if issued else (drafts[-1] if drafts else None)
        for invoice_id in sorted((i for i in live if i != winner), key=sort_key):
            logger.warning(
                "invoice_time_links: time entry %s is on invoices %s; linked to invoice %s only, skipped invoice %s",
                entry_id,
                sorted(by_invoice),
                winner,
                invoice_id,
            )
        for invoice_id, lines in by_invoice.items():
            cancelled = invoices[invoice_id]["status"] == "cancelled"
            if not cancelled and invoice_id != winner:
                continue
            if not cancelled and len(lines) > 1:
                lines = sorted(lines, key=lambda line: (line[0] is None, line[0] or 0))
                logger.warning(
                    "invoice_time_links: time entry %s is on lines %s of invoice %s; linked to line %s only",
                    entry_id,
                    [line[0] for line in lines],
                    invoice_id,
                    lines[0][0],
                )
                lines = lines[:1]
            for item_id, hours in lines:
                rows.append(
                    {
                        "time_entry_id": entry_id,
                        "invoice_id": invoice_id,
                        "invoice_item_id": item_id,
                        "hours": hours,
                        "created_at": now,
                        "created_by": None,
                        "released_at": now if cancelled else None,
                        "released_reason": CANCELLED_REASON if cancelled else None,
                    }
                )
    return rows


def lost_draft_lines(invoices, items, rows):
    """(item_id, entry_id) for each draft line that lists an entry its link went elsewhere.

    A draft that lost an entry to another invoice, or to another line of itself, would otherwise
    refuse to save: the entry no longer belongs to that line.
    """
    linked = {(row["time_entry_id"], row["invoice_item_id"]) for row in rows}
    lost = []
    for item_id, invoice_id, csv in items:
        inv = invoices.get(invoice_id)
        if not inv or inv["status"] != "draft":
            continue
        for entry_id in _parse_ids(csv):
            if (entry_id, item_id) not in linked:
                lost.append((item_id, entry_id))
    return lost


def backfill(bind, now=None):
    """Create links for existing invoices. Returns the number of links created."""
    now = now or datetime.utcnow()
    meta = sa.MetaData()
    with warnings.catch_warnings():
        # SQLite reflection warns about foreign keys older migrations left unnamed; harmless here
        warnings.simplefilter("ignore", sa.exc.SAWarning)
        invoices_t = sa.Table("invoices", meta, autoload_with=bind)
        items_t = sa.Table("invoice_items", meta, autoload_with=bind)
        entries_t = sa.Table("time_entries", meta, autoload_with=bind)
        links_t = sa.Table(TABLE, meta, autoload_with=bind)

    invoices = {
        row.id: {"status": row.status, "issue_date": row.issue_date, "created_at": row.created_at}
        for row in bind.execute(
            sa.select(invoices_t.c.id, invoices_t.c.status, invoices_t.c.issue_date, invoices_t.c.created_at)
        )
    }
    items = [
        (row.id, row.invoice_id, row.time_entry_ids)
        for row in bind.execute(
            sa.select(items_t.c.id, items_t.c.invoice_id, items_t.c.time_entry_ids).where(
                items_t.c.time_entry_ids.isnot(None), items_t.c.time_entry_ids != ""
            )
        )
    ]
    consumptions = []
    if _has_table(inspect(bind), "client_prepaid_consumptions"):
        ledger_t = sa.Table("client_prepaid_consumptions", meta, autoload_with=bind)
        consumptions = [
            (row.time_entry_id, row.invoice_id, row.seconds_consumed)
            for row in bind.execute(
                sa.select(ledger_t.c.time_entry_id, ledger_t.c.invoice_id, ledger_t.c.seconds_consumed)
            )
        ]

    wanted = set()
    for _item_id, _invoice_id, csv in items:
        wanted.update(_parse_ids(csv))
    wanted.update(row[0] for row in consumptions)
    entries = {}
    wanted = sorted(wanted)
    for start in range(0, len(wanted), 500):
        chunk = wanted[start : start + 500]
        for row in bind.execute(
            sa.select(entries_t.c.id, entries_t.c.duration_seconds).where(entries_t.c.id.in_(chunk))
        ):
            entries[row.id] = row.duration_seconds

    rows = build_links(invoices, items, entries, consumptions, now)
    if rows:
        bind.execute(links_t.insert(), rows)
    logger.info("invoice_time_links: created %s links", len(rows))

    # Drafts drop the entries they lost from their lines' time_entry_ids
    lost = defaultdict(list)
    for item_id, entry_id in lost_draft_lines(invoices, items, rows):
        lost[item_id].append(entry_id)
    csv_by_item = {item_id: csv for item_id, _invoice_id, csv in items}
    for item_id, entry_ids in sorted(lost.items()):
        kept = [i for i in _parse_ids(csv_by_item[item_id]) if i not in entry_ids]
        bind.execute(
            items_t.update()
            .where(items_t.c.id == item_id)
            .values(time_entry_ids=",".join(str(i) for i in kept) or None)
        )
        logger.warning(
            "invoice_time_links: draft invoice line %s no longer lists time entries %s (linked elsewhere)",
            item_id,
            entry_ids,
        )

    cancelled_ids = sorted(i for i, inv in invoices.items() if inv["status"] == "cancelled")
    if cancelled_ids:
        release_cancelled(bind, meta, cancelled_ids, now)
    return len(rows)


def release_cancelled(bind, meta, cancelled_ids, now):
    """Fix old cancelled invoices: let go of what they still hold, as cancelling does from now on.

    Time entries keep "paid" and the invoice number no more, unless another invoice now bills them:
    then they keep "paid" under that invoice's number. Project costs and expenses are
    billable again; prepaid hours go back to the client's plan (the ledger rows are removed and
    their entries are billable again).
    """
    invoices_t = sa.Table("invoices", meta, autoload_with=bind)
    entries_t = sa.Table("time_entries", meta, autoload_with=bind)
    numbers = {
        row.invoice_number
        for row in bind.execute(sa.select(invoices_t.c.invoice_number).where(invoices_t.c.id.in_(cancelled_ids)))
        if row.invoice_number
    }
    # A number still used by an invoice that is not cancelled is left alone
    numbers -= {
        row.invoice_number
        for row in bind.execute(
            sa.select(invoices_t.c.invoice_number).where(
                invoices_t.c.status != "cancelled", invoices_t.c.invoice_number.in_(sorted(numbers) or [""])
            )
        )
    }
    if numbers:
        links_t = sa.Table(TABLE, meta, autoload_with=bind)
        # An entry another invoice (not cancelled) now bills keeps its paid flag
        still_billed = sa.exists().where(
            sa.and_(links_t.c.time_entry_id == entries_t.c.id, links_t.c.released_at.is_(None))
        )
        result = bind.execute(
            entries_t.update()
            .where(
                entries_t.c.paid == sa.true(),
                entries_t.c.invoice_number.in_(sorted(numbers)),
                ~still_billed,
            )
            .values(paid=False, invoice_number=None)
        )
        logger.info("invoice_time_links: cancelled invoices: %s time entries no longer paid", result.rowcount)
        # The rest stay paid under the invoice that bills them now, so cancelling it later lets them go
        live_number = (
            sa.select(invoices_t.c.invoice_number)
            .select_from(links_t.join(invoices_t, invoices_t.c.id == links_t.c.invoice_id))
            .where(links_t.c.time_entry_id == entries_t.c.id, links_t.c.released_at.is_(None))
            .order_by(links_t.c.invoice_item_id.is_(None), links_t.c.id)
            .limit(1)
            .scalar_subquery()
        )
        result = bind.execute(
            entries_t.update()
            .where(entries_t.c.paid == sa.true(), entries_t.c.invoice_number.in_(sorted(numbers)), still_billed)
            .values(invoice_number=live_number)
        )
        logger.info(
            "invoice_time_links: cancelled invoices: %s paid time entries moved to their live invoice", result.rowcount
        )

    inspector = inspect(bind)
    for table_name in ("project_costs", "expenses"):
        if not _has_table(inspector, table_name):
            continue
        table = sa.Table(table_name, meta, autoload_with=bind)
        if "invoice_id" not in table.c:
            continue
        values = {"invoice_id": None}
        if "invoiced" in table.c:
            values["invoiced"] = False
        if "updated_at" in table.c:
            values["updated_at"] = now
        result = bind.execute(table.update().where(table.c.invoice_id.in_(cancelled_ids)).values(**values))
        logger.info("invoice_time_links: cancelled invoices: %s %s released", result.rowcount, table_name)

    if _has_table(inspector, "client_prepaid_consumptions"):
        ledger_t = sa.Table("client_prepaid_consumptions", meta, autoload_with=bind)
        entry_ids = [
            row.time_entry_id
            for row in bind.execute(sa.select(ledger_t.c.time_entry_id).where(ledger_t.c.invoice_id.in_(cancelled_ids)))
        ]
        for start in range(0, len(entry_ids), 500):
            chunk = entry_ids[start : start + 500]
            bind.execute(entries_t.update().where(entries_t.c.id.in_(chunk)).values(billable=True))
        result = bind.execute(ledger_t.delete().where(ledger_t.c.invoice_id.in_(cancelled_ids)))
        logger.info("invoice_time_links: cancelled invoices: %s prepaid ledger rows released", result.rowcount)


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    if not _has_table(inspector, TABLE):
        op.create_table(
            TABLE,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "time_entry_id",
                sa.Integer(),
                sa.ForeignKey("time_entries.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False),
            sa.Column(
                "invoice_item_id",
                sa.Integer(),
                sa.ForeignKey("invoice_items.id", ondelete="CASCADE"),
                nullable=True,
            ),
            sa.Column("hours", sa.Numeric(10, 4), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("released_at", sa.DateTime(), nullable=True),
            sa.Column("released_reason", sa.String(length=255), nullable=True),
        )
        op.create_index("ix_invoice_time_links_time_entry_id", TABLE, ["time_entry_id"])
        op.create_index("ix_invoice_time_links_invoice_id", TABLE, ["invoice_id"])
        op.create_index("ix_invoice_time_links_invoice_item_id", TABLE, ["invoice_item_id"])
        op.create_index("ix_invoice_time_links_released_at", TABLE, ["released_at"])
        op.create_index(
            ACTIVE_LINE_INDEX,
            TABLE,
            ["time_entry_id"],
            unique=True,
            postgresql_where=sa.text(ACTIVE_LINE_CONDITION),
            sqlite_where=sa.text(ACTIVE_LINE_CONDITION),
        )
        op.create_index(
            ACTIVE_PREPAID_INDEX,
            TABLE,
            ["time_entry_id"],
            unique=True,
            postgresql_where=sa.text(ACTIVE_PREPAID_CONDITION),
            sqlite_where=sa.text(ACTIVE_PREPAID_CONDITION),
        )
        backfill(bind)


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if not _has_table(inspector, TABLE):
        return
    existing = {ix["name"] for ix in inspector.get_indexes(TABLE)}
    for name in (
        ACTIVE_PREPAID_INDEX,
        ACTIVE_LINE_INDEX,
        "ix_invoice_time_links_released_at",
        "ix_invoice_time_links_invoice_item_id",
        "ix_invoice_time_links_invoice_id",
        "ix_invoice_time_links_time_entry_id",
    ):
        if name in existing:
            op.drop_index(name, table_name=TABLE)
    op.drop_table(TABLE)
