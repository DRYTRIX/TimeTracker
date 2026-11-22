"""Build InvoiceItem rows from billable time entries (grouped or per-entry)."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Dict, Iterable, List, Optional, Tuple, Union

from app.models import InvoiceItem, TimeEntry
from app.utils.prepaid_hours import ProcessedTimeEntry

QUANTITY_STEP = Decimal("0.01")


@dataclass
class BillableTimeEntry:
    entry: TimeEntry
    billable_hours: Decimal


def _hours_from_entry(entry: TimeEntry) -> Decimal:
    if not entry.duration_seconds:
        return Decimal("0")
    return Decimal(str(entry.duration_seconds)) / Decimal("3600")


def round_quantity(hours: Decimal) -> Decimal:
    """Round billable hours to the invoice quantity precision (2 places, half up)."""
    return Decimal(str(hours)).quantize(QUANTITY_STEP, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class EntryRate:
    """Hourly rate resolved for one time entry; ``found`` is False when no rate is configured."""

    rate: Decimal
    found: bool


def resolve_entry_rate(entry: TimeEntry) -> EntryRate:
    """Hourly rate for a time entry: person and date first, then project, then client.

    Uses ``RateOverride.resolve_rate_with_source`` with the entry's project, user and
    start date. Returns ``EntryRate(Decimal("0"), found=False)`` when nothing in the
    chain has a rate, so callers can bill at 0 and warn.
    """
    from app.models import RateOverride

    project = getattr(entry, "project", None)
    on_date = entry.start_time.date() if getattr(entry, "start_time", None) else None
    rate, source = RateOverride.resolve_rate_with_source(project, user_id=entry.user_id, on_date=on_date)
    return EntryRate(rate=Decimal(str(rate)), found=source is not None)


@dataclass
class MissingRate:
    """Billable hours added at 0 because neither person, project nor client has a rate."""

    project_name: Optional[str]
    user_name: Optional[str]
    hours: Decimal = Decimal("0")
    entry_ids: List[int] = field(default_factory=list)

    @property
    def rounded_hours(self) -> Decimal:
        return round_quantity(self.hours)

    @property
    def target(self) -> str:
        return " / ".join(part for part in (self.project_name, self.user_name) if part) or "time entry"

    def message(self) -> str:
        return f"{self.rounded_hours} h were added at 0: no hourly rate for {self.target}"


@dataclass
class TimeEntryLines:
    """Invoice lines built from time entries, plus the hours that had no rate."""

    items: List[InvoiceItem]
    missing_rates: List[MissingRate]

    @property
    def warnings(self) -> List[str]:
        return [m.message() for m in self.missing_rates]


def normalize_billable_entries(
    entries: Iterable[Union[TimeEntry, ProcessedTimeEntry, BillableTimeEntry]],
) -> List[BillableTimeEntry]:
    result: List[BillableTimeEntry] = []
    for item in entries:
        if isinstance(item, BillableTimeEntry):
            if item.billable_hours > 0:
                result.append(item)
        elif isinstance(item, ProcessedTimeEntry):
            if item.billable_hours > 0:
                result.append(BillableTimeEntry(entry=item.entry, billable_hours=item.billable_hours))
        elif isinstance(item, TimeEntry):
            hours = _hours_from_entry(item)
            if hours > 0:
                result.append(BillableTimeEntry(entry=item, billable_hours=hours))
    return result


def time_entry_line_description(entry: TimeEntry) -> str:
    task_name = entry.task.name if getattr(entry, "task", None) and entry.task else None
    notes = (entry.notes or "").strip()
    if task_name and notes:
        return f"{task_name}: {notes}"
    if notes:
        return notes
    if task_name:
        return f"Task: {task_name}"
    project = getattr(entry, "project", None)
    if project and getattr(project, "name", None):
        return f"Project: {project.name}"
    if entry.start_time:
        return f"Time entry {entry.start_time.strftime('%Y-%m-%d')}"
    return "Time entry"


def grouped_line_description(entry: TimeEntry, project_name: Optional[str] = None, *, by_task: bool = True) -> str:
    if by_task and entry.task_id:
        return f"Task: {entry.task.name if entry.task else 'Unknown Task'}"
    if entry.project and entry.project.name:
        return f"Project: {entry.project.name}"
    if project_name:
        return f"Project: {project_name}"
    return "Project hours"


def build_time_entry_lines(
    invoice_id: int,
    entries: Iterable[Union[TimeEntry, ProcessedTimeEntry, BillableTimeEntry]],
    *,
    group: bool = True,
    group_by_task: bool = True,
    project_name: Optional[str] = None,
) -> TimeEntryLines:
    """Create InvoiceItem instances from time entries with a rate resolved per entry.

    Each line has one unit price. When grouping, entries with different rates go to
    separate lines, so quantity x unit price always equals the line amount. Quantity is
    rounded to 2 places before it is multiplied by the rate. With ``group_by_task=False``
    a group is the whole project. Caller adds items to the session.
    """
    billable = normalize_billable_entries(entries)
    if not billable:
        return TimeEntryLines(items=[], missing_rates=[])

    rated: List[Tuple[BillableTimeEntry, Decimal]] = []
    missing: Dict[Tuple[Optional[int], Optional[int]], MissingRate] = {}
    for bte in billable:
        entry = bte.entry
        entry_rate = resolve_entry_rate(entry)
        rated.append((bte, entry_rate.rate))
        if not entry_rate.found:
            key = (entry.project_id, entry.user_id)
            if key not in missing:
                project = getattr(entry, "project", None)
                user = getattr(entry, "user", None)
                missing[key] = MissingRate(
                    project_name=getattr(project, "name", None) or project_name,
                    user_name=getattr(user, "display_name", None) if user else None,
                )
            missing[key].hours += bte.billable_hours
            missing[key].entry_ids.append(entry.id)

    items: List[InvoiceItem] = []

    if not group:
        for bte, rate in rated:
            items.append(
                InvoiceItem(
                    invoice_id=invoice_id,
                    description=time_entry_line_description(bte.entry),
                    quantity=round_quantity(bte.billable_hours),
                    unit_price=rate,
                    time_entry_ids=str(bte.entry.id),
                )
            )
        return TimeEntryLines(items=items, missing_rates=list(missing.values()))

    grouped: dict = {}
    for bte, rate in rated:
        entry = bte.entry
        by_task = group_by_task and entry.task_id
        base_key = f"task_{entry.task_id}" if by_task else f"project_{entry.project_id}"
        key = (base_key, rate)
        if key not in grouped:
            grouped[key] = {
                "description": grouped_line_description(entry, project_name, by_task=group_by_task),
                "rate": rate,
                "entries": [],
                "total_hours": Decimal("0"),
            }
        grouped[key]["entries"].append(bte)
        grouped[key]["total_hours"] += bte.billable_hours

    for group_data in grouped.values():
        if group_data["total_hours"] <= 0:
            continue
        items.append(
            InvoiceItem(
                invoice_id=invoice_id,
                description=group_data["description"],
                quantity=round_quantity(group_data["total_hours"]),
                unit_price=group_data["rate"],
                time_entry_ids=",".join(str(b.entry.id) for b in group_data["entries"]),
            )
        )
    return TimeEntryLines(items=items, missing_rates=list(missing.values()))


def resolve_group_time_entries_from_form(per_entry_lines_checked: bool, settings_default_group: bool = True) -> bool:
    """Return True to group entries, False for one line per entry."""
    if per_entry_lines_checked:
        return False
    return settings_default_group
