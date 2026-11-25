"""Step 1 of an invoice: which hours it bills, and to whom.

Step 1 decides the client, the period, the client's projects and how hours become lines. This
service works out what the step 1 page shows (hours per project for the period, the warnings, the
number of lines and the amount), collects the hours when the draft is created, and collects them
again when step 1 of a draft is saved with another period, other projects or another layout.
"""

from __future__ import annotations

import calendar
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from sqlalchemy import and_, exists, func, or_
from sqlalchemy.orm import joinedload

from app import db
from app.models import (
    Client,
    ClientPrepaidConsumption,
    Expense,
    Invoice,
    InvoiceTimeLink,
    Project,
    ProjectCost,
    RateOverride,
    TimeEntry,
    User,
)
from app.services.invoice_costs_service import (
    COSTS_BY_COST,
    InvoiceCostsService,
    cost_amount,
    cost_statuses,
    expense_amount,
    expense_statuses,
    normalize_costs_layout,
)
from app.services.invoice_time_service import LINE_KIND_MANUAL, LINE_KIND_MANUAL_HOURS, InvoiceTimeService
from app.utils.invoice_time_entry_items import (
    LAYOUT_NONE,
    BillableTimeEntry,
    EntryRate,
    build_time_entry_lines,
    default_line_template,
    layout_examples,
    normalize_layout,
    normalize_template,
    round_quantity,
)
from app.utils.prepaid_hours import PrepaidHoursAllocator

PERIOD_LAST_MONTH = "last_month"
PERIOD_THIS_MONTH = "this_month"
PERIOD_CUSTOM = "custom"
PERIOD_ALL = "all"
PERIOD_KINDS = (PERIOD_LAST_MONTH, PERIOD_THIS_MONTH, PERIOD_CUSTOM, PERIOD_ALL)

HOURS = Decimal("0.01")
SECONDS_IN_HOUR = Decimal("3600")
# Lines added by hand on a draft; hours lines and cost lines are collected by step 1
BY_HAND_KINDS = (LINE_KIND_MANUAL, LINE_KIND_MANUAL_HOURS)


class StepOneError(ValueError):
    """Step 1 cannot be used as posted (a wrong period, no project, a project of another client)."""


def _hours(seconds) -> Decimal:
    return (Decimal(int(seconds or 0)) / SECONDS_IN_HOUR).quantize(HOURS)


def _month_bounds(day: date) -> Tuple[date, date]:
    return day.replace(day=1), day.replace(day=calendar.monthrange(day.year, day.month)[1])


@dataclass
class BillingPeriod:
    """The period an invoice bills: entries that start on ``start``…``end`` (both included).

    ``start`` and ``end`` are None for "All unbilled".
    """

    kind: str
    start: Optional[date] = None
    end: Optional[date] = None

    @property
    def start_at(self) -> Optional[datetime]:
        return datetime.combine(self.start, time.min) if self.start else None

    @property
    def end_at(self) -> Optional[datetime]:
        return datetime.combine(self.end, time.max) if self.end else None

    def issue_date(self, today: Optional[date] = None) -> date:
        """Default issue date: the last day of the period; today for This month and All unbilled."""
        today = today or date.today()
        if self.kind in (PERIOD_THIS_MONTH, PERIOD_ALL) or self.end is None:
            return today
        return self.end


def resolve_period(kind: Optional[str], start=None, end=None, today: Optional[date] = None) -> BillingPeriod:
    """The period for a step 1 choice. ``start`` / ``end`` (dates or ISO strings) count for Custom only."""
    today = today or date.today()
    kind = kind if kind in PERIOD_KINDS else PERIOD_LAST_MONTH
    if kind == PERIOD_ALL:
        return BillingPeriod(PERIOD_ALL)
    if kind == PERIOD_THIS_MONTH:
        first, last = _month_bounds(today)
        return BillingPeriod(PERIOD_THIS_MONTH, first, last)
    if kind == PERIOD_CUSTOM:
        start, end = _parse_day(start), _parse_day(end)
        if start is None or end is None:
            raise StepOneError("Enter both dates of the period")
        if start > end:
            raise StepOneError("The period starts after it ends")
        return BillingPeriod(PERIOD_CUSTOM, start, end)
    first, last = _month_bounds(today.replace(day=1) - timedelta(days=1))
    return BillingPeriod(PERIOD_LAST_MONTH, first, last)


def period_from_dates(start: Optional[date], end: Optional[date], today: Optional[date] = None) -> BillingPeriod:
    """How step 1 shows a stored period: Last month or This month when it is one, else Custom."""
    if start is None and end is None:
        return BillingPeriod(PERIOD_ALL)
    for kind in (PERIOD_LAST_MONTH, PERIOD_THIS_MONTH):
        candidate = resolve_period(kind, today=today)
        if (candidate.start, candidate.end) == (start, end):
            return candidate
    return BillingPeriod(PERIOD_CUSTOM, start, end)


def _parse_day(value) -> Optional[date]:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value or "").strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


