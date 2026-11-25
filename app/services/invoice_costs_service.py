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
from app.services.invoice_time_service import LINE_KIND_COST, InvoiceTimeError, InvoiceTimeService

COSTS_BY_COST = "cost"
COSTS_BY_CATEGORY = "category"
COSTS_ONE_LINE = "one_line"
COSTS_LAYOUTS = (COSTS_BY_COST, COSTS_BY_CATEGORY, COSTS_ONE_LINE)
COSTS_LAYOUT_LABELS = OrderedDict(
    [(COSTS_BY_COST, "By cost"), (COSTS_BY_CATEGORY, "By category"), (COSTS_ONE_LINE, "One line")]
)
ONE_LINE_DESCRIPTION = "Project costs"
NO_CATEGORY = "Other"

# Statuses shown next to an expense or a cost
STATUS_PENDING = "pending"
STATUS_NON_BILLABLE = "non_billable"
STATUS_RECURRING = "recurring"
STATUS_LOGGED = "logged"

MONEY = Decimal("0.01")


class InvoiceCostsError(InvoiceTimeError):
    """An expense or a cost cannot be changed on this invoice as asked."""

    code = "invalid_cost"


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
            raise InvoiceCostsError("This cost is not on the invoice")
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
            raise InvoiceCostsError("Choose how to show the costs")
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
            raise InvoiceCostsError("This expense is not on the invoice")
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
            raise InvoiceCostsError("Description is required")
        if not (category or "").strip():
            raise InvoiceCostsError("Category is required")
        amount = self.times.parse_amount(amount, "Amount", minimum=Decimal("0.01")).quantize(MONEY)
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
    ) -> ProjectCost:
        """A new project cost billed on the draft at once, in the invoice's currency. The caller commits.

        With ``repeat_monthly`` a monthly recurring cost with the same amount, category and project is
        created too; this cost is its first one, and it next runs a month later.
        """
        self.times._require_draft(invoice)
        description = (description or "").strip()
        if not description:
            raise InvoiceCostsError("Description is required")
        if expense_category is None:
            raise InvoiceCostsError("Category is required")
        amount = self.times.parse_amount(amount, "Amount", minimum=Decimal("0.01")).quantize(MONEY)
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
        cost.set_category(expense_category)
        if repeat_monthly:
            recurring = RecurringProjectCost(
                project_id=project_id,
                user_id=user_id,
                description=description[:500],
                category=expense_category.legacy_key,
                amount=amount,
                frequency="monthly",
                next_run_date=cost_date + relativedelta(months=1),
                currency_code=invoice.currency_code,
                billable=True,
            )
            recurring.set_category(expense_category)
            recurring.last_generated_at = datetime.utcnow()
            db.session.add(recurring)
            db.session.flush()
            cost.recurring_cost_id = recurring.id
        db.session.add(cost)
        db.session.flush()
        self.add_cost_lines(invoice, [cost])
        invoice.calculate_totals()
        return cost

    @staticmethod
    def _require_in_period(invoice: Invoice, day: Optional[date]) -> None:
        if day is None:
            raise InvoiceCostsError("Date is required")
        if invoice.period_start and day < invoice.period_start:
            raise InvoiceCostsError("The date is before the invoice's period")
        if invoice.period_end and day > invoice.period_end:
            raise InvoiceCostsError("The date is after the invoice's period")

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
