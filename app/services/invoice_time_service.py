"""Which time entries are billed, and on which invoice.

A time entry is billed when it has an active ``InvoiceTimeLink`` (``released_at`` empty). This service
is the only place that creates, changes and removes links, and the one place every reader asks
"is this entry billed?". ``InvoiceItem.time_entry_ids`` stays as a cache for the PDF, the API and
older reports; the service writes it from the links.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

from sqlalchemy import and_, exists, or_

from app import db
from app.models import Invoice, InvoiceItem, InvoiceTimeLink, TimeEntry
from app.utils.invoice_time_entry_items import (
    LAYOUT_DETAILED,
    LAYOUT_NONE,
    LAYOUT_TASK,
    BillableTimeEntry,
    TimeEntryLines,
    build_time_entry_lines,
    default_line_template,
    describe_lines,
    normalize_billable_entries,
    normalize_layout,
    normalize_template,
    round_quantity,
)

UNBILLED = "unbilled"
ON_DRAFT = "on_draft"
BILLED = "billed"
NON_BILLABLE = "non_billable"
BILLED_OUTSIDE = "billed_outside"

HOURS_PLACES = Decimal("0.0001")
MONEY_PLACES = Decimal("0.01")

# Kinds of invoice lines. A time line is built from time entries and follows them; a manual line is
# typed in (a fixed fee, a retainer); a manual hours line is typed in too, but bills hours: it is
# listed with the hours and counts in the hours billed. Rebuilding hours touches time lines only.
LINE_KIND_TIME = "time"
LINE_KIND_MANUAL = "manual"
LINE_KIND_MANUAL_HOURS = "manual_hours"
HOURS_LINE_KINDS = (LINE_KIND_TIME, LINE_KIND_MANUAL_HOURS)
# A cost line bills project costs (``ProjectCost.invoice_item_id``); see InvoiceCostsService
LINE_KIND_COST = "cost"
VAT_CATEGORIES = ("S", "Z", "E", "AE", "K", "G", "O", "L", "M")

# Statuses of an invoice that has left draft and was not cancelled: its lines are locked and its time
# entries are billed (``paid`` with the invoice's number, set by ``InvoiceService.transition_status``).
ISSUED_STATUSES = ("issued", "sent", "overdue", "paid")

# Allowed invoice status changes. A cancelled or paid invoice does not change status again.
ALLOWED_STATUS_TRANSITIONS = {
    "draft": {"issued", "sent", "cancelled"},
    "issued": {"sent", "cancelled"},
    "sent": {"paid", "overdue", "cancelled"},
    "overdue": {"paid", "cancelled"},
    "paid": set(),
    "cancelled": set(),
}


def status_change_allowed(previous_status: Optional[str], new_status: str) -> bool:
    """Whether an invoice may go from ``previous_status`` to ``new_status`` (same status is allowed)."""
    previous = previous_status or "draft"
    return new_status == previous or new_status in ALLOWED_STATUS_TRANSITIONS.get(previous, set())


EntryWithHours = Union[TimeEntry, Tuple[TimeEntry, Optional[Decimal]]]


class InvoiceTimeError(ValueError):
    """Base error for a link the service refuses to create or change."""

    code = "invoice_time_error"


class TimeEntryAlreadyInvoicedError(InvoiceTimeError):
    """The time entry is already billed: by another invoice, or by another line of this one."""

    code = "already_invoiced"

    def __init__(self, entry_id: int, invoice: Invoice, item: Optional[InvoiceItem] = None):
        self.entry_id = entry_id
        self.invoice = invoice
        self.item = item
        self.invoice_number = invoice.invoice_number if invoice else None
        where = f"invoice {self.invoice_number}"
        if item is not None:
            where += f' (line "{item.description}")'
        super().__init__(f"Time entry {entry_id} is already on {where}")


class TimeEntriesNotBillableError(InvoiceTimeError):
    """Time entries listed for an invoice that this invoice may not bill."""

    code = "time_entries_not_billable"

    def __init__(self, reasons: Dict[int, str]):
        self.reasons = dict(reasons)
        parts = [f"{entry_id} ({reason})" for entry_id, reason in sorted(self.reasons.items())]
        super().__init__("These time entries cannot be billed on this invoice: " + ", ".join(parts))


class InvoiceStatusChangeError(InvoiceTimeError):
    """The invoice cannot leave its status (a cancelled invoice stays cancelled)."""

    code = "invalid_status_transition"

    def __init__(self, invoice: Invoice, previous_status: Optional[str]):
        self.invoice = invoice
        super().__init__(f"Invoice {invoice.invoice_number} cannot change from {previous_status} to {invoice.status}")


class InvalidHoursLayoutError(InvoiceTimeError):
    """Lines cannot be rebuilt with this layout (``none`` would drop the hours instead)."""

    code = "invalid_hours_layout"

    def __init__(self, layout: Optional[str]):
        self.layout = layout
        super().__init__(f"Hours cannot be regrouped as {layout!r}")


class InvalidLineValueError(InvoiceTimeError):
    """A value typed for a draft line or the invoice total that cannot be used.

    ``field`` is the form field (``description``, ``quantity``, ``unit_price``, ``tax_rate``,
    ``vat_category``, ``discount_percent``, ``discount_amount``, ``position``, ``discount``) and
    ``problem`` what is wrong with it (``required``, ``not_a_number``, ``too_low``, ``too_high``,
    ``unknown``), so a page can say it in its own words.
    """

    code = "invalid_value"

    def __init__(self, field: str, problem: str):
        self.field = field
        self.problem = problem
        super().__init__(f"{field}: {problem}")


class EntryNotOnLineError(InvoiceTimeError):
    """The time entry is not on this line of the invoice."""

    code = "not_on_line"

    def __init__(self, entry_id: int, item: InvoiceItem):
        self.entry_id = entry_id
        self.item = item
        super().__init__(f"Time entry {entry_id} is not on this line")


class InvoiceNotDraftError(InvoiceTimeError):
    """Hours can be added to or removed from a draft invoice only."""

    code = "invalid_status"

    def __init__(self, invoice: Invoice):
        self.invoice = invoice
        super().__init__(
            f"Invoice {invoice.invoice_number} is {invoice.status}; hours can only be changed on a draft invoice"
        )


def entry_hours(entry: TimeEntry) -> Decimal:
    """Hours of a time entry, as stored in a link."""
    seconds = entry.duration_seconds or 0
    return (Decimal(seconds) / Decimal(3600)).quantize(HOURS_PLACES)


def _active_link_exists():
    return exists().where(and_(InvoiceTimeLink.time_entry_id == TimeEntry.id, InvoiceTimeLink.released_at.is_(None)))


class InvoiceTimeService:
    """Links between time entries and invoice lines."""

    # ------------------------------------------------------------------
    # Readers
    # ------------------------------------------------------------------
    @staticmethod
    def unbilled_query(
        project_ids: Optional[Sequence[int]] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        client_id: Optional[int] = None,
    ):
        """Query of billable, finished time entries that no invoice bills.

        An entry marked paid without a link ("billed outside", e.g. imported) is left out.
        ``project_ids`` limits the entries to these projects; with ``client_id`` as well, entries
        logged straight on the client are included too. ``None`` means no limit; an empty list
        matches nothing. ``start`` and ``end`` bound the entry's start time.
        """
        query = TimeEntry.query.filter(
            TimeEntry.billable == True,  # noqa: E712
            TimeEntry.end_time.isnot(None),
            TimeEntry.paid == False,  # noqa: E712
            ~_active_link_exists(),
        )
        scope = []
        if project_ids is not None:
            ids = list(project_ids)
            if ids:
                scope.append(TimeEntry.project_id.in_(ids))
        if client_id is not None:
            scope.append(TimeEntry.client_id == client_id)
        if project_ids is not None or client_id is not None:
            query = query.filter(or_(*scope)) if scope else query.filter(db.false())
        if start is not None:
            query = query.filter(TimeEntry.start_time >= start)
        if end is not None:
            query = query.filter(TimeEntry.start_time <= end)
        return query

    def billable_unbilled(
        self,
        project_ids: Optional[Sequence[int]] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        client_id: Optional[int] = None,
    ) -> List[TimeEntry]:
        """Billable, finished time entries that no invoice bills, oldest first."""
        return (
            self.unbilled_query(project_ids, start, end, client_id=client_id)
            .order_by(TimeEntry.start_time.asc(), TimeEntry.id.asc())
            .all()
        )

    @staticmethod
    def active_links(entry: TimeEntry) -> List[InvoiceTimeLink]:
        return (
            InvoiceTimeLink.query.filter(
                InvoiceTimeLink.time_entry_id == entry.id, InvoiceTimeLink.released_at.is_(None)
            )
            .order_by(InvoiceTimeLink.id.asc())
            .all()
        )

    def billing_invoice(self, entry: TimeEntry) -> Optional[Invoice]:
        """The invoice that bills this entry now, or None."""
        links = self.active_links(entry)
        return links[0].invoice if links else None

    def billing_state(self, entry: TimeEntry) -> str:
        """``unbilled`` / ``on_draft`` / ``billed`` / ``non_billable`` / ``billed_outside``."""
        return self._state_for(entry, self.billing_invoice(entry))

    @staticmethod
    def _state_for(entry: TimeEntry, invoice: Optional[Invoice]) -> str:
        if invoice is not None:
            return ON_DRAFT if invoice.status == "draft" else BILLED
        if entry.paid:
            return BILLED_OUTSIDE
        if not entry.billable:
            return NON_BILLABLE
        return UNBILLED

    def billing_states(self, entries: Iterable[TimeEntry]) -> Dict[int, Tuple[str, Optional[Invoice]]]:
        """``{entry_id: (billing_state, invoice)}`` for many entries, in one query per 500 entries.

        Same answer as ``billing_state`` and ``billing_invoice`` for each entry; use it for lists.
        """
        entries = [e for e in entries if e is not None and e.id is not None]
        invoices: Dict[int, Invoice] = {}
        ids = sorted({e.id for e in entries})
        for start in range(0, len(ids), 500):
            chunk = ids[start : start + 500]
            rows = (
                db.session.query(InvoiceTimeLink.time_entry_id, Invoice)
                .join(Invoice, Invoice.id == InvoiceTimeLink.invoice_id)
                .filter(InvoiceTimeLink.time_entry_id.in_(chunk), InvoiceTimeLink.released_at.is_(None))
                .order_by(InvoiceTimeLink.id.asc())
                .all()
            )
            for entry_id, invoice in rows:
                invoices.setdefault(entry_id, invoice)
        return {e.id: (self._state_for(e, invoices.get(e.id)), invoices.get(e.id)) for e in entries}

    @staticmethod
    def locked_message(invoice: Invoice) -> str:
        return (
            f"This entry is on invoice {invoice.invoice_number} and cannot be edited or deleted. "
            "Remove it from the draft invoice or cancel the invoice first."
        )

    def edit_lock(self, entry: TimeEntry) -> Optional[Dict[str, str]]:
        """Refusal for editing or deleting an entry that an invoice bills, or None if it may change."""
        invoice = self.billing_invoice(entry)
        if invoice is None:
            return None
        return {
            "success": False,
            "error": "time_entry_invoiced",
            "message": self.locked_message(invoice),
            "invoice_number": invoice.invoice_number,
        }

    @staticmethod
    def active_entry_ids_query(*invoice_criteria):
        """Query of ``time_entry_id`` for active links, to invoices matching ``invoice_criteria``.

        Use it as a subquery (``TimeEntry.id.in_(...)``) rather than loading the IDs.
        """
        query = db.session.query(InvoiceTimeLink.time_entry_id).filter(InvoiceTimeLink.released_at.is_(None))
        if invoice_criteria:
            query = query.join(Invoice, Invoice.id == InvoiceTimeLink.invoice_id).filter(*invoice_criteria)
        return query

    @staticmethod
    def billed_clause():
        """SQL condition: the entry is billed.

        Billed means on an invoice that is no longer a draft, or marked paid without an invoice
        ("billed outside", e.g. imported). An entry on a draft is not billed yet.
        """
        on_issued_invoice = exists().where(
            and_(
                InvoiceTimeLink.time_entry_id == TimeEntry.id,
                InvoiceTimeLink.released_at.is_(None),
                InvoiceTimeLink.invoice_id == Invoice.id,
                Invoice.status != "draft",
            )
        )
        return or_(TimeEntry.paid == True, on_issued_invoice)  # noqa: E712

    @staticmethod
    def entry_ids_on_issued_invoices(entry_ids: Iterable[int]) -> set:
        """Which of these entries are on an invoice that is no longer a draft."""
        ids = [i for i in entry_ids if isinstance(i, int)]
        found: set = set()
        for start in range(0, len(ids), 500):
            chunk = ids[start : start + 500]
            rows = (
                db.session.query(InvoiceTimeLink.time_entry_id)
                .join(Invoice, Invoice.id == InvoiceTimeLink.invoice_id)
                .filter(
                    InvoiceTimeLink.time_entry_id.in_(chunk),
                    InvoiceTimeLink.released_at.is_(None),
                    Invoice.status != "draft",
                )
                .all()
            )
            found.update(row[0] for row in rows)
        return found

    @staticmethod
    def _scope(project_id: Optional[int], client_id: Optional[int]) -> Tuple[List[int], Optional[int]]:
        """Projects and client whose time an invoice may bill: its project and its client's projects."""
        from app.models import Project

        project_ids = [project_id] if project_id else []
        if client_id:
            project_ids += [row[0] for row in db.session.query(Project.id).filter(Project.client_id == client_id).all()]
        return sorted(set(project_ids)), client_id

    def eligible_entry_ids(
        self,
        invoice: Optional[Invoice],
        entry_ids: Iterable[int],
        *,
        project_id: Optional[int] = None,
        client_id: Optional[int] = None,
        include_prepaid_only: bool = False,
    ) -> set:
        """Which of ``entry_ids`` this invoice may bill on a line.

        The same set the generate-from-time picker offers: billable, finished entries no invoice
        bills (not "billed outside"), on the invoice's project or its client's projects, plus the
        entries already on a line of this invoice. An entry fully covered by this invoice's prepaid
        hours (a link without a line) is not, unless ``include_prepaid_only``: generate-from-time
        recalculates prepaid hours and needs those entries back. Pass ``project_id`` /
        ``client_id`` for an invoice that does not exist yet.
        """
        wanted = {i for i in entry_ids if isinstance(i, int)}
        ids = sorted(wanted)
        if not ids:
            return set()
        if invoice is not None:
            project_id = project_id or invoice.project_id
            client_id = client_id or invoice.client_id
        project_ids, client_id = self._scope(project_id, client_id)
        eligible: set = set()
        for start in range(0, len(ids), 500):
            chunk = ids[start : start + 500]
            query = self.unbilled_query(project_ids, client_id=client_id).filter(TimeEntry.id.in_(chunk))
            eligible.update(row[0] for row in query.with_entities(TimeEntry.id).all())
        if invoice is not None and invoice.id is not None:
            on_this_invoice = self.invoice_entry_ids(invoice, with_line_only=not include_prepaid_only)
            eligible.update(i for i in on_this_invoice if i in wanted)
        return eligible

    def ineligible_reason(self, entry: Optional[TimeEntry], invoice: Optional[Invoice]) -> str:
        """Why an entry cannot be billed on ``invoice``, in a few words."""
        if entry is None:
            return "not found"
        if entry.end_time is None:
            return "timer running"
        other = self._other_invoice_link(entry.id, invoice) if invoice is not None else None
        if other is None and invoice is None:
            links = self.active_links(entry)
            other = links[0] if links else None
        if other is not None:
            return f"on invoice {other.invoice.invoice_number}"
        if invoice is not None and invoice.id is not None:
            prepaid_only = InvoiceTimeLink.query.filter(
                InvoiceTimeLink.time_entry_id == entry.id,
                InvoiceTimeLink.invoice_id == invoice.id,
                InvoiceTimeLink.invoice_item_id.is_(None),
                InvoiceTimeLink.released_at.is_(None),
            ).first()
            if prepaid_only is not None:
                return "covered by prepaid hours on this invoice"
        if entry.paid:
            return "marked paid outside an invoice"
        if not entry.billable:
            return "non-billable"
        return "not on this invoice's project or client"

    def check_line_entries(self, invoice: Invoice, lines: Iterable[Iterable[int]]) -> None:
        """Refuse lines that list time entries this invoice may not bill.

        ``lines`` holds the entry IDs of each line. Raises ``TimeEntriesNotBillableError`` for an
        entry outside ``eligible_entry_ids`` or listed on two lines.
        """
        reasons: Dict[int, str] = {}
        seen: set = set()
        all_ids: List[int] = []
        for ids in lines:
            for entry_id in ids:
                if entry_id in seen:
                    reasons[entry_id] = "listed on two lines"
                seen.add(entry_id)
                all_ids.append(entry_id)
        eligible = self.eligible_entry_ids(invoice, all_ids)
        missing = [i for i in seen if i not in eligible and i not in reasons]
        if missing:
            by_id = {e.id: e for e in TimeEntry.query.filter(TimeEntry.id.in_(missing)).all()}
            for entry_id in missing:
                reasons[entry_id] = self.ineligible_reason(by_id.get(entry_id), invoice)
        if reasons:
            raise TimeEntriesNotBillableError(reasons)

    @staticmethod
    def invoice_entry_ids(invoice: Invoice, *, with_line_only: bool = False) -> List[int]:
        """IDs of time entries this invoice bills, in link order."""
        query = InvoiceTimeLink.query.filter(
            InvoiceTimeLink.invoice_id == invoice.id, InvoiceTimeLink.released_at.is_(None)
        )
        if with_line_only:
            query = query.filter(InvoiceTimeLink.invoice_item_id.isnot(None))
        seen: List[int] = []
        for link in query.order_by(InvoiceTimeLink.id.asc()).all():
            if link.time_entry_id not in seen:
                seen.append(link.time_entry_id)
        return seen

    def invoice_summary(self, invoice: Invoice) -> Dict:
        """What an invoice bills, for the issue and cancel dialogs and the "locked" notice.

        ``entries``: time entries it bills; ``tracked_hours``: their hours; ``billed_hours``: the
        quantity of the lines that bill time; ``expenses`` and ``costs``: how many it bills;
        ``prepaid``: ``[(allocation month, hours)]`` of the client's prepaid hours it uses.
        """
        from app.models import ClientPrepaidConsumption, ProjectCost

        entry_ids = self.invoice_entry_ids(invoice) if invoice.id is not None else []
        tracked = Decimal("0")
        for start in range(0, len(entry_ids), 500):
            chunk = entry_ids[start : start + 500]
            seconds = (
                db.session.query(db.func.coalesce(db.func.sum(TimeEntry.duration_seconds), 0))
                .filter(TimeEntry.id.in_(chunk))
                .scalar()
            )
            tracked += Decimal(int(seconds or 0)) / Decimal(3600)

        billed = Decimal("0")
        if invoice.id is not None:
            line_ids = (
                db.session.query(InvoiceTimeLink.invoice_item_id)
                .filter(
                    InvoiceTimeLink.invoice_id == invoice.id,
                    InvoiceTimeLink.released_at.is_(None),
                    InvoiceTimeLink.invoice_item_id.isnot(None),
                )
                .distinct()
            )
            billed = Decimal(
                str(
                    db.session.query(db.func.coalesce(db.func.sum(InvoiceItem.quantity), 0))
                    .filter(InvoiceItem.id.in_(line_ids))
                    .scalar()
                    or 0
                )
            )

        prepaid: Dict = {}
        expenses = costs = 0
        if invoice.id is not None:
            for month, seconds in (
                db.session.query(ClientPrepaidConsumption.allocation_month, ClientPrepaidConsumption.seconds_consumed)
                .filter(ClientPrepaidConsumption.invoice_id == invoice.id)
                .all()
            ):
                prepaid[month] = prepaid.get(month, 0) + int(seconds or 0)
            expenses = invoice.expenses.count()
            costs = ProjectCost.query.filter(ProjectCost.invoice_id == invoice.id).count()

        return {
            "entries": len(entry_ids),
            "tracked_hours": tracked.quantize(Decimal("0.01")),
            "billed_hours": billed.quantize(Decimal("0.01")),
            "expenses": expenses,
            "costs": costs,
            "prepaid": [
                (month, (Decimal(seconds) / Decimal(3600)).quantize(Decimal("0.01")))
                for month, seconds in sorted(prepaid.items())
            ],
        }

    # ------------------------------------------------------------------
    # Writers
    # ------------------------------------------------------------------
    @staticmethod
    def _require_draft(invoice: Invoice) -> None:
        if (invoice.status or "draft") != "draft":
            raise InvoiceNotDraftError(invoice)

    @staticmethod
    def _other_invoice_link(entry_id: int, invoice: Invoice) -> Optional[InvoiceTimeLink]:
        return (
            InvoiceTimeLink.query.filter(
                InvoiceTimeLink.time_entry_id == entry_id,
                InvoiceTimeLink.released_at.is_(None),
                InvoiceTimeLink.invoice_id != invoice.id,
            )
            .order_by(InvoiceTimeLink.id.asc())
            .first()
        )

    def find_conflicts(self, entries: Iterable[TimeEntry], invoice: Optional[Invoice] = None) -> List[Tuple]:
        """(entry, invoice) for each entry that cannot get a new line on ``invoice``.

        That is an entry billed by another invoice, or already on a line of ``invoice`` itself:
        an entry has at most one line, so the same hours are never billed twice.
        """
        conflicts = []
        for entry in entries:
            link = self._line_or_other_invoice_link(entry.id, invoice)
            if link is not None:
                conflicts.append((entry, link.invoice))
        return conflicts

    @staticmethod
    def _line_or_other_invoice_link(entry_id: int, invoice: Optional[Invoice]) -> Optional[InvoiceTimeLink]:
        query = InvoiceTimeLink.query.filter(
            InvoiceTimeLink.time_entry_id == entry_id, InvoiceTimeLink.released_at.is_(None)
        )
        if invoice is not None and invoice.id is not None:
            query = query.filter(
                or_(InvoiceTimeLink.invoice_id != invoice.id, InvoiceTimeLink.invoice_item_id.isnot(None))
            )
        return query.order_by(InvoiceTimeLink.id.asc()).first()

    @staticmethod
    def refresh_item_cache(item: InvoiceItem) -> None:
        """Write ``item.time_entry_ids`` from the item's active links."""
        ids: List[int] = []
        for link in (
            InvoiceTimeLink.query.filter(
                InvoiceTimeLink.invoice_item_id == item.id, InvoiceTimeLink.released_at.is_(None)
            )
            .order_by(InvoiceTimeLink.id.asc())
            .all()
        ):
            if link.time_entry_id not in ids:
                ids.append(link.time_entry_id)
        item.time_entry_ids = ",".join(str(i) for i in ids) if ids else None

    def link_entries(
        self,
        invoice: Invoice,
        item: Optional[InvoiceItem],
        entries_with_hours: Iterable[EntryWithHours],
        created_by: Optional[int] = None,
    ) -> List[InvoiceTimeLink]:
        """Link time entries to an invoice line (``item`` None: entries with no line, fully prepaid).

        Each element is an entry or ``(entry, hours)``; hours default to the entry's hours.
        Refuses a non-draft invoice, an entry already billed by another invoice, and an entry
        already on another line of this invoice. An entry has at most one line link, plus at most
        one link without a line (prepaid hours) on the same invoice.
        """
        self._require_draft(invoice)
        if invoice.id is None or (item is not None and item.id is None):
            db.session.flush()

        links: List[InvoiceTimeLink] = []
        for element in entries_with_hours:
            if isinstance(element, tuple):
                entry, hours = element
            else:
                entry, hours = element, None
            hours = entry_hours(entry) if hours is None else Decimal(str(hours)).quantize(HOURS_PLACES)

            other = self._other_invoice_link(entry.id, invoice)
            if other is not None:
                raise TimeEntryAlreadyInvoicedError(entry.id, other.invoice)
            if item is not None:
                # One line per entry: the same hours are never billed twice on one invoice
                other_line = InvoiceTimeLink.query.filter(
                    InvoiceTimeLink.time_entry_id == entry.id,
                    InvoiceTimeLink.released_at.is_(None),
                    InvoiceTimeLink.invoice_item_id.isnot(None),
                    InvoiceTimeLink.invoice_item_id != item.id,
                ).first()
                if other_line is not None:
                    raise TimeEntryAlreadyInvoicedError(entry.id, invoice, other_line.invoice_item)

            existing = InvoiceTimeLink.query.filter(
                InvoiceTimeLink.time_entry_id == entry.id,
                InvoiceTimeLink.invoice_id == invoice.id,
                InvoiceTimeLink.released_at.is_(None),
                (
                    InvoiceTimeLink.invoice_item_id == item.id
                    if item is not None
                    else InvoiceTimeLink.invoice_item_id.is_(None)
                ),
            ).first()
            if existing is not None:
                existing.hours = hours
                links.append(existing)
                continue

            link = InvoiceTimeLink(
                time_entry=entry,
                invoice=invoice,
                invoice_item=item,
                hours=hours,
                created_by=created_by,
            )
            db.session.add(link)
            links.append(link)

        db.session.flush()
        if item is not None:
            self.refresh_item_cache(item)
        return links

    def link_items(
        self,
        invoice: Invoice,
        items: Iterable[InvoiceItem],
        hours_by_entry: Optional[Dict[int, Decimal]] = None,
        created_by: Optional[int] = None,
    ) -> List[InvoiceTimeLink]:
        """Link the entries each new line lists in ``time_entry_ids`` (as built by the line builders).

        IDs of entries that do not exist are dropped from the line's cache.
        """
        hours_by_entry = hours_by_entry or {}
        items = list(items)
        if any(item.id is None for item in items):
            db.session.flush()
        links: List[InvoiceTimeLink] = []
        for item in items:
            ids = _parse_ids(item.time_entry_ids)
            if not ids:
                continue
            by_id = {e.id: e for e in TimeEntry.query.filter(TimeEntry.id.in_(ids)).all()}
            pairs = [(by_id[i], hours_by_entry.get(i)) for i in ids if i in by_id]
            if pairs:
                links.extend(self.link_entries(invoice, item, pairs, created_by=created_by))
            else:
                item.time_entry_ids = None
        return links

    def unlink_entry(self, invoice: Invoice, entry: TimeEntry, item: Optional[InvoiceItem] = None) -> int:
        """Remove an entry from a draft invoice (from one line, if ``item`` is given)."""
        self._require_draft(invoice)
        query = InvoiceTimeLink.query.filter(
            InvoiceTimeLink.invoice_id == invoice.id,
            InvoiceTimeLink.time_entry_id == entry.id,
            InvoiceTimeLink.released_at.is_(None),
        )
        if item is not None:
            query = query.filter(InvoiceTimeLink.invoice_item_id == item.id)
        links = query.all()
        items = {link.invoice_item for link in links if link.invoice_item is not None}
        for link in links:
            db.session.delete(link)
        db.session.flush()
        for affected in items:
            self.refresh_item_cache(affected)
        return len(links)

    def detach_lines(self, invoice: Invoice, items: Optional[Iterable[InvoiceItem]] = None) -> Dict[int, Decimal]:
        """Remove the links of a draft invoice's lines before the lines are replaced.

        Returns hours per entry so the new lines can keep them. Links of entries with no line
        (fully prepaid) stay. ``items`` limits this to these lines.
        """
        self._require_draft(invoice)
        hours: Dict[int, Decimal] = {}
        query = InvoiceTimeLink.query.filter(
            InvoiceTimeLink.invoice_id == invoice.id,
            InvoiceTimeLink.invoice_item_id.isnot(None),
            InvoiceTimeLink.released_at.is_(None),
        )
        if items is not None:
            item_ids = [item.id for item in items if item.id is not None]
            if not item_ids:
                return hours
            query = query.filter(InvoiceTimeLink.invoice_item_id.in_(item_ids))
        links = query.all()
        for link in links:
            hours[link.time_entry_id] = hours.get(link.time_entry_id, Decimal("0")) + Decimal(link.hours or 0)
            db.session.delete(link)
        db.session.flush()
        return hours

    # ------------------------------------------------------------------
    # Lines from hours: layout and description template
    # ------------------------------------------------------------------
    @staticmethod
    def settings_layout() -> str:
        """Layout from the global "group time entries" setting: by task, or one line per entry."""
        from app.models import Settings

        settings = Settings.get_settings()
        group = getattr(settings, "invoice_group_time_entries", True) if settings else True
        return LAYOUT_TASK if group else LAYOUT_DETAILED

    def resolve_layout(
        self,
        project=None,
        layout: Optional[str] = None,
        template: Optional[str] = None,
        fallback_layout: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Layout and template to use: the ones given, else the project's last ones, else defaults.

        Without a layout and without a project default, ``fallback_layout`` (if given) or the global
        setting decides. Without a template, the project's last template is used when it was
        written for the same layout, else the layout's default.
        """
        # "Don't add any hours" is a choice for one invoice, never the default for the next one
        last_layout = normalize_layout(getattr(project, "last_hours_layout", None))
        if last_layout == LAYOUT_NONE:
            last_layout = None
        layout = normalize_layout(layout) or last_layout or normalize_layout(fallback_layout) or self.settings_layout()
        resolved = normalize_template(template)
        if resolved is None and last_layout == layout:
            resolved = normalize_template(getattr(project, "last_line_template", None))
        return layout, resolved or default_line_template(layout)

    @staticmethod
    def remember_layout(invoice: Invoice, project, layout: str, template: Optional[str]) -> None:
        """Store the layout and template on the invoice and, when ``project`` is given, on the project.

        ``none`` is stored on the invoice only: the project keeps its last layout with hours.
        """
        template = normalize_template(template)
        invoice.hours_layout = layout
        invoice.line_template = template
        if project is not None and layout != LAYOUT_NONE:
            project.last_hours_layout = layout
            project.last_line_template = template

    @staticmethod
    def _next_position(invoice: Invoice) -> int:
        if invoice.id is None:
            return 0
        positions = [item.position or 0 for item in invoice.items.all()]
        return max(positions) + 1 if positions else 0

    def add_entries(
        self,
        invoice: Invoice,
        entries,
        layout: Optional[str] = None,
        template: Optional[str] = None,
        *,
        hours_by_entry: Optional[Dict[int, Decimal]] = None,
        created_by: Optional[int] = None,
        project=None,
        remember: bool = True,
        fallback_layout: Optional[str] = None,
    ) -> TimeEntryLines:
        """Build lines for time entries on a draft invoice and link the entries to them.

        ``entries`` are time entries, or entries with their billable hours (``ProcessedTimeEntry``
        after prepaid hours, ``BillableTimeEntry``); each link gets those hours unless
        ``hours_by_entry`` says otherwise. Layout and template come from ``resolve_layout``. New lines
        go after the invoice's other lines. The layout and template are stored on the invoice and,
        with ``remember``, on the project as the default for its next invoice. Returns the lines
        (with warnings for hours that had no rate). The caller commits.
        """
        self._require_draft(invoice)
        entries = list(entries or [])
        project = project if project is not None else invoice.project
        layout, template = self.resolve_layout(project, layout, template, fallback_layout)
        if invoice.id is None:
            db.session.flush()

        lines = build_time_entry_lines(
            invoice.id,
            entries,
            layout=layout,
            template=template,
            project_name=project.name if project is not None else None,
            currency=invoice.currency_code,
        )
        position = self._next_position(invoice)
        for offset, item in enumerate(lines.items):
            item.position = position + offset
            db.session.add(item)
        db.session.flush()

        hours = {b.entry.id: b.billable_hours for b in normalize_billable_entries(entries)}
        hours.update(hours_by_entry or {})
        self.link_items(invoice, lines.items, hours_by_entry=hours, created_by=created_by)
        self.remember_layout(invoice, project if remember else None, layout, template)
        return lines

    def _line_entries(self, item: InvoiceItem) -> List[Tuple[TimeEntry, Decimal]]:
        """(entry, hours) of a line's active links, oldest link first."""
        result: List[Tuple[TimeEntry, Decimal]] = []
        for link in (
            InvoiceTimeLink.query.filter(
                InvoiceTimeLink.invoice_item_id == item.id, InvoiceTimeLink.released_at.is_(None)
            )
            .order_by(InvoiceTimeLink.id.asc())
            .all()
        ):
            result.append((link.time_entry, Decimal(link.hours or 0)))
        return result

    @staticmethod
    def _ordered_items(invoice: Invoice) -> List[InvoiceItem]:
        return sorted(invoice.items.all(), key=lambda item: (item.position or 0, item.id or 0))

    def rebuild_lines(
        self,
        invoice: Invoice,
        layout: Optional[str] = None,
        template: Optional[str] = None,
        keep_edited: bool = True,
        created_by: Optional[int] = None,
    ) -> TimeEntryLines:
        """Regroup a draft's hours: its time lines are built again from the same entries and hours.

        Links stay with the same entries, so the hours and the total do not change (unless a
        rebuilt line had a hand-edited quantity or price). Manual lines are never touched. With
        ``keep_edited`` a time line whose description, quantity or price was edited stays as it is,
        with its entries; without it, edited lines are rebuilt too. Kept and manual lines keep their
        place; the new lines take the place of the first rebuilt line. Without ``layout`` the
        invoice's own layout is kept. The caller commits.
        """
        self._require_draft(invoice)
        project = invoice.project
        layout = normalize_layout(layout) or normalize_layout(invoice.hours_layout)
        if layout == LAYOUT_NONE:
            raise InvalidHoursLayoutError(layout)
        if template is None and layout is not None and layout == normalize_layout(invoice.hours_layout):
            template = invoice.line_template
        layout, template = self.resolve_layout(project, layout, template)

        items = self._ordered_items(invoice)
        rebuilt = [i for i in items if i.kind == "time" and not (keep_edited and i.is_edited)]
        billable: List[BillableTimeEntry] = []
        for item in rebuilt:
            for entry, hours in self._line_entries(item):
                billable.append(BillableTimeEntry(entry=entry, billable_hours=hours))

        hours = self.detach_lines(invoice, rebuilt)
        lines = build_time_entry_lines(
            invoice.id,
            billable,
            layout=layout,
            template=template,
            project_name=project.name if project is not None else None,
            currency=invoice.currency_code,
        )
        rebuilt_ids = {item.id for item in rebuilt}
        order: List[InvoiceItem] = []
        placed = False
        for item in items:
            if item.id in rebuilt_ids:
                if not placed:
                    order.extend(lines.items)
                    placed = True
                continue
            order.append(item)
        if not placed:
            order.extend(lines.items)
        for item in rebuilt:
            db.session.delete(item)
        db.session.flush()
        for position, item in enumerate(order):
            item.position = position
            if item.id is None:
                db.session.add(item)
        db.session.flush()
        self.link_items(invoice, lines.items, hours_by_entry=hours, created_by=created_by)
        self.remember_layout(invoice, project, layout, template)
        invoice.calculate_totals()
        return lines

    def apply_template(self, invoice: Invoice, template: Optional[str], keep_edited: bool = True) -> int:
        """Rewrite the descriptions of a draft's time lines from their entries, lines unchanged.

        With ``keep_edited`` a line whose description was edited by hand keeps it; without it, the
        line is rewritten and no longer counts as edited. Returns the number of lines rewritten.
        The caller commits.
        """
        self._require_draft(invoice)
        project = invoice.project
        layout = normalize_layout(invoice.hours_layout)
        if layout in (None, LAYOUT_NONE):
            layout, _template = self.resolve_layout(project)
            layout = LAYOUT_TASK if layout == LAYOUT_NONE else layout
        template = normalize_template(template) or default_line_template(layout)

        time_items = [i for i in self._ordered_items(invoice) if i.kind == "time"]
        lines = [(item, [entry for entry, _hours in self._line_entries(item)]) for item in time_items]
        descriptions = describe_lines(
            lines,
            layout=layout,
            template=template,
            currency=invoice.currency_code,
            project_name=project.name if project is not None else None,
        )
        rewritten = 0
        for index, (item, _entries) in enumerate(lines):
            if index not in descriptions or (keep_edited and item.description_edited):
                continue
            item.description = descriptions[index]
            item.description_edited = False
            rewritten += 1
        self.remember_layout(invoice, project, layout, template)
        db.session.flush()
        return rewritten

    # ------------------------------------------------------------------
    # Draft page: one line at a time
    # ------------------------------------------------------------------
    def _invoice_layout(self, invoice: Invoice) -> str:
        """The invoice's hours layout, or the one its next hours would get when it has none."""
        layout = normalize_layout(invoice.hours_layout)
        if layout in (None, LAYOUT_NONE):
            layout, _template = self.resolve_layout(invoice.project)
        return LAYOUT_TASK if layout == LAYOUT_NONE else layout

    def _refresh_descriptions(self, invoice: Invoice, items: Iterable[InvoiceItem]) -> None:
        """Rewrite the descriptions of ``items`` (time lines not edited by hand) from their entries.

        Every time line takes part, so lines of one group that differ by rate keep their rate suffix.
        """
        wanted = {item.id for item in items if item.kind == LINE_KIND_TIME and not item.description_edited}
        if not wanted:
            return
        project = invoice.project
        layout = self._invoice_layout(invoice)
        template = normalize_template(invoice.line_template) or default_line_template(layout)
        time_items = [i for i in self._ordered_items(invoice) if i.kind == LINE_KIND_TIME]
        lines = [(item, [entry for entry, _hours in self._line_entries(item)]) for item in time_items]
        descriptions = describe_lines(
            lines,
            layout=layout,
            template=template,
            currency=invoice.currency_code,
            project_name=project.name if project is not None else None,
        )
        for index, (item, _entries) in enumerate(lines):
            if item.id in wanted and index in descriptions:
                item.description = descriptions[index]

    def recalculate_line(self, invoice: Invoice, item: InvoiceItem, hours_change: Optional[Decimal] = None) -> str:
        """Bring a time line back in line with its entries after entries were removed or added.

        A line whose quantity was not changed by hand takes the tracked hours of its remaining links;
        a line with a hand-edited quantity changes by ``hours_change`` (the hours of the entries
        removed, negative, or added) and never goes below 0. A description not edited by hand is
        rewritten from the remaining entries. A line left without entries is deleted, unless it was
        edited by hand: then it stays as a manual hours line. Returns ``updated``, ``deleted`` or
        ``manual``. Totals are recalculated; the caller commits.
        """
        self._require_draft(invoice)
        db.session.flush()
        result = "updated"
        if self.tracked_quantity(item) is None:
            if not item.is_edited:
                db.session.delete(item)
                db.session.flush()
                invoice.calculate_totals()
                return "deleted"
            item.kind = LINE_KIND_MANUAL_HOURS
            item.time_entry_ids = None
            result = "manual"
            if hours_change is not None:
                quantity = Decimal(str(item.quantity or 0)) + Decimal(str(hours_change))
                item.quantity = max(quantity, Decimal("0")).quantize(MONEY_PLACES)
        elif item.quantity_edited:
            if hours_change is not None:
                quantity = Decimal(str(item.quantity or 0)) + Decimal(str(hours_change))
                item.quantity = max(quantity, Decimal("0")).quantize(MONEY_PLACES)
        else:
            item.quantity = self.tracked_quantity(item)
            self._refresh_descriptions(invoice, [item])
        item.total_amount = item.line_net
        db.session.flush()
        invoice.calculate_totals()
        return result

    def _line_link(self, invoice: Invoice, item: InvoiceItem, entry: TimeEntry) -> InvoiceTimeLink:
        link = InvoiceTimeLink.query.filter(
            InvoiceTimeLink.invoice_id == invoice.id,
            InvoiceTimeLink.invoice_item_id == item.id,
            InvoiceTimeLink.time_entry_id == entry.id,
            InvoiceTimeLink.released_at.is_(None),
        ).first()
        if link is None:
            raise EntryNotOnLineError(entry.id, item)
        return link

    def release_prepaid(self, invoice: Invoice, entry: TimeEntry) -> Decimal:
        """Give back the prepaid hours an entry used on this draft, as the prepaid allocator does.

        The entry's ledger row for this invoice and its link without a line go, and the entry is
        billable again. The other entries of the draft keep their prepaid hours: the hours freed are
        not spread over them. Returns the prepaid hours freed (0 when the entry used none here).
        """
        from app.models import ClientPrepaidConsumption

        self._require_draft(invoice)
        rows = ClientPrepaidConsumption.query.filter(
            ClientPrepaidConsumption.invoice_id == invoice.id,
            ClientPrepaidConsumption.time_entry_id == entry.id,
        ).all()
        freed = sum((row.hours_consumed for row in rows), Decimal("0"))
        for row in rows:
            db.session.delete(row)
        for link in InvoiceTimeLink.query.filter(
            InvoiceTimeLink.invoice_id == invoice.id,
            InvoiceTimeLink.time_entry_id == entry.id,
            InvoiceTimeLink.invoice_item_id.is_(None),
            InvoiceTimeLink.released_at.is_(None),
        ).all():
            db.session.delete(link)
        if rows:
            entry.billable = True
        db.session.flush()
        return freed

    def release_dropped_prepaid(self, invoice: Invoice, entry_ids: Iterable[int]) -> Decimal:
        """After a draft's lines were replaced or removed: give back the prepaid hours of the entries
        that are on no line of the invoice any more (``release_prepaid``).

        ``entry_ids``: the entries the old lines had (what ``detach_lines`` returned). Entries the new
        lines kept keep their prepaid hours. Does nothing on an invoice that is not a draft. Returns the
        prepaid hours freed.
        """
        ids = {int(i) for i in entry_ids}
        if not ids or invoice.status != "draft":
            return Decimal("0")
        db.session.flush()
        on_lines = {
            row[0]
            for row in db.session.query(InvoiceTimeLink.time_entry_id)
            .filter(
                InvoiceTimeLink.invoice_id == invoice.id,
                InvoiceTimeLink.invoice_item_id.isnot(None),
                InvoiceTimeLink.released_at.is_(None),
                InvoiceTimeLink.time_entry_id.in_(list(ids)),
            )
            .all()
        }
        dropped = ids - on_lines
        freed = Decimal("0")
        if dropped:
            for entry in TimeEntry.query.filter(TimeEntry.id.in_(list(dropped))).all():
                freed += self.release_prepaid(invoice, entry)
        return freed

    def remove_line_entry(
        self, invoice: Invoice, item: InvoiceItem, entry: TimeEntry, *, non_billable: bool = False
    ) -> Dict:
        """Take a time entry off a draft's line: × (back to Unbilled) or Non-billable.

        The entry leaves the invoice: its line link goes, and so do the prepaid hours it used here
        (``release_prepaid``). Non-billable then sets the entry's ``billable`` to False, so it is not
        offered for an invoice again. The line is recalculated (``recalculate_line``). Returns
        ``line`` (``updated``, ``deleted`` or ``manual``), ``hours`` (the hours the line lost) and
        ``prepaid_freed`` (prepaid hours given back). The caller commits.
        """
        self._require_draft(invoice)
        link = self._line_link(invoice, item, entry)
        hours = round_quantity(Decimal(link.hours or 0))
        self.unlink_entry(invoice, entry, item)
        freed = self.release_prepaid(invoice, entry)
        if non_billable:
            entry.set_billable(False, commit=False)
        line = self.recalculate_line(invoice, item, hours_change=-hours)
        return {"line": line, "hours": hours, "prepaid_freed": freed}

    @staticmethod
    def default_hours_rate(invoice: Invoice) -> Decimal:
        """Hourly rate a hand-added hours line starts with: the invoice project's rate (or its client's)."""
        from app.models import RateOverride

        try:
            return Decimal(str(RateOverride.resolve_rate(invoice.project) or 0)).quantize(MONEY_PLACES)
        except Exception:
            return Decimal("0.00")

    @staticmethod
    def parse_amount(value, field: str, *, allow_empty: bool = False, minimum: Optional[Decimal] = None):
        """A decimal typed in a draft form, or None when empty and ``allow_empty``.

        ``field`` names the form field in the ``InvalidLineValueError`` raised for a bad value.
        """
        text = (str(value) if value is not None else "").strip().replace(",", ".")
        if not text:
            if allow_empty:
                return None
            raise InvalidLineValueError(field, "required")
        try:
            number = Decimal(text)
        except (ArithmeticError, ValueError):
            raise InvalidLineValueError(field, "not_a_number") from None
        if not number.is_finite():
            raise InvalidLineValueError(field, "not_a_number")
        if minimum is not None and number < minimum:
            raise InvalidLineValueError(field, "too_low")
        return number

    def add_manual_line(
        self,
        invoice: Invoice,
        description: str,
        quantity,
        unit_price=None,
        *,
        hours: bool = False,
    ) -> InvoiceItem:
        """Add a line typed in to a draft, after its other lines.

        ``hours`` makes it a manual hours line (listed with the hours; the price defaults to the
        project's rate); otherwise a manual line (a fixed fee). It has no time entries. The caller commits.
        """
        self._require_draft(invoice)
        description = self.normalize_description(description)
        if not description:
            raise InvalidLineValueError("description", "required")
        quantity = self.parse_amount(quantity, "quantity", minimum=Decimal("0"))
        price = self.parse_amount(unit_price, "unit_price", allow_empty=True)
        if price is None:
            price = self.default_hours_rate(invoice) if hours else Decimal("0")
        item = InvoiceItem(
            invoice_id=invoice.id,
            description=description[:500],
            quantity=quantity.quantize(MONEY_PLACES),
            unit_price=price.quantize(MONEY_PLACES),
            position=self._next_position(invoice),
        )
        item.kind = LINE_KIND_MANUAL_HOURS if hours else LINE_KIND_MANUAL
        db.session.add(item)
        db.session.flush()
        invoice.calculate_totals()
        return item

    def update_line(self, invoice: Invoice, item: InvoiceItem, values: Dict) -> InvoiceItem:
        """Change a draft line from the draft page; only the keys present in ``values`` change.

        Keys: ``description``, ``quantity``, ``unit_price``, ``tax_rate`` (empty: the invoice's),
        ``vat_category`` (empty: the invoice's), ``discount_percent``, ``discount_amount``,
        ``position``. A time or cost line whose description, quantity or price changes is marked as
        edited by hand, as in the edit form. The caller commits.
        """
        self._require_draft(invoice)
        # Time lines and cost lines remember what was changed by hand (Regroup keeps or rebuilds them)
        is_time = item.kind in (LINE_KIND_TIME, LINE_KIND_COST)
        if "description" in values:
            text = self.normalize_description(values["description"])
            if not text:
                raise InvalidLineValueError("description", "required")
            if text != self.normalize_description(item.description):
                item.description = text[:500]
                if is_time:
                    item.description_edited = True
        if "quantity" in values:
            quantity = self.parse_amount(values["quantity"], "quantity", minimum=Decimal("0")).quantize(MONEY_PLACES)
            if quantity != Decimal(str(item.quantity or 0)).quantize(MONEY_PLACES):
                item.quantity = quantity
                if is_time:
                    item.quantity_edited = True
        if "unit_price" in values:
            price = self.parse_amount(values["unit_price"], "unit_price").quantize(MONEY_PLACES)
            if price != Decimal(str(item.unit_price or 0)).quantize(MONEY_PLACES):
                item.unit_price = price
                if is_time:
                    item.price_edited = True
        if "tax_rate" in values:
            rate = self.parse_amount(values["tax_rate"], "tax_rate", allow_empty=True, minimum=Decimal("0"))
            item.tax_rate = rate
        if "vat_category" in values:
            category = (values["vat_category"] or "").strip().upper() or None
            if category is not None and category not in VAT_CATEGORIES:
                raise InvalidLineValueError("vat_category", "unknown")
            item.vat_category = category
        if "discount_percent" in values:
            percent = self.parse_amount(
                values["discount_percent"], "discount_percent", allow_empty=True, minimum=Decimal("0")
            )
            if percent is not None and percent > 100:
                raise InvalidLineValueError("discount_percent", "too_high")
            item.discount_percent = percent or Decimal("0")
        if "discount_amount" in values:
            amount = self.parse_amount(
                values["discount_amount"], "discount_amount", allow_empty=True, minimum=Decimal("0")
            )
            item.discount_amount = amount or Decimal("0")
        if "position" in values:
            position = self.parse_amount(values["position"], "position", allow_empty=True)
            if position is not None:
                item.position = int(position)
        item.total_amount = item.line_net
        db.session.flush()
        invoice.calculate_totals()
        return item

    def delete_line(self, invoice: Invoice, item: InvoiceItem) -> Dict:
        """Delete a draft line; its time entries go back to Unbilled with the prepaid hours they used here,
        its project costs (a cost line) are unbilled again.

        Returns ``entries`` (how many the line had) and ``prepaid_freed`` (prepaid hours given back).
        """
        self._require_draft(invoice)
        hours = self.detach_lines(invoice, [item])
        freed = self.release_dropped_prepaid(invoice, hours.keys())
        # A cost line's project costs are unbilled again with it
        from app.models import ProjectCost

        for cost in ProjectCost.query.filter(ProjectCost.invoice_item_id == item.id).all():
            cost.unmark_as_invoiced()
        db.session.delete(item)
        db.session.flush()
        invoice.calculate_totals()
        return {"entries": len(hours), "prepaid_freed": freed}

    def _period_query(self, invoice: Invoice):
        """Time entries of the invoice's projects and period (None for an invoice without a period)."""
        from datetime import time as dt_time

        if invoice.period_start is None or invoice.period_end is None:
            return None
        project_ids, client_id = self._scope(invoice.project_id, invoice.client_id)
        start = datetime.combine(invoice.period_start, dt_time.min)
        end = datetime.combine(invoice.period_end, dt_time.max)
        scope = [TimeEntry.project_id.in_(project_ids)] if project_ids else []
        if client_id is not None:
            scope.append(TimeEntry.client_id == client_id)
        if not scope:
            return None
        return TimeEntry.query.filter(or_(*scope), TimeEntry.start_time >= start, TimeEntry.start_time <= end)

    @staticmethod
    def _draft_created_local(invoice: Invoice) -> Optional[datetime]:
        """When the draft was created, in the app's time zone (time entries store local times)."""
        if invoice.created_at is None:
            return None
        try:
            from app.utils.timezone import utc_to_local

            return utc_to_local(invoice.created_at).replace(tzinfo=None)
        except Exception:
            return invoice.created_at

    @staticmethod
    def _only_projects(query, allowed_project_ids: Optional[Iterable[int]]):
        """Limit a time entry query to the projects a user may see (None: no limit)."""
        if allowed_project_ids is None:
            return query
        allowed = [int(i) for i in allowed_project_ids]
        return query.filter(TimeEntry.project_id.in_(allowed or [-1]))

    def new_period_entries(
        self, invoice: Invoice, allowed_project_ids: Optional[Iterable[int]] = None
    ) -> List[TimeEntry]:
        """Entries the draft could bill that were logged after it was created ("new entries").

        The set the picker offers (billable, finished, on no invoice, on the invoice's projects)
        within the invoice's period, limited to ``allowed_project_ids`` (the projects the user may
        see; None: all). Empty for an invoice without a period.
        """
        if invoice.period_start is None or invoice.period_end is None:
            return []
        from datetime import time as dt_time

        project_ids, client_id = self._scope(invoice.project_id, invoice.client_id)
        query = self.unbilled_query(
            project_ids,
            datetime.combine(invoice.period_start, dt_time.min),
            datetime.combine(invoice.period_end, dt_time.max),
            client_id=client_id,
        )
        created = self._draft_created_local(invoice)
        if created is not None:
            query = query.filter(TimeEntry.created_at > created)
        query = self._only_projects(query, allowed_project_ids)
        return query.order_by(TimeEntry.start_time.asc(), TimeEntry.id.asc()).all()

    def running_period_entries(
        self, invoice: Invoice, allowed_project_ids: Optional[Iterable[int]] = None
    ) -> List[TimeEntry]:
        """Entries in the invoice's projects and period whose timer is still running.

        ``allowed_project_ids``: the projects the user may see (None: all).
        """
        query = self._period_query(invoice)
        if query is None:
            return []
        query = self._only_projects(query, allowed_project_ids)
        return query.filter(TimeEntry.end_time.is_(None)).order_by(TimeEntry.start_time.asc()).all()

    def add_new_entries(
        self,
        invoice: Invoice,
        entry_ids: Optional[Iterable[int]] = None,
        created_by: Optional[int] = None,
        allowed_project_ids: Optional[Iterable[int]] = None,
    ) -> Dict:
        """Add new entries of the period to the lines they belong to ("Add to matching lines").

        The entries first go through the client's prepaid hours (``PrepaidHoursAllocator``); the
        entries already on the draft keep theirs. An entry fully covered by prepaid hours gets a link
        without a line; the rest of an entry (all of it without prepaid hours) joins the time line with
        the same group (by the invoice's layout) and the same hourly rate: a line not edited by hand
        follows its entries (hours and text); an edited line keeps its text, and an edited quantity
        grows by those hours. Entries with no such line get new lines. ``entry_ids`` limits it to these
        of ``new_period_entries``; ``allowed_project_ids`` to the projects the user may see. Returns
        ``added`` (hours per line id), ``new_lines``, ``entries``, ``prepaid_hours`` (prepaid hours
        the new entries used), ``warnings`` (hours of new lines that had no rate) and ``skipped``
        (entries left out because their prepaid hours are recorded on another invoice). The caller commits.
        """
        from app.utils.invoice_time_entry_items import group_key, resolve_entry_rate
        from app.utils.prepaid_hours import PrepaidHoursAllocator

        self._require_draft(invoice)
        entries = self.new_period_entries(invoice, allowed_project_ids)
        if entry_ids is not None:
            wanted = {int(i) for i in entry_ids}
            entries = [e for e in entries if e.id in wanted]
        # An entry whose prepaid hours are recorded on another invoice cannot be allocated again
        # (one ledger row per entry): it is left out and reported
        skipped = self._prepaid_elsewhere(invoice, [e.id for e in entries])
        if skipped:
            entries = [e for e in entries if e.id not in skipped]
        if not entries:
            return {
                "added": {},
                "new_lines": 0,
                "entries": 0,
                "prepaid_hours": Decimal("0"),
                "warnings": [],
                "skipped": len(skipped),
            }

        allocator = PrepaidHoursAllocator(
            client=invoice.client,
            invoice=invoice,
            keep_entry_ids=self.invoice_entry_ids(invoice),
        )
        processed = allocator.process(entries)
        covered = [p for p in processed if p.prepaid_hours > 0 and p.billable_hours <= 0]
        if covered:
            self.link_entries(invoice, None, [(p.entry, p.prepaid_hours) for p in covered], created_by=created_by)
        to_bill = [p for p in processed if p.billable_hours > 0]

        layout = self._invoice_layout(invoice)
        lines: Dict[tuple, InvoiceItem] = {}
        for item in self._ordered_items(invoice):
            if item.kind != LINE_KIND_TIME:
                continue
            line_entries = self._line_entries(item)
            if not line_entries:
                continue
            first = sorted((e for e, _h in line_entries), key=lambda e: (e.start_time or datetime.min, e.id))[0]
            key = (group_key(layout, first), resolve_entry_rate(first).rate)
            lines.setdefault(key, item)

        added: Dict[int, Decimal] = {}
        leftovers = []
        for billed in to_bill:
            entry = billed.entry
            item = lines.get((group_key(layout, entry), resolve_entry_rate(entry).rate))
            if item is None:
                leftovers.append(billed)
                continue
            self.link_entries(invoice, item, [(entry, billed.billable_hours)], created_by=created_by)
            added[item.id] = added.get(item.id, Decimal("0")) + round_quantity(billed.billable_hours)

        by_id = {item.id: item for item in lines.values()}
        for item_id, hours in added.items():
            self.recalculate_line(invoice, by_id[item_id], hours_change=hours)

        new_lines, warnings = 0, []
        if leftovers:
            built = self.add_entries(
                invoice,
                leftovers,
                layout,
                invoice.line_template,
                created_by=created_by,
                remember=False,
            )
            new_lines, warnings = len(built.items), built.warnings
        invoice.calculate_totals()
        return {
            "added": added,
            "new_lines": new_lines,
            "skipped": len(skipped),
            "warnings": warnings,
            "entries": len(entries),
            "prepaid_hours": allocator.total_prepaid_hours_assigned,
        }

    @staticmethod
    def _prepaid_elsewhere(invoice: Invoice, entry_ids: List[int]) -> set:
        """Entries among ``entry_ids`` with a prepaid ledger row that does not belong to this invoice."""
        from app.models import ClientPrepaidConsumption

        if not entry_ids:
            return set()
        rows = (
            db.session.query(ClientPrepaidConsumption.time_entry_id)
            .filter(
                ClientPrepaidConsumption.time_entry_id.in_(entry_ids),
                or_(
                    ClientPrepaidConsumption.invoice_id.is_(None),
                    ClientPrepaidConsumption.invoice_id != invoice.id,
                ),
            )
            .all()
        )
        return {row[0] for row in rows}

    def draft_lines(self, invoice: Invoice) -> List[Dict]:
        """Lines of a draft with their entries, for the draft page, in a few queries.

        Each element: ``item``, ``entries`` (``[(link, entry)]`` by date), ``tracked`` (hours of
        the links, rounded as on the line) and ``kind``.
        """
        from sqlalchemy.orm import joinedload

        items = self._ordered_items(invoice)
        links = (
            InvoiceTimeLink.query.options(
                joinedload(InvoiceTimeLink.time_entry).joinedload(TimeEntry.user),
                joinedload(InvoiceTimeLink.time_entry).joinedload(TimeEntry.task),
                joinedload(InvoiceTimeLink.time_entry).joinedload(TimeEntry.project),
            )
            .filter(
                InvoiceTimeLink.invoice_id == invoice.id,
                InvoiceTimeLink.invoice_item_id.isnot(None),
                InvoiceTimeLink.released_at.is_(None),
            )
            .order_by(InvoiceTimeLink.id.asc())
            .all()
        )
        by_item: Dict[int, List[InvoiceTimeLink]] = {}
        for link in links:
            by_item.setdefault(link.invoice_item_id, []).append(link)
        result = []
        for item in items:
            item_links = sorted(
                by_item.get(item.id, []),
                key=lambda link: (link.time_entry.start_time or datetime.min, link.time_entry_id),
            )
            tracked = sum((round_quantity(Decimal(link.hours or 0)) for link in item_links), Decimal("0"))
            result.append(
                {
                    "item": item,
                    "kind": item.kind or LINE_KIND_MANUAL,
                    "entries": [(link, link.time_entry) for link in item_links],
                    "tracked": tracked,
                }
            )
        return result

    @staticmethod
    def snapshot_lines(invoice: Invoice) -> Dict[str, Dict]:
        """What a draft's lines look like before a form or the API replaces them (see ``carry_line_state``)."""
        by_id: Dict[int, Dict] = {}
        by_entries: Dict[frozenset, Dict] = {}
        for item in invoice.items.all():
            state = {
                "kind": item.kind,
                "description": item.description,
                "quantity": Decimal(str(item.quantity or 0)),
                "unit_price": Decimal(str(item.unit_price or 0)),
                "description_edited": bool(item.description_edited),
                "quantity_edited": bool(item.quantity_edited),
                "price_edited": bool(item.price_edited),
            }
            by_id[item.id] = state
            ids = frozenset(_parse_ids(item.time_entry_ids))
            if ids:
                by_entries.setdefault(ids, state)
        return {"by_id": by_id, "by_entries": by_entries}

    @staticmethod
    def previous_line_state(snapshot: Dict[str, Dict], time_entry_ids=None, item_id=None) -> Optional[Dict]:
        """The line a new line replaces: by its former id, else by the same time entries."""
        try:
            previous = snapshot["by_id"].get(int(item_id)) if item_id not in (None, "") else None
        except (TypeError, ValueError):
            previous = None
        if previous is None:
            previous = snapshot["by_entries"].get(frozenset(line_entry_ids(time_entry_ids)))
        return previous

    @staticmethod
    def normalize_description(text: Optional[str]) -> str:
        """Description as stored: line breaks as ``\\n``, no spaces at line ends or around the text."""
        lines = (text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
        return "\n".join(line.rstrip() for line in lines).strip()

    @staticmethod
    def tracked_quantity(item: InvoiceItem) -> Optional[Decimal]:
        """Quantity from a line's links: the sum of each link's hours rounded to 2 places."""
        links = InvoiceTimeLink.query.filter(
            InvoiceTimeLink.invoice_item_id == item.id, InvoiceTimeLink.released_at.is_(None)
        ).all()
        if not links:
            return None
        return sum((round_quantity(Decimal(link.hours or 0)) for link in links), Decimal("0"))

    @classmethod
    def carry_line_state(cls, snapshot: Dict[str, Dict], item: InvoiceItem, item_id=None) -> None:
        """Set the kind of a replaced line, its quantity, and what was changed by hand.

        Call after the line's entries are linked. A line with time entries is a time line, and its
        quantity is the tracked one (from its links) unless it was changed by hand: a submitted
        quantity that differs from the tracked one and from the line's previous quantity, or one
        already marked as edited, is kept and marks the line. The description and price are marked
        when they differ from the previous line's (line breaks and spaces at the ends do not count).
        A flag once set stays.
        """
        previous = cls.previous_line_state(snapshot, item.time_entry_ids, item_id)
        if not item.time_entry_ids:
            # A line typed in keeps its kind (a manual hours line stays one)
            kept = (previous or {}).get("kind")
            item.kind = kept if kept in (LINE_KIND_MANUAL, LINE_KIND_MANUAL_HOURS) else LINE_KIND_MANUAL
            return
        item.kind = LINE_KIND_TIME
        if previous is not None and previous["kind"] != "time":
            previous = None

        quantity = Decimal(str(item.quantity or 0)).quantize(Decimal("0.01"))
        tracked = cls.tracked_quantity(item)
        if tracked is not None and quantity != tracked:
            untouched = previous is not None and quantity == previous["quantity"].quantize(Decimal("0.01"))
            if (previous is None or untouched) and not (previous or {}).get("quantity_edited"):
                # Not changed by hand: follow the entries
                item.quantity = tracked
                item.total_amount = item.line_net
            else:
                item.quantity_edited = True
        if previous is None:
            return

        unit_price = Decimal(str(item.unit_price or 0)).quantize(Decimal("0.01"))
        item.description_edited = previous["description_edited"] or (
            cls.normalize_description(item.description) != cls.normalize_description(previous["description"])
        )
        item.quantity_edited = bool(previous["quantity_edited"] or item.quantity_edited)
        item.price_edited = previous["price_edited"] or unit_price != previous["unit_price"].quantize(Decimal("0.01"))

    def unlink_invoice(self, invoice: Invoice) -> List[int]:
        """Remove every link of a draft invoice. Returns the entry IDs it billed, in link order."""
        self._require_draft(invoice)
        entry_ids = self.invoice_entry_ids(invoice)
        for link in InvoiceTimeLink.query.filter(
            InvoiceTimeLink.invoice_id == invoice.id, InvoiceTimeLink.released_at.is_(None)
        ).all():
            db.session.delete(link)
        db.session.flush()
        return entry_ids

    def release(self, invoice: Invoice, reason: Optional[str] = None) -> int:
        """Let go of a cancelled invoice's hours.

        Links get ``released_at`` and stay as history; entries this invoice marked paid are unpaid
        again; project costs, expenses and prepaid hours are released. Returns the number of links.
        """
        links = InvoiceTimeLink.query.filter(
            InvoiceTimeLink.invoice_id == invoice.id, InvoiceTimeLink.released_at.is_(None)
        ).all()
        now = datetime.utcnow()
        entry_ids = set()
        for link in links:
            link.released_at = now
            link.released_reason = (reason or "invoice cancelled")[:255]
            entry_ids.add(link.time_entry_id)

        if entry_ids:
            for entry in TimeEntry.query.filter(TimeEntry.id.in_(entry_ids)).all():
                if entry.paid and (entry.invoice_number or None) == invoice.invoice_number:
                    entry.paid = False
                    entry.invoice_number = None

        invoice.release_invoiced_costs_and_expenses()
        db.session.flush()
        return len(links)

    def on_status_change(self, invoice: Invoice, previous_status: Optional[str]) -> int:
        """Call after an invoice's status changed: a newly cancelled invoice releases its hours.

        Refuses a change out of ``cancelled``: its links are released, so bringing it back would
        bill hours that may already be on another invoice.
        """
        if previous_status == "cancelled" and invoice.status != "cancelled":
            raise InvoiceStatusChangeError(invoice, previous_status)
        if invoice.status == "cancelled" and previous_status != "cancelled":
            return self.release(invoice, reason=f"invoice cancelled (was {previous_status or 'draft'})")
        return 0


def _parse_ids(csv: Optional[str]) -> List[int]:
    ids: List[int] = []
    for part in (csv or "").split(","):
        part = part.strip()
        if part.isdigit() and int(part) not in ids:
            ids.append(int(part))
    return ids


parse_time_entry_ids = _parse_ids


def line_entry_ids(value) -> List[int]:
    """Entry IDs of a line as sent by a form or the API: a comma-separated string or a list."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        value = ",".join(str(v) for v in value)
    return _parse_ids(str(value))