class RateTable:
    """Hourly rates of many time entries from one query.

    Gives the same answer as ``resolve_entry_rate``: the person's override for the date, the
    project's override for the date, the project's rate, the client's rate; the client's rate for
    an entry logged on the client without a project.
    """

    def __init__(self, project_ids: Iterable[Optional[int]]):
        ids = sorted({pid for pid in project_ids if pid})
        self._overrides: Dict[Tuple[int, Optional[int]], List[RateOverride]] = defaultdict(list)
        if ids:
            for row in RateOverride.query.filter(RateOverride.project_id.in_(ids)).all():
                self._overrides[(row.project_id, row.user_id)].append(row)
        for rows in self._overrides.values():
            # Latest start first, open start last (``order_by(effective_from.desc().nullslast())``)
            rows.sort(key=lambda r: (r.effective_from is None, -(r.effective_from or date.min).toordinal(), r.id))

    def _override(self, project_id: int, user_id: Optional[int], on_date: Optional[date]) -> Optional[RateOverride]:
        for row in self._overrides.get((project_id, user_id), []):
            if on_date is None:
                return row
            if (row.effective_from is None or row.effective_from <= on_date) and (
                row.effective_to is None or row.effective_to >= on_date
            ):
                return row
        return None

    def __call__(self, entry: TimeEntry) -> EntryRate:
        project = getattr(entry, "project", None)
        if project is None:
            # Logged on the client without a project: the client's rate
            client = getattr(entry, "client", None)
            if client is not None and client.default_hourly_rate:
                return EntryRate(Decimal(client.default_hourly_rate), True)
            return EntryRate(Decimal("0"), False)
        on_date = entry.start_time.date() if entry.start_time else None
        if entry.user_id is not None:
            row = self._override(project.id, entry.user_id, on_date)
            if row is not None:
                return EntryRate(Decimal(row.hourly_rate), True)
        row = self._override(project.id, None, on_date)
        if row is not None:
            return EntryRate(Decimal(row.hourly_rate), True)
        if project.hourly_rate:
            return EntryRate(Decimal(project.hourly_rate), True)
        client = getattr(project, "client_obj", None)
        if client is not None and client.default_hourly_rate:
            return EntryRate(Decimal(client.default_hourly_rate), True)
        return EntryRate(Decimal("0"), False)


@dataclass
class StepOneSelection:
    """What step 1 posts about the hours: client, projects, period, layout and line template.

    ``client_entries``: time logged straight on the client, without a project, is billed too (only
    with ``client_entries_allowed``).
    ``invoice``: the draft whose step 1 this is; its own hours count as available.
    """

    client: Client
    project_ids: List[int]
    period: BillingPeriod
    layout: Optional[str] = None
    template: Optional[str] = None
    client_entries: bool = False
    currency: Optional[str] = None
    invoice: Optional[Invoice] = None
    primary_project_id: Optional[int] = None
    # False for a user limited to their own or assigned projects: time logged on the client without
    # a project is not theirs to see or bill
    client_entries_allowed: bool = True
    # Expenses and project costs ticked on the page (None: the page posted none, defaults apply) and
    # those it showed: one it did not show yet is ticked by default (see ``expenses_and_costs``)
    expense_ids: Optional[List[int]] = None
    expense_seen: List[int] = field(default_factory=list)
    cost_ids: Optional[List[int]] = None
    cost_seen: List[int] = field(default_factory=list)
    costs_layout: Optional[str] = None

    def __post_init__(self):
        if not self.client_entries_allowed:
            self.client_entries = False

    @property
    def collects_hours(self) -> bool:
        return normalize_layout(self.layout) != LAYOUT_NONE


@dataclass
class StepOneSummary:
    """What the step 1 page shows below the period."""

    period: BillingPeriod
    projects: List[Dict] = field(default_factory=list)
    client_entries: Optional[Dict] = None
    tracked_hours: Decimal = Decimal("0")
    prepaid_hours: Decimal = Decimal("0")
    billed_hours: Decimal = Decimal("0")
    amount: Decimal = Decimal("0")
    lines: int = 0
    layout: str = ""
    template: str = ""
    examples: Dict[str, Dict] = field(default_factory=dict)
    prepaid: Optional[Dict] = None
    warnings: List[Dict] = field(default_factory=list)
    # Step 1 of a draft: the draft as it will be after Save (see ``draft_amount``)
    draft: Optional[Dict] = None
    first_entry_date: Optional[date] = None
    last_entry_date: Optional[date] = None
    # Expenses and project costs of the period: every one listed, with ``checked`` for those billed
    expenses: List[Dict] = field(default_factory=list)
    costs: List[Dict] = field(default_factory=list)
    expenses_total: Decimal = Decimal("0")
    costs_total: Decimal = Decimal("0")
    costs_layout: str = COSTS_BY_COST
    cost_lines: int = 0


@dataclass
class ExpensesAndCosts:
    """What step 1 bills besides hours: every expense and cost listed, and those ticked."""

    expenses: List[Expense] = field(default_factory=list)
    chosen_expenses: List[Expense] = field(default_factory=list)
    costs: List[ProjectCost] = field(default_factory=list)
    chosen_costs: List[ProjectCost] = field(default_factory=list)
    layout: str = COSTS_BY_COST
    # Step 1 of a draft: the costs and their layout are those the draft already bills
    costs_unchanged: bool = False


