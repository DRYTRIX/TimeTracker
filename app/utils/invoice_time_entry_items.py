"""Build InvoiceItem rows from billable time entries (grouped or per-entry)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, List, Optional, Union

from app.models import InvoiceItem, TimeEntry
from app.utils.prepaid_hours import ProcessedTimeEntry


@dataclass
class BillableTimeEntry:
    entry: TimeEntry
    billable_hours: Decimal


def _hours_from_entry(entry: TimeEntry) -> Decimal:
    if not entry.duration_seconds:
        return Decimal("0")
    return Decimal(str(entry.duration_seconds)) / Decimal("3600")


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


def grouped_line_description(entry: TimeEntry, project_name: Optional[str] = None) -> str:
    if entry.task_id:
        return f"Task: {entry.task.name if entry.task else 'Unknown Task'}"
    if entry.project and entry.project.name:
        return f"Project: {entry.project.name}"
    if project_name:
        return f"Project: {project_name}"
    return "Project hours"


def build_invoice_items_from_entries(
    invoice_id: int,
    entries: Iterable[Union[TimeEntry, ProcessedTimeEntry, BillableTimeEntry]],
    hourly_rate: Decimal,
    *,
    group: bool = True,
    project_name: Optional[str] = None,
) -> List[InvoiceItem]:
    """Create InvoiceItem instances from time entries. Caller adds them to the session."""
    billable = normalize_billable_entries(entries)
    if not billable:
        return []

    items: List[InvoiceItem] = []

    if not group:
        for bte in billable:
            items.append(
                InvoiceItem(
                    invoice_id=invoice_id,
                    description=time_entry_line_description(bte.entry),
                    quantity=bte.billable_hours,
                    unit_price=hourly_rate,
                    time_entry_ids=str(bte.entry.id),
                )
            )
        return items

    grouped: dict = {}
    for bte in billable:
        entry = bte.entry
        key = f"task_{entry.task_id}" if entry.task_id else f"project_{entry.project_id}"
        if key not in grouped:
            grouped[key] = {
                "description": grouped_line_description(entry, project_name),
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
                quantity=group_data["total_hours"],
                unit_price=hourly_rate,
                time_entry_ids=",".join(str(b.entry.id) for b in group_data["entries"]),
            )
        )
    return items


def resolve_group_time_entries_from_form(per_entry_lines_checked: bool, settings_default_group: bool = True) -> bool:
    """Return True to group entries, False for one line per entry."""
    if per_entry_lines_checked:
        return False
    return settings_default_group
