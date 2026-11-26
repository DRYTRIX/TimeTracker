"""Expenses and project costs of an invoice: which ones it bills, and the lines that bill the costs.

An expense stays its own row on the invoice (``Expense.invoice_id``); the invoice prints it in its own
block. A project cost is billed by a line of kind ``cost`` (``ProjectCost.invoice_item_id``); one line
may bill several costs (by category, or all on one line). This service collects both for step 1 and
the draft page, and keeps lines and costs in step when costs are taken off, added or regrouped.
"""

from __future__ import annotations

from collections import OrderedDict
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from dateutil.relativedelta import relativedelta
from sqlalchemy import and_, or_
from sqlalchemy.orm import joinedload

from app import db
from app.models import Expense, Invoice, InvoiceItem, ProjectCost, RecurringProjectCost
from app.services.invoice_time_service import (
    LINE_KIND_COST,
    InvalidLineValueError,
    InvoiceTimeError,
    InvoiceTimeService,
)

COSTS_BY_COST = "cost"
COSTS_BY_CATEGORY = "category"
COSTS_ONE_LINE = "one_line"
COSTS_LAYOUTS = (COSTS_BY_COST, COSTS_BY_CATEGORY, COSTS_ONE_LINE)
COSTS_LAYOUT_LABELS = OrderedDict(
    [(COSTS_BY_COST, "By cost"), (COSTS_BY_CATEGORY, "By category"), (COSTS_ONE_LINE, "One line")]
)
ONE_LINE_DESCRIPTION = "Project costs"
NO_CATEGORY = "Other"
RECURRING_FREQUENCIES = ("daily", "weekly", "monthly", "yearly")

# Statuses shown next to an expense or a cost
STATUS_PENDING = "pending"
STATUS_NON_BILLABLE = "non_billable"
STATUS_RECURRING = "recurring"
STATUS_LOGGED = "logged"

MONEY = Decimal("0.01")


class InvoiceCostsError(InvoiceTimeError):
    """An expense or a cost cannot be changed on this invoice as asked."""

    code = "invalid_cost"


class ExpenseNotOnInvoiceError(InvoiceCostsError):
    """The expense is not on this invoice."""

    code = "expense_not_on_invoice"


class CostNotOnInvoiceError(InvoiceCostsError):
    """The project cost is not on this invoice."""

    code = "cost_not_on_invoice"


class InvalidCostsLayoutError(InvoiceCostsError):
    """Not one of the ways to show costs (by cost, by category, one line)."""

    code = "invalid_costs_layout"


class ProjectNotOnInvoiceError(InvoiceCostsError):
    """The project is not one the invoice bills."""

    code = "project_not_on_invoice"


class InvoiceHasNoPeriodError(InvoiceCostsError):
    """The invoice has no period (all unbilled time), so nothing can be logged on its last day."""

    code = "no_period"


class CostAlreadyLoggedError(InvoiceCostsError):
    """The Not logged yet row is not missing any more: the period has that cost (a second "+")."""

    code = "already_logged"


class AlreadyRecurringError(InvoiceCostsError):
    """The project already has an active recurring cost with this category and description."""

    code = "already_recurring"


class DateOutsidePeriodError(InvoiceCostsError):
    """The date is before (``side`` "before") or after (``side`` "after") the invoice's period."""

    code = "date_outside_period"

    def __init__(self, side: str):
        self.side = side
        super().__init__(f"date {side} the period")


def normalize_costs_layout(value) -> Optional[str]:
    value = (value or "").strip().lower() if isinstance(value, str) else None
    return value if value in COSTS_LAYOUTS else None


def expense_statuses(expense: Expense) -> List[str]:
    """What the invoice says about an expense: waiting for approval, was non-billable."""
    statuses = []
    if expense.status == "pending":
        statuses.append(STATUS_PENDING)
    if not expense.billable:
        statuses.append(STATUS_NON_BILLABLE)
    return statuses


def cost_statuses(cost: ProjectCost) -> List[str]:
    """What the invoice says about a cost: recurring (fixed) or logged, and was non-billable."""
    statuses = [STATUS_RECURRING if cost.recurring_cost_id else STATUS_LOGGED]
    if not cost.billable:
        statuses.append(STATUS_NON_BILLABLE)
    return statuses


def expense_amount(expense: Expense) -> Decimal:
    """What an expense adds to the invoice: its amount with tax, as ``Invoice.calculate_totals`` counts it."""
    return Decimal(str(expense.total_amount or 0)).quantize(MONEY)


def cost_amount(cost: ProjectCost) -> Decimal:
    return Decimal(str(cost.amount or 0)).quantize(MONEY)


def cost_description(cost: ProjectCost) -> str:
    """A line for one cost, as Generate from Time writes it: "<description> (<category>)"."""
    label = cost.category_name
    return f"{cost.description} ({label})" if label else (cost.description or "")


def category_key(cost: ProjectCost) -> Tuple:
    if cost.category_id is not None:
        return ("id", cost.category_id)
    return ("legacy", (cost.category or "").strip().lower())