class InvoiceStepOneService:
    """Step 1 of an invoice: the page's numbers and warnings, and collecting the hours."""

    def __init__(self):
        self.time_links = InvoiceTimeService()
        self.costs = InvoiceCostsService()

    # ------------------------------------------------------------------
    # Which entries step 1 may bill
    # ------------------------------------------------------------------
    @staticmethod
    def _linked_to(invoice: Optional[Invoice]):
        if invoice is None or invoice.id is None:
            return None
        return exists().where(
            and_(
                InvoiceTimeLink.time_entry_id == TimeEntry.id,
                InvoiceTimeLink.invoice_id == invoice.id,
                InvoiceTimeLink.released_at.is_(None),
            )
        )

    def available_clause(self, invoice: Optional[Invoice] = None):
        """Finished entries step 1 may bill: billable and on no invoice, or already on this draft."""
        unbilled = and_(
            TimeEntry.billable == True,  # noqa: E712
            TimeEntry.paid == False,  # noqa: E712
            ~exists().where(and_(InvoiceTimeLink.time_entry_id == TimeEntry.id, InvoiceTimeLink.released_at.is_(None))),
        )
        own = self._linked_to(invoice)
        return and_(TimeEntry.end_time.isnot(None), or_(unbilled, own) if own is not None else unbilled)

    @staticmethod
    def scope_clause(project_ids: Sequence[int], client_id: Optional[int], client_entries: bool):
        """Entries of these projects, plus entries logged on the client without a project."""
        parts = []
        ids = [pid for pid in project_ids if pid]
        if ids:
            parts.append(TimeEntry.project_id.in_(ids))
        if client_entries and client_id:
            parts.append(and_(TimeEntry.project_id.is_(None), TimeEntry.client_id == client_id))
        return or_(*parts) if parts else db.false()

    @staticmethod
    def _period_clause(period: BillingPeriod):
        parts = []
        if period.start_at is not None:
            parts.append(TimeEntry.start_time >= period.start_at)
        if period.end_at is not None:
            parts.append(TimeEntry.start_time <= period.end_at)
        return and_(*parts) if parts else db.true()

    def client_projects(self, client: Client, user=None, invoice: Optional[Invoice] = None) -> List[Project]:
        """The client's billable projects step 1 offers: active ones, and others that still have hours to bill.

        A user limited to assigned projects (subcontractor) gets those only; a draft's own project is
        always offered.
        """
        from app.utils.scope_filter import apply_project_scope_to_model

        query = Project.query.filter(Project.client_id == client.id, Project.billable == True)  # noqa: E712
        scope = apply_project_scope_to_model(Project, user)
        if scope is not None:
            query = query.filter(scope)
        projects = query.order_by(Project.name.asc(), Project.id.asc()).all()
        inactive = [p.id for p in projects if p.status != "active"]
        with_hours = set()
        if inactive:
            with_hours = {
                row[0]
                for row in db.session.query(TimeEntry.project_id)
                .filter(TimeEntry.project_id.in_(inactive), self.available_clause(invoice))
                .distinct()
                .all()
            }
        offered = [p for p in projects if p.status == "active" or p.id in with_hours]
        if invoice is not None and invoice.project is not None and invoice.project not in offered:
            offered = sorted(offered + [invoice.project], key=lambda p: (p.name or "", p.id))
        return offered

    def hours_by_project(
        self,
        client: Client,
        project_ids: Sequence[int],
        period: BillingPeriod,
        invoice: Optional[Invoice] = None,
        client_entries: bool = True,
    ) -> Dict[Optional[int], Tuple[int, int]]:
        """{project_id (None: logged on the client): (seconds, entries)} that step 1 may bill in the period.

        Time logged on the client without a project is counted only with ``client_entries``.
        """
        rows = (
            db.session.query(
                TimeEntry.project_id, func.coalesce(func.sum(TimeEntry.duration_seconds), 0), func.count(TimeEntry.id)
            )
            .filter(
                self.available_clause(invoice),
                self.scope_clause(project_ids, client.id, client_entries),
                self._period_clause(period),
            )
            .group_by(TimeEntry.project_id)
            .all()
        )
        return {project_id: (int(seconds or 0), int(count or 0)) for project_id, seconds, count in rows}

    def collect(self, selection: StepOneSelection, *, invoice: Optional[Invoice] = None) -> List[TimeEntry]:
        """Entries the selection bills, oldest first, with their project, person and task loaded."""
        return (
            TimeEntry.query.options(
                joinedload(TimeEntry.project).joinedload(Project.client_obj),
                joinedload(TimeEntry.client),
                joinedload(TimeEntry.user),
                joinedload(TimeEntry.task),
            )
            .filter(
                self.available_clause(invoice),
                self.scope_clause(selection.project_ids, selection.client.id, selection.client_entries),
                self._period_clause(selection.period),
            )
            .order_by(TimeEntry.start_time.asc(), TimeEntry.id.asc())
            .all()
        )

    # ------------------------------------------------------------------
    # Prepaid hours (read only)
    # ------------------------------------------------------------------
    @staticmethod
    def _used_by_month(client: Client, months: Iterable[date], invoice: Optional[Invoice]) -> Dict[date, Dict]:
        """{cycle start: {"seconds", "invoice_id"}} of prepaid hours other invoices already use."""
        months = sorted(set(m for m in months if m))
        if not months:
            return {}
        query = db.session.query(
            ClientPrepaidConsumption.allocation_month,
            ClientPrepaidConsumption.seconds_consumed,
            ClientPrepaidConsumption.invoice_id,
        ).filter(ClientPrepaidConsumption.client_id == client.id, ClientPrepaidConsumption.allocation_month.in_(months))
        if invoice is not None and invoice.id is not None:
            query = query.filter(
                or_(ClientPrepaidConsumption.invoice_id.is_(None), ClientPrepaidConsumption.invoice_id != invoice.id)
            )
        used: Dict[date, Dict] = {}
        for month, seconds, invoice_id in query.order_by(ClientPrepaidConsumption.id.asc()).all():
            slot = used.setdefault(month, {"seconds": 0, "invoice_id": None})
            slot["seconds"] += int(seconds or 0)
            if invoice_id:
                slot["invoice_id"] = invoice_id
        return used

    def prepaid_plan(
        self, client: Client, period: BillingPeriod, entries: Sequence[TimeEntry], invoice: Optional[Invoice] = None
    ) -> Tuple[Optional[Dict], Dict[int, Decimal]]:
        """The client's prepaid plan for the period, and how many hours of each entry it would cover.

        Same allocation as ``PrepaidHoursAllocator.process`` (oldest entry first, hours rounded to
        2 places), without writing anything.
        """
        if not client.prepaid_plan_enabled:
            return None, {}
        plan = client.prepaid_hours_decimal
        months = {client.prepaid_month_start(e.start_time) for e in entries if e.start_time}
        for day in (period.start, period.end):
            if day is not None:
                months.add(client.prepaid_month_start(datetime.combine(day, time.min)))
        if not months:
            months.add(client.prepaid_month_start(datetime.combine(date.today(), time.min)))
        used = self._used_by_month(client, months, invoice)
        left = {m: max(plan - _hours(used.get(m, {}).get("seconds", 0)), Decimal("0")) for m in months}
        before = dict(left)

        covered: Dict[int, Decimal] = {}
        for entry in sorted(entries, key=lambda e: (e.start_time or datetime.min)):
            month = client.prepaid_month_start(entry.start_time) if entry.start_time else None
            hours = _hours(entry.duration_seconds)
            if month is None or hours <= 0 or left.get(month, Decimal("0")) <= 0:
                continue
            take = min(hours, left[month]).quantize(HOURS)
            left[month] -= take
            covered[entry.id] = take

        used_on = {}
        invoice_ids = {slot["invoice_id"] for slot in used.values() if slot.get("invoice_id")}
        if invoice_ids:
            numbers = dict(
                db.session.query(Invoice.id, Invoice.invoice_number).filter(Invoice.id.in_(invoice_ids)).all()
            )
            used_on = {m: numbers.get(slot.get("invoice_id")) for m, slot in used.items()}
        return (
            {
                "plan_hours": plan,
                "reset_day": client.prepaid_reset_day or 1,
                "months": [
                    {
                        "month": month,
                        "left": before[month].quantize(HOURS),
                        "used_on": used_on.get(month),
                        "covers": (before[month] - left[month]).quantize(HOURS),
                    }
                    for month in sorted(months)
                ],
            },
            covered,
        )

    # ------------------------------------------------------------------
    # The page
    # ------------------------------------------------------------------
    def summary(
        self, selection: StepOneSelection, projects: Sequence[Project], remove_line_ids: Iterable[int] = ()
    ) -> StepOneSummary:
        """What the step 1 page shows for this selection; ``projects`` are the ones it lists.

        For a draft, ``remove_line_ids`` are its lines added by hand marked Remove: the amount leaves them out.
        """
        client = selection.client
        invoice = selection.invoice
        period = selection.period
        selected = [pid for pid in selection.project_ids if pid in {p.id for p in projects}]
        result = StepOneSummary(period=period)

        by_project = self.hours_by_project(
            client, [p.id for p in projects], period, invoice, client_entries=selection.client_entries_allowed
        )
        for project in projects:
            seconds, count = by_project.get(project.id, (0, 0))
            result.projects.append({"id": project.id, "name": project.name, "hours": _hours(seconds), "entries": count})
        seconds, count = by_project.get(None, (0, 0))
        if count:
            result.client_entries = {"hours": _hours(seconds), "entries": count}

        entries = self.collect(
            StepOneSelection(
                client=client,
                project_ids=selected,
                period=period,
                client_entries=selection.client_entries,
                invoice=invoice,
                client_entries_allowed=selection.client_entries_allowed,
            ),
            invoice=invoice,
        )
        if entries:
            result.first_entry_date = entries[0].start_time.date()
            result.last_entry_date = entries[-1].start_time.date()
        result.tracked_hours = sum((round_quantity(_hours(e.duration_seconds)) for e in entries), Decimal("0"))

        primary = self.primary_project(selection, projects)
        layout, template = self.time_links.resolve_layout(primary, selection.layout, selection.template)
        result.layout, result.template = layout, template
        rates = RateTable([e.project_id for e in entries])

        prepaid, covered = self.prepaid_plan(client, period, entries, invoice)
        result.prepaid = prepaid
        billable = []
        for entry in entries:
            hours = _hours(entry.duration_seconds) - covered.get(entry.id, Decimal("0"))
            if hours > 0:
                billable.append(BillableTimeEntry(entry=entry, billable_hours=hours))
        if layout != LAYOUT_NONE:
            result.prepaid_hours = sum(covered.values(), Decimal("0"))
            lines = build_time_entry_lines(
                None,
                billable,
                layout=layout,
                template=template,
                project_name=primary.name if primary is not None else None,
                currency=selection.currency,
                rate_resolver=rates,
            )
            result.lines = len(lines.items)
            result.billed_hours = sum((Decimal(item.quantity) for item in lines.items), Decimal("0"))
            result.amount = sum((item.line_net for item in lines.items), Decimal("0")).quantize(HOURS)
            entry_projects = {e.id: e.project_id for e in entries}
            names = {p.id: p.name for p in projects}
            for missing in lines.missing_rates:
                project_id = next((entry_projects.get(i) for i in missing.entry_ids if entry_projects.get(i)), None)
                result.warnings.append(
                    {
                        "kind": "no_rate",
                        "hours": missing.rounded_hours,
                        "entries": len(missing.entry_ids),
                        "client_id": client.id if project_id is None else None,
                        "project_id": project_id,
                        "project": names.get(project_id) or missing.project_name,
                        "person": missing.user_name,
                    }
                )
        # Like Generate from Time: a template of one's own applies to every layout, else each its default
        custom = normalize_template(selection.template)
        result.examples = layout_examples(
            billable[:1000],
            template=custom if custom and custom != default_line_template(layout) else None,
            currency=selection.currency,
            project_name=primary.name if primary is not None else None,
            rate_resolver=rates,
        )

        if prepaid is not None and selection.collects_hours:
            for month in prepaid["months"]:
                if month["left"] <= 0 and month["used_on"]:
                    result.warnings.append({"kind": "prepaid_used_up", **month})
                elif month["covers"] > 0:
                    result.warnings.append({"kind": "prepaid_left", **month})
        result.warnings.extend(self._hour_warnings(selection, projects, by_project))
        manual = self.manual_lines(invoice) if invoice is not None else []
        if manual:
            result.warnings.append(
                {
                    "kind": "manual_lines",
                    "lines": [
                        {"id": item.id, "description": item.description, "amount": Decimal(item.line_net)}
                        for item in manual
                    ],
                }
            )
        self._fill_expenses_and_costs(result, selection)
        if invoice is not None:
            if not self.hours_changed(self.draft_selection(invoice), selection):
                # Same hours: Save leaves the hours lines as they are, edits included
                current = [item for item in invoice.items.all() if item.kind == "time"]
                result.lines = len(current)
                result.billed_hours = sum((Decimal(item.quantity) for item in current), Decimal("0"))
                result.amount = sum((Decimal(item.line_net) for item in current), Decimal("0")).quantize(HOURS)
                result.prepaid_hours = sum(
                    (Decimal(link.hours) for link in invoice.time_links.all() if link.invoice_item_id is None),
                    Decimal("0"),
                )
            result.draft = self.draft_amount(
                invoice, result.amount, remove_line_ids, result.expenses_total, result.costs_total
            )
        return result

    @staticmethod
    def manual_lines(invoice: Invoice) -> List:
        """A draft's lines added by hand (fixed fees, hours lines typed in): saving step 1 keeps them.

        Hours lines and cost lines are not among them: step 1 collects those.
        """
        if invoice is None or invoice.id is None:
            return []
        return sorted(
            (item for item in invoice.items.all() if (item.kind or LINE_KIND_MANUAL) in BY_HAND_KINDS),
            key=lambda i: (i.position or 0, i.id or 0),
        )

    def draft_amount(
        self,
        invoice: Invoice,
        hours_net: Decimal,
        remove_line_ids: Iterable[int] = (),
        expenses_net: Optional[Decimal] = None,
        costs_net: Optional[Decimal] = None,
    ) -> Dict:
        """The draft's amount before tax after Save, counted as ``Invoice.calculate_totals`` does.

        ``hours_net``: the hours lines after Save (as they are, or collected again); ``expenses_net``
        and ``costs_net``: the expenses and cost lines after Save (None: as on the draft). Lines added
        by hand marked Remove are left out; goods and the invoice discount count as on the draft.
        """
        remove = set(remove_line_ids or ())
        by_hand = sum(
            (Decimal(item.line_net) for item in self.manual_lines(invoice) if item.id not in remove), Decimal("0")
        )
        goods = sum((Decimal(str(g.total_amount or 0)) for g in invoice.extra_goods), Decimal("0"))
        if expenses_net is None:
            expenses_net = sum((Decimal(str(e.total_amount or 0)) for e in invoice.expenses), Decimal("0"))
        if costs_net is None:
            costs_net = sum((Decimal(i.line_net) for i in self.costs.cost_lines(invoice)), Decimal("0"))
        combined = Decimal(hours_net) + by_hand + goods + Decimal(expenses_net) + Decimal(costs_net)
        discount = Decimal(str(invoice.discount_amount or 0))
        if not discount and invoice.discount_percent and combined:
            discount = combined * (Decimal(str(invoice.discount_percent)) / 100)
        return {
            "hours": Decimal(hours_net).quantize(HOURS),
            "by_hand": by_hand.quantize(HOURS),
            "expenses": Decimal(expenses_net).quantize(HOURS),
            "costs": Decimal(costs_net).quantize(HOURS),
            "other": goods.quantize(HOURS),
            "discount": discount.quantize(HOURS),
            "total": (combined - discount).quantize(HOURS),
        }

    # ------------------------------------------------------------------
    # Expenses and project costs
    # ------------------------------------------------------------------
    @staticmethod
    def scope_changed(before: StepOneSelection, after: StepOneSelection) -> bool:
        """Whether a draft's expenses and costs are collected again: another period or other projects."""
        return (
            (before.period.start, before.period.end) != (after.period.start, after.period.end)
            or sorted(set(before.project_ids)) != sorted(set(after.project_ids))
            or bool(before.client_entries) != bool(after.client_entries)
        )

    def expenses_and_costs(self, selection: StepOneSelection) -> ExpensesAndCosts:
        """Expenses and project costs step 1 lists for the selection, and those it bills.

        A new invoice ticks every one (rejected expenses are not listed). Step 1 of a draft with the
        same period and projects lists what the draft bills (ticked) and the rest of the period (not
        ticked, as for hours: Save changes nothing); with another period or other projects everything
        of the new period is ticked, and what the draft billed outside it is let go.
        """
        invoice = selection.invoice
        draft = invoice is not None and invoice.id is not None
        changed = not draft or self.scope_changed(self.draft_selection(invoice), selection)
        start, end = selection.period.start, selection.period.end
        expenses = self.costs.period_expenses(
            selection.client.id,
            selection.project_ids,
            start,
            end,
            client_entries=selection.client_entries and selection.client_entries_allowed,
            invoice=invoice,
            keep_own=not changed,
        )
        costs = self.costs.period_costs(selection.project_ids, start, end, invoice=invoice, keep_own=not changed)

        def default(item):
            return changed or item.invoice_id == invoice.id

        layout = normalize_costs_layout(selection.costs_layout)
        if layout is None:
            layout = self.costs.invoice_layout(invoice) if draft else COSTS_BY_COST
        result = ExpensesAndCosts(
            expenses=expenses,
            chosen_expenses=self.costs.choose(expenses, selection.expense_ids, selection.expense_seen, default),
            costs=costs,
            chosen_costs=self.costs.choose(costs, selection.cost_ids, selection.cost_seen, default),
            layout=layout,
        )
        if draft:
            linked = {c.id for c in self.costs.invoice_costs(invoice) if c.invoice_item_id}
            result.costs_unchanged = {c.id for c in result.chosen_costs} == linked and (
                layout == self.costs.invoice_layout(invoice)
            )
        return result

    def _fill_expenses_and_costs(self, result: StepOneSummary, selection: StepOneSelection) -> None:
        extra = self.expenses_and_costs(selection)
        currency = selection.currency
        chosen_expenses = {e.id for e in extra.chosen_expenses}
        chosen_costs = {c.id for c in extra.chosen_costs}
        for expense in extra.expenses:
            person = (expense.user.display_name or expense.user.username) if expense.user else ""
            result.expenses.append(
                {
                    "id": expense.id,
                    "date": expense.expense_date,
                    "title": expense.title,
                    "category": expense.category,
                    "person": person,
                    "project": expense.project.name if expense.project else None,
                    "amount": expense_amount(expense),
                    "currency": expense.currency_code,
                    "other_currency": bool(currency) and expense.currency_code != currency,
                    "statuses": expense_statuses(expense),
                    "checked": expense.id in chosen_expenses,
                }
            )
        for cost in extra.costs:
            result.costs.append(
                {
                    "id": cost.id,
                    "date": cost.cost_date,
                    "description": cost.description,
                    "category": cost.category_name,
                    "amount": cost_amount(cost),
                    "currency": cost.currency_code,
                    "other_currency": bool(currency) and cost.currency_code != currency,
                    "statuses": cost_statuses(cost),
                    "checked": cost.id in chosen_costs,
                }
            )
        result.expenses_total = sum((expense_amount(e) for e in extra.chosen_expenses), Decimal("0"))
        result.costs_layout = extra.layout
        if extra.costs_unchanged:
            current = self.costs.cost_lines(selection.invoice)
            result.costs_total = sum((Decimal(item.line_net) for item in current), Decimal("0"))
            result.cost_lines = len(current)
        else:
            result.costs_total = sum((cost_amount(c) for c in extra.chosen_costs), Decimal("0"))
            result.cost_lines = len(self.costs.group_costs(extra.chosen_costs, extra.layout))

        pending = [e for e in extra.chosen_expenses if e.status == "pending"]
        if pending:
            result.warnings.append(
                {
                    "kind": "expenses_pending",
                    "expenses": [{"id": e.id, "title": e.title, "amount": expense_amount(e)} for e in pending],
                }
            )
        non_billable = [
            {"kind": "expense", "id": e.id, "title": e.title, "amount": expense_amount(e)}
            for e in extra.chosen_expenses
            if not e.billable
        ] + [
            {"kind": "cost", "id": c.id, "title": c.description, "amount": cost_amount(c)}
            for c in extra.chosen_costs
            if not c.billable
        ]
        if non_billable:
            result.warnings.append({"kind": "was_non_billable", "items": non_billable})

    def add_expenses_and_costs(self, invoice: Invoice, extra: ExpensesAndCosts) -> Dict[str, int]:
        """Bill the ticked expenses and costs on a new draft. The caller commits."""
        return self.costs.add_to_draft(invoice, extra.chosen_expenses, extra.chosen_costs, extra.layout)

    def sync_expenses_and_costs(self, invoice: Invoice, extra: ExpensesAndCosts) -> Dict[str, int]:
        """Step 1 of a draft saved: it bills the ticked expenses and costs. The caller commits."""
        return self.costs.sync_draft(invoice, extra.chosen_expenses, extra.chosen_costs, extra.layout)

    def remove_manual_lines(self, invoice: Invoice, item_ids: Iterable[int]) -> int:
        """Delete the draft's lines added by hand that step 1 marked Remove. The caller commits."""
        self.time_links._require_draft(invoice)
        ids = set(item_ids or ())
        removed = 0
        for item in self.manual_lines(invoice):
            if item.id in ids:
                db.session.delete(item)
                removed += 1
        if removed:
            db.session.flush()
        return removed

    def _hour_warnings(self, selection: StepOneSelection, projects, by_project) -> List[Dict]:
        """Running timers, hours before and after the period, other projects, non-billable entries."""
        client = selection.client
        invoice = selection.invoice
        period = selection.period
        scope = self.scope_clause(selection.project_ids, client.id, selection.client_entries)
        warnings: List[Dict] = []

        running = (
            db.session.query(User, Project.name)
            .join(TimeEntry, TimeEntry.user_id == User.id)
            .outerjoin(Project, Project.id == TimeEntry.project_id)
            .filter(TimeEntry.end_time.is_(None), scope)
            .order_by(TimeEntry.start_time.asc())
            .limit(20)
            .all()
        )
        if running:
            warnings.append(
                {
                    "kind": "timer_running",
                    "entries": len(running),
                    "people": sorted({(user.display_name or user.username) for user, _name in running}),
                    "projects": sorted({name for _user, name in running if name}),
                }
            )

        def aggregate(*criteria):
            return (
                db.session.query(
                    func.count(TimeEntry.id),
                    func.coalesce(func.sum(TimeEntry.duration_seconds), 0),
                    func.min(TimeEntry.start_time),
                    func.max(TimeEntry.start_time),
                )
                .filter(*criteria)
                .one()
            )

        available = self.available_clause(invoice)
        if period.start_at is not None:
            count, seconds, first, _last = aggregate(available, scope, TimeEntry.start_time < period.start_at)
            if count:
                warnings.append(
                    {
                        "kind": "before_period",
                        "entries": count,
                        "hours": _hours(seconds),
                        "since": first.date() if first else None,
                    }
                )

        selected = set(selection.project_ids)
        others = [
            {"id": p.id, "name": p.name, "hours": _hours(by_project[p.id][0])}
            for p in projects
            if p.id not in selected and by_project.get(p.id, (0, 0))[1]
        ]
        if not selection.client_entries and by_project.get(None, (0, 0))[1]:
            others.append({"id": None, "name": None, "hours": _hours(by_project[None][0])})
        if others:
            warnings.append(
                {
                    "kind": "other_projects",
                    "projects": others,
                    "hours": sum((o["hours"] for o in others), Decimal("0")),
                }
            )

        if period.end_at is not None:
            count, seconds, _first, last = aggregate(available, scope, TimeEntry.start_time > period.end_at)
            if count:
                warnings.append(
                    {"kind": "after_period", "entries": count, "hours": _hours(seconds), "until": last.date()}
                )

        count, seconds, _first, _last = aggregate(
            TimeEntry.billable == False,  # noqa: E712
            TimeEntry.end_time.isnot(None),
            TimeEntry.paid == False,  # noqa: E712
            ~exists().where(and_(InvoiceTimeLink.time_entry_id == TimeEntry.id, InvoiceTimeLink.released_at.is_(None))),
            scope,
            self._period_clause(period),
        )
        if count:
            warnings.append({"kind": "non_billable", "entries": count, "hours": _hours(seconds)})
        return warnings

    def number_period(self, selection: StepOneSelection) -> Optional[date]:
        """A day in the month the invoice bills, for {YYYY} and {MM} of its number.

        The period's last day; for All unbilled, the day of the last entry it bills (None without any).
        """
        if selection.period.end is not None:
            return selection.period.end
        last = (
            db.session.query(func.max(TimeEntry.start_time))
            .filter(
                self.available_clause(selection.invoice),
                self.scope_clause(
                    selection.project_ids,
                    selection.client.id,
                    selection.client_entries and selection.client_entries_allowed,
                ),
            )
            .scalar()
        )
        return last.date() if last else None

    @staticmethod
    def primary_project(selection: StepOneSelection, projects: Sequence[Project]) -> Optional[Project]:
        """The invoice's own project: the one step 1 came from if it is selected, else the first selected."""
        by_id = {p.id: p for p in projects}
        if selection.primary_project_id in selection.project_ids and selection.primary_project_id in by_id:
            return by_id[selection.primary_project_id]
        for project in projects:
            if project.id in selection.project_ids:
                return project
        return None

    # ------------------------------------------------------------------
    # A draft's step 1
    # ------------------------------------------------------------------
    def draft_selection(self, invoice: Invoice) -> StepOneSelection:
        """Step 1 of a draft as it was: its period, its projects, its layout and template.

        The projects are the invoice's own and those of the entries it bills; a draft made before
        step 1 existed takes its period from those entries (Last month when it has none).
        """
        rows = (
            db.session.query(TimeEntry.project_id, func.min(TimeEntry.start_time), func.max(TimeEntry.start_time))
            .join(InvoiceTimeLink, InvoiceTimeLink.time_entry_id == TimeEntry.id)
            .filter(InvoiceTimeLink.invoice_id == invoice.id, InvoiceTimeLink.released_at.is_(None))
            .group_by(TimeEntry.project_id)
            .all()
        )
        project_ids = sorted({invoice.project_id} | {pid for pid, _first, _last in rows if pid})
        client_entries = any(pid is None for pid, _first, _last in rows)
        if invoice.period_start or invoice.period_end:
            period = period_from_dates(invoice.period_start, invoice.period_end)
        elif rows:
            period = period_from_dates(
                min(first for _pid, first, _last in rows).date(), max(last for _pid, _first, last in rows).date()
            )
        else:
            period = resolve_period(PERIOD_LAST_MONTH)
        layout = normalize_layout(invoice.hours_layout)
        template = normalize_template(invoice.line_template)
        if layout is None:
            layout, template = self.time_links.resolve_layout(invoice.project)
        return StepOneSelection(
            client=invoice.client,
            project_ids=project_ids,
            period=period,
            layout=layout,
            template=template or default_line_template(layout),
            client_entries=client_entries,
            currency=invoice.currency_code,
            invoice=invoice,
            primary_project_id=invoice.project_id,
        )

    @staticmethod
    def hours_changed(before: StepOneSelection, after: StepOneSelection) -> bool:
        """Whether a draft's hours must be collected again: another period, projects, layout or template."""
        layout_before = normalize_layout(before.layout)
        layout_after = normalize_layout(after.layout) or layout_before
        template_before = normalize_template(before.template) or default_line_template(layout_before)
        template_after = normalize_template(after.template) or default_line_template(layout_after)
        return (
            (before.period.start, before.period.end) != (after.period.start, after.period.end)
            or sorted(set(before.project_ids)) != sorted(set(after.project_ids))
            or bool(before.client_entries) != bool(after.client_entries)
            or layout_before != layout_after
            or (layout_after != LAYOUT_NONE and template_before != template_after)
        )

    # ------------------------------------------------------------------
    # Writers
    # ------------------------------------------------------------------
    def add_hours(
        self, invoice: Invoice, selection: StepOneSelection, projects: Sequence[Project], created_by: Optional[int]
    ):
        """Collect the selection's hours onto a draft, as Generate from Time does.

        Prepaid hours are used first; entries they cover in full get a link without a line. The
        layout and template become the default of every selected project. Returns the lines (or
        None with "Don't add any hours"). The caller commits.
        """
        layout = normalize_layout(selection.layout)
        template = normalize_template(selection.template)
        primary = self.primary_project(selection, projects)
        if not selection.collects_hours:
            invoice.hours_layout = LAYOUT_NONE
            invoice.line_template = None
            return None

        entries = self.collect(selection)
        if invoice.period_start is None and invoice.period_end is None and entries:
            # All unbilled: the period is the one the entries span
            invoice.period_start = entries[0].start_time.date()
            invoice.period_end = entries[-1].start_time.date()
        allocator = PrepaidHoursAllocator(client=selection.client, invoice=invoice)
        processed = allocator.process(entries)
        lines = self.time_links.add_entries(
            invoice, processed, layout, template, created_by=created_by, project=primary
        )
        self.time_links.link_entries(
            invoice,
            None,
            [(p.entry, p.prepaid_hours) for p in processed if p.prepaid_hours > 0 and p.billable_hours <= 0],
            created_by=created_by,
        )
        for project in projects:
            if project.id in selection.project_ids and project is not primary:
                project.last_hours_layout = invoice.hours_layout
                project.last_line_template = invoice.line_template
        return lines

    def release_hours(self, invoice: Invoice) -> int:
        """Let go of a draft's hours before step 1 collects them again.

        Its prepaid hours go back to the plan, every link is removed and its hours lines are
        deleted; lines added by hand stay. Returns the number of entries let go. The caller commits.
        """
        self.time_links._require_draft(invoice)
        if invoice.client is not None and invoice.client.prepaid_plan_enabled:
            # Same reset Generate from Time does before it allocates again
            PrepaidHoursAllocator(client=invoice.client, invoice=invoice)._reset_invoice_allocations()
        entry_ids = self.time_links.unlink_invoice(invoice)
        for item in invoice.items.all():
            if item.kind == "time":
                db.session.delete(item)
        db.session.flush()
        return len(entry_ids)

    def recollect(
        self, invoice: Invoice, selection: StepOneSelection, projects: Sequence[Project], created_by: Optional[int]
    ):
        """Step 1 of a draft saved with another period, projects, layout or template: hours again."""
        before = sorted(invoice.items.all(), key=lambda i: (i.position or 0, i.id or 0))
        slot = next((index for index, item in enumerate(before) if item.kind == "time"), 0)
        self.release_hours(invoice)
        invoice.period_start = selection.period.start
        invoice.period_end = selection.period.end
        lines = self.add_hours(invoice, selection, projects, created_by)
        # The new hours lines take the place of the first old one; lines added by hand keep their order
        kept = [item for item in before if item.kind != "time"]
        new = list(lines.items) if lines is not None else []
        for position, item in enumerate(kept[:slot] + new + kept[slot:]):
            item.position = position
        invoice.calculate_totals()
        return lines