class InvoiceCostsService:
    """Expenses and project costs on invoices."""

    def __init__(self):
        self.times = InvoiceTimeService()

    # ------------------------------------------------------------------
    # What step 1 and the draft may bill
    # ------------------------------------------------------------------
    @staticmethod
    def _own(model, invoice: Optional[Invoice]):
        if invoice is None or invoice.id is None:
            return None
        return model.invoice_id == invoice.id

    def expenses_query(
        self,
        client_id: Optional[int],
        project_ids: Sequence[int],
        start: Optional[date],
        end: Optional[date],
        *,
        client_entries: bool = False,
        invoice: Optional[Invoice] = None,
        keep_own: bool = False,
    ):
        """Expenses of these projects in the period that are on no invoice (or on this one), not rejected.

        With ``client_entries`` also the client's expenses without a project. With ``keep_own`` every
        expense this invoice already bills is included, whatever its date or project.
        """
        scope = []
        ids = [pid for pid in project_ids if pid]
        if ids:
            scope.append(Expense.project_id.in_(ids))
        if client_entries and client_id:
            scope.append(and_(Expense.project_id.is_(None), Expense.client_id == client_id))
        criteria = [or_(*scope) if scope else db.false(), Expense.status != "rejected"]
        if start is not None:
            criteria.append(Expense.expense_date >= start)
        if end is not None:
            criteria.append(Expense.expense_date <= end)
        own = self._own(Expense, invoice)
        criteria.append(or_(Expense.invoice_id.is_(None), own) if own is not None else Expense.invoice_id.is_(None))
        clause = and_(*criteria)
        if keep_own and own is not None:
            clause = or_(clause, own)
        return Expense.query.options(joinedload(Expense.user), joinedload(Expense.project)).filter(clause)

    def period_expenses(self, *args, **kwargs) -> List[Expense]:
        return self.expenses_query(*args, **kwargs).order_by(Expense.expense_date.asc(), Expense.id.asc()).all()

    def costs_query(
        self,
        project_ids: Sequence[int],
        start: Optional[date],
        end: Optional[date],
        *,
        invoice: Optional[Invoice] = None,
        keep_own: bool = False,
    ):
        """Project costs of these projects in the period that are on no invoice (or on this one)."""
        ids = [pid for pid in project_ids if pid]
        criteria = [ProjectCost.project_id.in_(ids) if ids else db.false()]
        if start is not None:
            criteria.append(ProjectCost.cost_date >= start)
        if end is not None:
            criteria.append(ProjectCost.cost_date <= end)
        # A cost this invoice bills counts only with its line: one billed by an old line not linked to it
        # is left alone, so it is never billed twice
        own = self._own(ProjectCost, invoice)
        own_linked = and_(own, ProjectCost.invoice_item_id.isnot(None)) if own is not None else None
        criteria.append(
            or_(ProjectCost.invoice_id.is_(None), own_linked)
            if own_linked is not None
            else ProjectCost.invoice_id.is_(None)
        )
        clause = and_(*criteria)
        if keep_own and own_linked is not None:
            clause = or_(clause, own_linked)
        return ProjectCost.query.options(joinedload(ProjectCost.expense_category)).filter(clause)

    def period_costs(self, *args, **kwargs) -> List[ProjectCost]:
        return self.costs_query(*args, **kwargs).order_by(ProjectCost.cost_date.asc(), ProjectCost.id.asc()).all()

    @staticmethod
    def choose(items: Iterable, checked: Optional[Iterable[int]], seen: Optional[Iterable[int]], default) -> List:
        """The items that stay ticked: those posted as ticked; an item the page did not show yet gets ``default``.

        ``checked`` None: nothing was posted, every item gets ``default``. ``default`` is a bool or a
        function of the item.
        """
        checked_ids = set(checked or ())
        seen_ids = set(seen or ())
        chosen = []
        for item in items:
            if checked is not None and (item.id in seen_ids or item.id in checked_ids):
                ticked = item.id in checked_ids
            else:
                ticked = default(item) if callable(default) else default
            if ticked:
                chosen.append(item)
        return chosen

    # ------------------------------------------------------------------
    # Lines that bill costs
    # ------------------------------------------------------------------
    @staticmethod
    def invoice_layout(invoice: Invoice) -> str:
        return normalize_costs_layout(invoice.costs_layout) or COSTS_BY_COST

    @staticmethod
    def group_costs(costs: Sequence[ProjectCost], layout: str) -> List[Tuple[str, List[ProjectCost]]]:
        """``[(description, costs)]`` of the lines ``costs`` become, oldest cost first."""
        ordered = sorted(costs, key=lambda c: (c.cost_date or date.min, c.id or 0))
        if not ordered:
            return []
        if layout == COSTS_ONE_LINE:
            return [(ONE_LINE_DESCRIPTION, ordered)]
        if layout == COSTS_BY_CATEGORY:
            groups: "OrderedDict[Tuple, List[ProjectCost]]" = OrderedDict()
            for cost in ordered:
                groups.setdefault(category_key(cost), []).append(cost)
            return [(group[0].category_name or NO_CATEGORY, group) for group in groups.values()]
        return [(cost_description(cost), [cost]) for cost in ordered]

    @staticmethod
    def describe(costs: Sequence[ProjectCost], layout: str) -> str:
        """Description of a line that bills ``costs`` in ``layout``."""
        if layout == COSTS_ONE_LINE:
            return ONE_LINE_DESCRIPTION
        if layout == COSTS_BY_CATEGORY:
            return costs[0].category_name or NO_CATEGORY
        if len(costs) == 1:
            return cost_description(costs[0])
        return ONE_LINE_DESCRIPTION

    def add_cost_lines(
        self, invoice: Invoice, costs: Sequence[ProjectCost], layout: Optional[str] = None, position: int = None
    ) -> List[InvoiceItem]:
        """Bill ``costs`` on new lines of a draft (after its other lines, or from ``position``). The caller commits."""
        self.times._require_draft(invoice)
        layout = normalize_costs_layout(layout) or self.invoice_layout(invoice)
        if invoice.id is None:
            db.session.flush()
        next_position = self.times._next_position(invoice) if position is None else position
        items = []
        for description, group in self.group_costs(costs, layout):
            amount = sum((cost_amount(c) for c in group), Decimal("0"))
            item = InvoiceItem(
                invoice_id=invoice.id,
                description=description[:500],
                quantity=Decimal("1"),
                unit_price=amount,
                position=next_position,
            )
            item.kind = LINE_KIND_COST
            db.session.add(item)
            items.append((item, group))
            next_position += 1
        db.session.flush()
        for item, group in items:
            for cost in group:
                cost.mark_as_invoiced(invoice.id)
                cost.invoice_item_id = item.id
        if invoice.costs_layout is None:
            invoice.costs_layout = layout
        db.session.flush()
        return [item for item, _group in items]

    @staticmethod
    def cost_lines(invoice: Invoice) -> List[InvoiceItem]:
        if invoice is None or invoice.id is None:
            return []
        return sorted(
            (item for item in invoice.items.all() if item.kind == LINE_KIND_COST),
            key=lambda item: (item.position or 0, item.id or 0),
        )

    @staticmethod
    def costs_by_line(invoice: Invoice) -> Dict[int, List[ProjectCost]]:
        """``{line id: [costs]}`` of a draft's cost lines, oldest cost first."""
        if invoice is None or invoice.id is None:
            return {}
        by_line: Dict[int, List[ProjectCost]] = {}
        costs = (
            ProjectCost.query.options(joinedload(ProjectCost.expense_category))
            .filter(ProjectCost.invoice_id == invoice.id, ProjectCost.invoice_item_id.isnot(None))
            .order_by(ProjectCost.cost_date.asc(), ProjectCost.id.asc())
            .all()
        )
        for cost in costs:
            by_line.setdefault(cost.invoice_item_id, []).append(cost)
        return by_line

    @staticmethod
    def invoice_costs(invoice: Invoice) -> List[ProjectCost]:
        if invoice is None or invoice.id is None:
            return []
        return ProjectCost.query.filter(ProjectCost.invoice_id == invoice.id).all()

    def refresh_cost_line(self, invoice: Invoice, item: InvoiceItem, removed: Decimal = Decimal("0")) -> str:
        """Bring a cost line in step with its costs after some were taken off. Returns ``updated`` or ``deleted``.

        A line left without costs is deleted. Otherwise its price is the sum of its costs; on a line
        whose price or quantity was changed by hand the amount goes down by exactly ``removed`` instead
        (price minus ``removed`` / quantity, never below 0). A description not changed by hand is written
        again. Totals are recalculated; the caller commits.
        """
        db.session.flush()
        costs = (
            ProjectCost.query.filter(ProjectCost.invoice_item_id == item.id)
            .order_by(ProjectCost.cost_date.asc(), ProjectCost.id.asc())
            .all()
        )
        if not costs:
            db.session.delete(item)
            db.session.flush()
            invoice.calculate_totals()
            return "deleted"
        if item.price_edited or item.quantity_edited:
            quantity = Decimal(str(item.quantity or 0))
            step = Decimal(str(removed or 0)) / quantity if quantity > 0 else Decimal("0")
            price = Decimal(str(item.unit_price or 0)) - step
            item.unit_price = max(price, Decimal("0")).quantize(MONEY)
        else:
            item.quantity = Decimal("1")
            item.unit_price = sum((cost_amount(c) for c in costs), Decimal("0"))
        if not item.description_edited:
            item.description = self.describe(costs, self.invoice_layout(invoice))[:500]
        item.total_amount = item.line_net
        db.session.flush()
        invoice.calculate_totals()
        return "updated"

    def release_costs(self, invoice: Invoice, costs: Iterable[ProjectCost]) -> int:
        """Take costs off a draft: they are unbilled again and their lines follow. The caller commits."""
        self.times._require_draft(invoice)
        affected: Dict[int, Decimal] = {}
        count = 0
        for cost in costs:
            if cost.invoice_id != invoice.id:
                continue
            if cost.invoice_item_id:
                affected[cost.invoice_item_id] = affected.get(cost.invoice_item_id, Decimal("0")) + cost_amount(cost)
            cost.unmark_as_invoiced()
            count += 1
        db.session.flush()
        for item_id, removed in affected.items():
            item = db.session.get(InvoiceItem, item_id)
            if item is not None and item.invoice_id == invoice.id:
                self.refresh_cost_line(invoice, item, removed)
        invoice.calculate_totals()
        return count

    def remove_cost(self, invoice: Invoice, cost: ProjectCost) -> None:
        if cost.invoice_id != invoice.id:
            raise CostNotOnInvoiceError()
        self.release_costs(invoice, [cost])

    def release_line_costs(self, invoice: Invoice, item: InvoiceItem) -> int:
        """The line is being deleted: its costs are unbilled again. The caller deletes the line."""
        costs = ProjectCost.query.filter(ProjectCost.invoice_item_id == item.id).all()
        for cost in costs:
            cost.unmark_as_invoiced()
        db.session.flush()
        return len(costs)

    def regroup_costs(self, invoice: Invoice, layout: str, keep_edited: bool = True) -> List[InvoiceItem]:
        """Build a draft's cost lines again in another layout, from the same costs. The caller commits.

        With ``keep_edited`` a line whose description or price was changed by hand stays, with its
        costs. The new lines take the place of the first rebuilt one.
        """
        self.times._require_draft(invoice)
        layout = normalize_costs_layout(layout)
        if layout is None:
            raise InvalidCostsLayoutError()
        lines = self.cost_lines(invoice)
        by_line = self.costs_by_line(invoice)
        rebuilt = [i for i in lines if not (keep_edited and self.line_edited(i))]
        position = min((i.position or 0) for i in rebuilt) if rebuilt else None
        costs = [cost for item in rebuilt for cost in by_line.get(item.id, [])]
        for cost in costs:
            cost.invoice_item_id = None
        for item in rebuilt:
            db.session.delete(item)
        db.session.flush()
        new_items = []
        if costs:
            new_items = self.add_cost_lines(invoice, costs, layout, position=position)
            self._shift_after(invoice, new_items, position)
        invoice.costs_layout = layout
        invoice.calculate_totals()
        return new_items

    def _shift_after(self, invoice: Invoice, new_items: List[InvoiceItem], position: Optional[int]) -> None:
        """Lines after the new ones move down so the order stays as it was."""
        if position is None or not new_items:
            return
        new_ids = {item.id for item in new_items}
        others = [
            item
            for item in self.times._ordered_items(invoice)
            if item.id not in new_ids and (item.position or 0) >= position
        ]
        next_position = position + len(new_items)
        for item in others:
            item.position = next_position
            next_position += 1
        db.session.flush()

    @staticmethod
    def line_edited(item: InvoiceItem) -> bool:
        """Whether a cost line's description, quantity or price was changed by hand."""
        return bool(item.price_edited or item.quantity_edited or item.description_edited)

    def edited_cost_lines(self, invoice: Invoice) -> List[InvoiceItem]:
        return [i for i in self.cost_lines(invoice) if self.line_edited(i)]

    # ------------------------------------------------------------------
    # Step 1: bill the ticked expenses and costs
    # ------------------------------------------------------------------
    def add_to_draft(
        self, invoice: Invoice, expenses: Iterable[Expense], costs: Iterable[ProjectCost], layout: Optional[str]
    ) -> Dict[str, int]:
        """Bill these expenses and costs on a new draft. The caller commits."""
        expenses = list(expenses)
        costs = list(costs)
        for expense in expenses:
            expense.mark_as_invoiced(invoice.id)
        layout = normalize_costs_layout(layout) or COSTS_BY_COST
        invoice.costs_layout = layout
        lines = self.add_cost_lines(invoice, costs, layout) if costs else []
        invoice.calculate_totals()
        return {"expenses": len(expenses), "costs": len(costs), "lines": len(lines)}

    def sync_draft(
        self,
        invoice: Invoice,
        expenses: Iterable[Expense],
        costs: Iterable[ProjectCost],
        layout: Optional[str],
    ) -> Dict[str, int]:
        """Step 1 of a draft saved: it bills exactly these expenses and costs. The caller commits.

        Expenses no longer ticked are unbilled, new ones are added. Cost lines are left alone when the
        costs and the layout did not change; otherwise they are built again (edits to them are lost).
        """
        self.times._require_draft(invoice)
        wanted_expenses = {e.id: e for e in expenses}
        released = added = 0
        for expense in invoice.expenses.all():
            if expense.id not in wanted_expenses:
                expense.unmark_as_invoiced()
                released += 1
        for expense in wanted_expenses.values():
            if expense.invoice_id != invoice.id:
                expense.mark_as_invoiced(invoice.id)
                added += 1

        layout = normalize_costs_layout(layout) or self.invoice_layout(invoice)
        wanted_costs = {c.id: c for c in costs}
        linked = {c.id for c in self.invoice_costs(invoice) if c.invoice_item_id}
        costs_changed = set(wanted_costs) != linked or layout != self.invoice_layout(invoice)
        if costs_changed:
            lines = self.cost_lines(invoice)
            position = min((i.position or 0) for i in lines) if lines else None
            for cost in self.invoice_costs(invoice):
                if cost.invoice_item_id or cost.id in wanted_costs:
                    cost.unmark_as_invoiced()
            for item in lines:
                db.session.delete(item)
            db.session.flush()
            new_items = self.add_cost_lines(invoice, list(wanted_costs.values()), layout, position=position)
            self._shift_after(invoice, new_items, position)
        invoice.costs_layout = layout
        invoice.calculate_totals()
        return {"expenses_released": released, "expenses_added": added, "costs_rebuilt": int(costs_changed)}

    # ------------------------------------------------------------------
    # Draft page
    # ------------------------------------------------------------------
    def remove_expense(self, invoice: Invoice, expense: Expense) -> None:
        self.times._require_draft(invoice)
        if expense.invoice_id != invoice.id:
            raise ExpenseNotOnInvoiceError()
        expense.unmark_as_invoiced()
        db.session.flush()
        invoice.calculate_totals()

    def log_expense(
        self,
        invoice: Invoice,
        *,
        user_id: int,
        project_id: Optional[int],
        title: str,
        category: str,
        amount,
        expense_date: date,
        notes: Optional[str] = None,
        reimbursable: bool = False,
        receipt_path: Optional[str] = None,
        approver_id: Optional[int] = None,
    ) -> Expense:
        """A new expense billed on the draft at once, in the invoice's currency. The caller commits.

        Approved when ``approver_id`` is given (the person logging it may approve), else pending.
        """
        self.times._require_draft(invoice)
        title = (title or "").strip()
        if not title:
            raise InvalidLineValueError("title", "required")
        if not (category or "").strip():
            raise InvalidLineValueError("category", "required")
        amount = self.parse_positive_amount(amount)
        self._require_in_period(invoice, expense_date)
        expense = Expense(
            user_id=user_id,
            title=title[:200],
            category=category.strip()[:50],
            amount=amount,
            expense_date=expense_date,
            project_id=project_id,
            client_id=invoice.client_id,
            currency_code=invoice.currency_code,
            notes=notes,
            billable=True,
            reimbursable=bool(reimbursable),
            receipt_path=receipt_path,
        )
        if approver_id:
            expense.approve(approver_id)
        db.session.add(expense)
        db.session.flush()
        expense.mark_as_invoiced(invoice.id)
        invoice.calculate_totals()
        return expense

    def log_cost(
        self,
        invoice: Invoice,
        *,
        user_id: int,
        project_id: int,
        description: str,
        expense_category,
        amount,
        cost_date: date,
        notes: Optional[str] = None,
        receipt_path: Optional[str] = None,
        repeat_monthly: bool = False,
        ask_amount: bool = False,
        recurring_cost_id: Optional[int] = None,
        legacy_category: Optional[str] = None,
    ) -> ProjectCost:
        """A new project cost billed on the draft at once, in the invoice's currency. The caller commits.

        With ``repeat_monthly`` a monthly recurring cost with the same category and project is created
        too, and this cost is its first one: with the same amount every month, or, with ``ask_amount``,
        asking for the amount in each draft of its period (it next runs a month later).
        ``recurring_cost_id``: the cost is one of an existing recurring cost (Not logged yet).
        ``legacy_category``: the category when the cost has only the old category text.
        """
        self.times._require_draft(invoice)
        description = (description or "").strip()
        if not description:
            raise InvalidLineValueError("description", "required")
        if expense_category is None and not (legacy_category or "").strip():
            raise InvalidLineValueError("category", "required")
        amount = self.parse_positive_amount(amount)
        self._require_in_period(invoice, cost_date)
        cost = ProjectCost(
            project_id=project_id,
            user_id=user_id,
            description=description[:500],
            category=None,
            amount=amount,
            cost_date=cost_date,
            billable=True,
            notes=notes,
            currency_code=invoice.currency_code,
            receipt_path=receipt_path,
        )
        if expense_category is not None:
            cost.set_category(expense_category)
        else:
            cost.set_category_from_input(category=legacy_category)
        if repeat_monthly:
            recurring = self.make_recurring(
                project_id=project_id,
                user_id=user_id,
                description=description,
                category=cost.category,
                category_id=cost.category_id,
                amount=amount,
                next_run_date=cost_date + relativedelta(months=1),
                currency_code=invoice.currency_code,
                ask_amount=ask_amount,
                # This cost is its first one
                start_date=cost_date,
            )
            recurring.last_generated_at = datetime.utcnow()
            cost.recurring_cost_id = recurring.id
        elif recurring_cost_id:
            recurring = db.session.get(RecurringProjectCost, recurring_cost_id)
            if recurring is not None and recurring.project_id == project_id:
                cost.recurring_cost_id = recurring.id
                if recurring.ask_amount:
                    # The last amount asked for is the hint next time; it next asks after this period
                    recurring.amount = amount
                    self.advance_past(recurring, invoice.period_end or cost_date)
        db.session.add(cost)
        db.session.flush()
        self.add_cost_lines(invoice, [cost])
        invoice.calculate_totals()
        return cost

    def parse_positive_amount(self, value) -> Decimal:
        """An amount typed in a draft form: a number above 0, to the cent."""
        amount = self.times.parse_amount(value, "amount")
        if amount <= 0:
            raise InvalidLineValueError("amount", "not_positive")
        return amount.quantize(MONEY)

    @staticmethod
    def make_recurring(
        *,
        project_id: int,
        user_id: int,
        description: str,
        category: Optional[str],
        category_id: Optional[int],
        amount,
        next_run_date: date,
        currency_code: str,
        ask_amount: bool = False,
        start_date: Optional[date] = None,
    ) -> RecurringProjectCost:
        """A monthly recurring cost in this category (``category_id``, and the old category text). The caller commits."""
        recurring = RecurringProjectCost(
            project_id=project_id,
            user_id=user_id,
            description=description.strip()[:500],
            category=(category or "other")[:50],
            amount=Decimal(str(amount or 0)).quantize(MONEY),
            frequency="monthly",
            next_run_date=next_run_date,
            currency_code=currency_code,
            billable=True,
            ask_amount=ask_amount,
        )
        recurring.category_id = category_id
        recurring.start_date = start_date or next_run_date
        db.session.add(recurring)
        db.session.flush()
        return recurring

    # ------------------------------------------------------------------
    # Not logged yet: costs of earlier invoices that this period does not have
    # ------------------------------------------------------------------
    @staticmethod
    def cost_keys(cost: ProjectCost) -> List[Tuple]:
        """What makes two costs "the same cost": their recurring cost, else category and description."""
        keys = [("d", cost.project_id, category_key(cost), (cost.description or "").strip().lower())]
        if cost.recurring_cost_id:
            keys.insert(0, ("r", cost.recurring_cost_id))
        return keys

    def not_logged(self, invoice: Invoice, project_ids: Sequence[int]) -> List[Dict]:
        """Costs the period may be missing, oldest invoice's order kept: each a dict with ``key``,
        ``description``, ``category_id``, ``category`` (old text), ``category_name``, ``project_id``,
        ``last_amount``, ``last_date``, ``currency``, ``recurring_cost_id``, ``ask_amount``.

        A cost billed on one of the last 3 invoices (not cancelled) of a project before this period,
        that has no cost of the same kind in the period nor on this invoice; and every recurring cost
        that asks for its amount and falls in the period without a cost in it.
        """
        from sqlalchemy import func

        if invoice is None or invoice.period_start is None or invoice.period_end is None:
            return []
        start, end = invoice.period_start, invoice.period_end
        ids = sorted({pid for pid in project_ids if pid})
        if not ids:
            return []

        present: Set[Tuple] = set()
        in_period = ProjectCost.query.filter(
            ProjectCost.project_id.in_(ids),
            or_(
                and_(ProjectCost.cost_date >= start, ProjectCost.cost_date <= end), ProjectCost.invoice_id == invoice.id
            ),
        ).all()
        for cost in in_period:
            present.update(self.cost_keys(cost))

        rows: "OrderedDict[Tuple, Dict]" = OrderedDict()

        def add(key, cost=None, recurring=None):
            if key in rows:
                return
            source = cost if cost is not None else recurring
            rows[key] = {
                "key": f"r{key[1]}" if key[0] == "r" else f"c{len(rows) + 1}",
                "description": source.description,
                "category_id": source.category_id,
                "category": source.category,
                "category_name": source.category_name,
                "project_id": source.project_id,
                "last_amount": Decimal(str((cost or recurring).amount or 0)).quantize(MONEY),
                "last_date": cost.cost_date if cost is not None else None,
                "currency": source.currency_code,
                "recurring_cost_id": recurring.id if recurring is not None else None,
                "ask_amount": bool(recurring.ask_amount) if recurring is not None else False,
            }

        day = func.coalesce(Invoice.period_end, Invoice.issue_date)
        for pid in ids:
            earlier = (
                db.session.query(Invoice.id, day.label("day"))
                .join(ProjectCost, ProjectCost.invoice_id == Invoice.id)
                .filter(
                    ProjectCost.project_id == pid,
                    Invoice.status != "cancelled",
                    Invoice.id != invoice.id,
                    day < start,
                )
                .distinct()
                .order_by(day.desc(), Invoice.id.desc())
                .limit(3)
                .all()
            )
            invoice_ids = [row[0] for row in earlier]
            if not invoice_ids:
                continue
            costs = (
                ProjectCost.query.options(joinedload(ProjectCost.expense_category))
                .filter(ProjectCost.invoice_id.in_(invoice_ids), ProjectCost.project_id == pid)
                .order_by(ProjectCost.cost_date.desc(), ProjectCost.id.desc())
                .all()
            )
            for cost in costs:
                keys = self.cost_keys(cost)
                if present.intersection(keys):
                    continue
                recurring = (
                    db.session.get(RecurringProjectCost, cost.recurring_cost_id) if cost.recurring_cost_id else None
                )
                # A recurring cost that was switched off or ended before the period: the service is
                # over, its old costs are not missing
                if recurring is not None and self.recurring_over(recurring, start):
                    continue
                # A recurring cost is missing only in a period it falls in by its frequency (a yearly
                # one is not asked for every month)
                if recurring is not None and self.due_in_period(recurring, start, end) is None:
                    continue
                add(keys[0], cost=cost, recurring=recurring)
                if recurring is not None:
                    rows[keys[0]]["last_amount"] = cost_amount(cost)

        # Which of them fall in the period is decided by their frequency (``due_in_period``), from their start
        asking = RecurringProjectCost.query.filter(
            RecurringProjectCost.project_id.in_(ids),
            RecurringProjectCost.is_active == True,  # noqa: E712
            RecurringProjectCost.ask_amount == True,  # noqa: E712
            or_(RecurringProjectCost.end_date.is_(None), RecurringProjectCost.end_date >= start),
        ).all()
        for recurring in asking:
            key = ("r", recurring.id)
            if key in present or self.due_in_period(recurring, start, end) is None:
                continue
            last = (
                ProjectCost.query.filter(ProjectCost.recurring_cost_id == recurring.id)
                .order_by(ProjectCost.cost_date.desc(), ProjectCost.id.desc())
                .first()
            )
            add(key, cost=last, recurring=recurring)
            if last is None:
                rows[key]["last_amount"] = Decimal(str(recurring.amount or 0)).quantize(MONEY)
        return list(rows.values())

    @staticmethod
    def due_in_period(recurring: RecurringProjectCost, start: date, end: date) -> Optional[date]:
        """The day in the period a recurring cost is due by its frequency, or None.

        A recurring cost that asks for its amount counts from its start (``start_date``): its days are
        the start and every step of the frequency after it, whatever was logged since, so a draft of an
        earlier month made later still asks. A fixed one counts from ``next_run_date``, which its
        generator moves on. Nothing is due after ``end_date``.
        """
        day = (recurring.start_date or recurring.next_run_date) if recurring.ask_amount else recurring.next_run_date
        if day is None or recurring.frequency not in RECURRING_FREQUENCIES:
            return None
        for _step in range(10000):
            if day > end or (recurring.end_date is not None and day > recurring.end_date):
                return None
            if day >= start:
                return day
            following = recurring.calculate_next_run_date(day)
            if following is None or following <= day:
                return None
            day = following
        return None

    @staticmethod
    def recurring_over(recurring: RecurringProjectCost, start: date) -> bool:
        """Whether a recurring cost no longer runs for a period from ``start``: switched off, or ended before."""
        return not recurring.is_active or (recurring.end_date is not None and recurring.end_date < start)

    @staticmethod
    def advance_past(recurring: RecurringProjectCost, end: date) -> None:
        """A recurring cost whose amount was logged for a period next asks after that period.

        ``next_run_date`` only moves forward: logging an earlier month never moves it back.
        """
        day = recurring.next_run_date
        if recurring.frequency not in RECURRING_FREQUENCIES:
            return
        for _step in range(10000):
            if day is None or day > end:
                break
            following = recurring.calculate_next_run_date(day)
            if following is None or following <= day:
                break
            day = following
        recurring.next_run_date = day
        recurring.last_generated_at = datetime.utcnow()

    @staticmethod
    def same_kind(row: Dict, *, recurring_cost_id, category_id, legacy_category, description) -> bool:
        """Whether a Not logged yet row is the one a form names: its recurring cost, else category and description."""
        if recurring_cost_id:
            return row.get("recurring_cost_id") == recurring_cost_id
        if row.get("recurring_cost_id"):
            return False
        if (description or "").strip().lower() != (row.get("description") or "").strip().lower():
            return False
        if category_id or row.get("category_id"):
            return row.get("category_id") == category_id
        return (legacy_category or "").strip().lower() == (row.get("category") or "").strip().lower()

    @staticmethod
    def active_recurring_like(
        project_id: int, category_id, legacy_category, description
    ) -> Optional[RecurringProjectCost]:
        """An active recurring cost of the project with this category and description, if there is one."""
        wanted = (description or "").strip().lower()
        candidates = RecurringProjectCost.query.filter(
            RecurringProjectCost.project_id == project_id,
            RecurringProjectCost.is_active == True,  # noqa: E712
        ).all()
        for recurring in candidates:
            if (recurring.description or "").strip().lower() != wanted:
                continue
            if category_id or recurring.category_id:
                if recurring.category_id == category_id:
                    return recurring
            elif (recurring.category or "").strip().lower() == (legacy_category or "").strip().lower():
                return recurring
        return None

    # ------------------------------------------------------------------
    # Issued invoices lock what they bill
    # ------------------------------------------------------------------
    @staticmethod
    def issued_invoice(record) -> Optional[Invoice]:
        """The invoice that bills this expense or cost when it was issued (not a draft, not cancelled)."""
        if record is None or not getattr(record, "invoice_id", None):
            return None
        invoice = db.session.get(Invoice, record.invoice_id)
        if invoice is None or invoice.status in ("draft", "cancelled"):
            return None
        return invoice

    @staticmethod
    def lock_message(record, invoice: Invoice) -> str:
        """The refusal in English, for API answers."""
        what = "expense" if isinstance(record, Expense) else "cost"
        return (
            f"This {what} is on invoice {invoice.invoice_number}, which was issued: its amount, currency, date, "
            "project and billable flag cannot change, and it cannot be deleted or rejected. Cancel the invoice first."
        )

    def edit_lock(self, record, **changes) -> Optional[Invoice]:
        """The issued invoice that refuses this change to what it bills, or None.

        ``changes``: the new values of ``amount``, ``tax_amount``, ``date``, ``project_id``, ``billable``,
        ``currency_code`` (only those given are compared); ``delete=True`` for a deletion or a rejection.
        """
        invoice = self.issued_invoice(record)
        if invoice is None:
            return None
        if changes.pop("delete", False):
            return invoice
        current = {
            "amount": record.amount,
            "tax_amount": getattr(record, "tax_amount", None),
            "date": record.expense_date if isinstance(record, Expense) else record.cost_date,
            "project_id": record.project_id,
            "billable": record.billable,
            "currency_code": record.currency_code,
        }
        for name, value in changes.items():
            before = current.get(name)
            if name in ("amount", "tax_amount"):
                same = Decimal(str(before or 0)).quantize(MONEY) == Decimal(str(value or 0)).quantize(MONEY)
            elif name == "billable":
                same = bool(before) == bool(value)
            elif name == "currency_code":
                same = (before or "").strip().upper() == (value or "").strip().upper()
            else:
                same = before == value
            if not same:
                return invoice
        return None

    @staticmethod
    def _require_in_period(invoice: Invoice, day: Optional[date]) -> None:
        if day is None:
            raise InvalidLineValueError("date", "required")
        if invoice.period_start and day < invoice.period_start:
            raise DateOutsidePeriodError("before")
        if invoice.period_end and day > invoice.period_end:
            raise DateOutsidePeriodError("after")

    # ------------------------------------------------------------------
    # Lines replaced by the edit form or the API
    # ------------------------------------------------------------------
    @staticmethod
    def snapshot_cost_lines(invoice: Invoice) -> Dict[int, Dict]:
        """``{line id: {"costs": [cost ids], ...line as it was}}`` before a form or the API replaces the lines."""
        snapshot: Dict[int, Dict] = {}
        if invoice is None or invoice.id is None:
            return snapshot
        rows = (
            db.session.query(ProjectCost.id, ProjectCost.invoice_item_id)
            .filter(ProjectCost.invoice_id == invoice.id, ProjectCost.invoice_item_id.isnot(None))
            .all()
        )
        items = {item.id: item for item in invoice.items.all()}
        for cost_id, item_id in rows:
            item = items.get(item_id)
            if item is None:
                continue
            state = snapshot.setdefault(
                item_id,
                {
                    "costs": [],
                    "description": item.description,
                    "quantity": Decimal(str(item.quantity or 0)).quantize(MONEY),
                    "unit_price": Decimal(str(item.unit_price or 0)).quantize(MONEY),
                    "description_edited": bool(item.description_edited),
                    "quantity_edited": bool(item.quantity_edited),
                    "price_edited": bool(item.price_edited),
                },
            )
            state["costs"].append(cost_id)
        return snapshot

    def carry_cost_lines(
        self, invoice: Invoice, snapshot: Dict[int, Dict], new_items: Sequence[InvoiceItem], row_ids: Sequence
    ) -> int:
        """After the lines were replaced: a new line sent with the id of a cost line bills its costs and
        remembers what was changed by hand; the costs of a cost line not sent again are unbilled.
        Returns the number of costs unbilled. Call after the new lines are added.
        """
        if not snapshot:
            return 0
        db.session.flush()
        normalize = self.times.normalize_description
        kept: Set[int] = set()
        for item, row_id in zip(new_items, row_ids):
            try:
                old_id = int(row_id) if row_id not in (None, "") else None
            except (TypeError, ValueError):
                old_id = None
            if old_id not in snapshot or old_id in kept or item.time_entry_ids:
                continue
            kept.add(old_id)
            previous = snapshot[old_id]
            item.kind = LINE_KIND_COST
            item.description_edited = previous["description_edited"] or normalize(item.description) != normalize(
                previous["description"]
            )
            quantity = Decimal(str(item.quantity or 0)).quantize(MONEY)
            item.quantity_edited = previous["quantity_edited"] or quantity != previous["quantity"]
            price = Decimal(str(item.unit_price or 0)).quantize(MONEY)
            item.price_edited = previous["price_edited"] or price != previous["unit_price"]
            for cost in ProjectCost.query.filter(ProjectCost.id.in_(previous["costs"])).all():
                cost.invoice_item_id = item.id
        released = 0
        for old_id, previous in snapshot.items():
            if old_id in kept:
                continue
            for cost in ProjectCost.query.filter(ProjectCost.id.in_(previous["costs"])).all():
                cost.unmark_as_invoiced()
                released += 1
        db.session.flush()
        return released

    # ------------------------------------------------------------------
    # Copies (Cancel and reissue)
    # ------------------------------------------------------------------
    @staticmethod
    def move_costs(costs: Iterable[ProjectCost], draft: Invoice, new_items: Dict[int, InvoiceItem]) -> None:
        """Costs that move to a reissued draft point at the copy of their line."""
        for cost in costs:
            old_item = cost.invoice_item_id
            cost.mark_as_invoiced(draft.id)
            copy = new_items.get(old_item) if old_item else None
            cost.invoice_item_id = copy.id if copy is not None else None
            if copy is not None:
                copy.kind = LINE_KIND_COST


__all__ = [
    "COSTS_BY_CATEGORY",
    "COSTS_BY_COST",
    "COSTS_LAYOUTS",
    "COSTS_LAYOUT_LABELS",
    "COSTS_ONE_LINE",
    "AlreadyRecurringError",
    "CostAlreadyLoggedError",
    "CostNotOnInvoiceError",
    "DateOutsidePeriodError",
    "ExpenseNotOnInvoiceError",
    "InvalidCostsLayoutError",
    "InvoiceHasNoPeriodError",
    "ProjectNotOnInvoiceError",
    "InvoiceCostsError",
    "InvoiceCostsService",
    "LINE_KIND_COST",
    "cost_amount",
    "cost_description",
    "cost_statuses",
    "expense_amount",
    "expense_statuses",
    "normalize_costs_layout",
]
