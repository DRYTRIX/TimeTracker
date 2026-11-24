"""Build InvoiceItem rows from billable time entries.

A layout says which entries share a line (one line per entry, per task, per person, per task and
person, or per project); a template says what the line's description reads. Inside a layout the
entries are split by hourly rate, so quantity x unit price is the line amount on every line.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple, Union

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


# ----------------------------------------------------------------------
# Layouts: which entries share a line
# ----------------------------------------------------------------------
LAYOUT_DETAILED = "detailed"
LAYOUT_TASK = "task"
LAYOUT_PERSON = "person"
LAYOUT_TASK_PERSON = "task_person"
LAYOUT_PROJECT = "project"
LAYOUT_NONE = "none"

HOURS_LAYOUTS = (LAYOUT_DETAILED, LAYOUT_TASK, LAYOUT_PERSON, LAYOUT_TASK_PERSON, LAYOUT_PROJECT, LAYOUT_NONE)

HOURS_LAYOUT_LABELS = {
    LAYOUT_DETAILED: "One line per entry",
    LAYOUT_TASK: "By task",
    LAYOUT_PERSON: "By person",
    LAYOUT_TASK_PERSON: "By task and person",
    LAYOUT_PROJECT: "One line per project",
    LAYOUT_NONE: "Don't add any hours",
}

DEFAULT_LINE_TEMPLATES = {
    LAYOUT_DETAILED: "{date} - {task} - {person}: {note}",
    LAYOUT_TASK: "{task}",
    LAYOUT_PERSON: "{date} - {person}",
    LAYOUT_TASK_PERSON: "{task} - {person}",
    LAYOUT_PROJECT: "{project} ({date})",
    LAYOUT_NONE: "",
}

TEMPLATE_PLACEHOLDERS = ("date", "project", "task", "person", "note")
DESCRIPTION_MAX_LENGTH = 500  # invoice_items.description
TEMPLATE_MAX_LENGTH = 255  # invoices.line_template, projects.last_line_template
ELLIPSIS = "…"
DEFAULT_DATE_FORMAT = "%Y-%m-%d"

_PLACEHOLDER_RE = re.compile(r"\{(" + "|".join(TEMPLATE_PLACEHOLDERS) + r")\}")
_OPENING = {"(": ")", "[": "]"}
_CLOSING = {")": "(", "]": "["}


def normalize_layout(value: Optional[str]) -> Optional[str]:
    """A known layout name, or None."""
    value = (value or "").strip().lower()
    return value if value in HOURS_LAYOUTS else None


def legacy_layout(group: Optional[bool] = None, group_by_task: Optional[bool] = None) -> str:
    """Layout for the older ``group`` / ``group_by_task`` switches."""
    if group is False:
        return LAYOUT_DETAILED
    if group_by_task is False:
        return LAYOUT_PROJECT
    return LAYOUT_TASK


def default_line_template(layout: Optional[str]) -> str:
    return DEFAULT_LINE_TEMPLATES.get(normalize_layout(layout) or LAYOUT_TASK, DEFAULT_LINE_TEMPLATES[LAYOUT_TASK])


def normalize_template(value: Optional[str]) -> Optional[str]:
    """A template trimmed to what the database keeps, or None when empty."""
    value = (value or "").strip()
    return value[:TEMPLATE_MAX_LENGTH] if value else None


def invoice_date_format() -> str:
    """strftime format of the system date setting (an invoice reads the same for every user)."""
    try:
        from app.utils.timezone import get_system_date_format

        return get_system_date_format()
    except Exception:
        return DEFAULT_DATE_FORMAT


def format_rate_suffix(rate: Decimal, currency: Optional[str] = None) -> str:
    """`` – 40.00 EUR/h``: added to the descriptions of a group split by rate, money as on the PDF."""
    amount = f"{Decimal(str(rate)):,.2f}"
    unit = f"{amount} {currency}" if currency else amount
    return f" – {unit}/h"


# ----------------------------------------------------------------------
# Descriptions
# ----------------------------------------------------------------------
def _unique(values: Iterable[Optional[str]]) -> List[str]:
    seen: List[str] = []
    for value in values:
        value = (value or "").strip()
        if value and value not in seen:
            seen.append(value)
    return seen


def _entry_date(entry: TimeEntry) -> Optional[date]:
    start = getattr(entry, "start_time", None)
    return start.date() if start else None


def _task_name(entry: TimeEntry) -> Optional[str]:
    task = getattr(entry, "task", None) if getattr(entry, "task_id", None) else None
    return task.name if task is not None else None


def _person_name(entry: TimeEntry) -> Optional[str]:
    user = getattr(entry, "user", None)
    return user.display_name if user is not None else None


def _project_name(entry: TimeEntry) -> Optional[str]:
    project = getattr(entry, "project", None)
    return project.name if project is not None else None


def line_values(
    entries: Sequence[TimeEntry], *, date_format: Optional[str] = None, project_name: Optional[str] = None
) -> Dict[str, str]:
    """Placeholder values for the entries of one line.

    ``{date}`` is the entry's date, or the line's period ``first-last`` when the entries span days;
    ``{task}``, ``{person}`` and ``{project}`` list the distinct names, comma-separated; ``{note}``
    lists the distinct notes, one per line.
    """
    date_format = date_format or DEFAULT_DATE_FORMAT
    ordered = sorted(entries, key=lambda e: (getattr(e, "start_time", None) is None, e.start_time or 0, e.id or 0))
    dates = [d for d in (_entry_date(e) for e in ordered) if d is not None]
    if not dates:
        when = ""
    elif min(dates) == max(dates):
        when = min(dates).strftime(date_format)
    else:
        when = f"{min(dates).strftime(date_format)}-{max(dates).strftime(date_format)}"
    projects = _unique(_project_name(e) for e in ordered) or _unique([project_name])
    return {
        "date": when,
        "project": ", ".join(projects),
        "task": ", ".join(_unique(_task_name(e) for e in ordered)),
        "person": ", ".join(_unique(_person_name(e) for e in ordered)),
        "note": "\n".join(_unique(getattr(e, "notes", None) for e in ordered)),
    }


def render_line_template(template: str, values: Dict[str, str]) -> str:
    """Fill a line template; an empty placeholder takes the separator in front of it along.

    ``{date} - {task} - {person}: {note}`` with no task reads ``date - person: note``. Brackets of
    the template left without a pair (``{project} ({date})`` with no date) are dropped too.
    """
    parts = _PLACEHOLDER_RE.split(template or "")
    # parts: literal, name, literal, name, ..., literal
    literals = parts[0::2]
    names = parts[1::2]
    if not names:
        return (template or "").strip()

    pieces: List[Tuple[str, str]] = [("literal", literals[0])]  # (kind, text)
    first = True
    for index, name in enumerate(names):
        value = (values.get(name) or "").strip()
        if not value:
            continue
        if not first:
            pieces.append(("literal", literals[index]))
        pieces.append(("value", value))
        first = False
    if first:
        return ""
    pieces.append(("literal", literals[-1]))

    # Drop template brackets that lost their pair
    stack: List[Tuple[int, int]] = []
    unmatched = set()
    for p_index, (kind, text) in enumerate(pieces):
        if kind != "literal":
            continue
        for c_index, char in enumerate(text):
            if char in _OPENING:
                stack.append((p_index, c_index))
            elif char in _CLOSING:
                if stack and pieces[stack[-1][0]][1][stack[-1][1]] == _CLOSING[char]:
                    stack.pop()
                else:
                    unmatched.add((p_index, c_index))
    unmatched.update(stack)

    out = []
    for p_index, (kind, text) in enumerate(pieces):
        if kind == "literal":
            text = "".join(char for c_index, char in enumerate(text) if (p_index, c_index) not in unmatched)
        out.append(text)
    return re.sub(r"[ \t]{2,}", " ", "".join(out)).strip()


def fit_description(text: str, suffix: str = "") -> str:
    """Cut a description to the column size with an ellipsis, keeping ``suffix`` whole."""
    if len(text) + len(suffix) <= DESCRIPTION_MAX_LENGTH:
        return text + suffix
    room = max(DESCRIPTION_MAX_LENGTH - len(suffix) - len(ELLIPSIS), 0)
    return text[:room].rstrip() + ELLIPSIS + suffix


def line_description(
    template: Optional[str],
    entries: Sequence[TimeEntry],
    *,
    layout: Optional[str] = None,
    rate_suffix: str = "",
    date_format: Optional[str] = None,
    project_name: Optional[str] = None,
) -> str:
    """Description of a line billing ``entries``: the template filled in, never empty."""
    values = line_values(entries, date_format=date_format, project_name=project_name)
    text = render_line_template(template or default_line_template(layout), values)
    if not text:
        text = values["project"] or values["task"] or "Time entry"
    return fit_description(text, rate_suffix)


# ----------------------------------------------------------------------
# Grouping
# ----------------------------------------------------------------------
def group_key(layout: str, entry: TimeEntry) -> tuple:
    """Entries with the same key share a line (before the split by rate)."""
    task_key = entry.task_id if entry.task_id else ("no task", entry.project_id)
    if layout == LAYOUT_DETAILED:
        return ("entry", entry.id)
    if layout == LAYOUT_PERSON:
        return ("person", entry.user_id)
    if layout == LAYOUT_TASK_PERSON:
        return ("task_person", task_key, entry.user_id)
    if layout == LAYOUT_PROJECT:
        return ("project", entry.project_id)
    return ("task", task_key)


def _name_key(name: Optional[str]) -> tuple:
    return (name is None, (name or "").lower())


def _first_start(entries: Sequence[TimeEntry]) -> tuple:
    starts = [(e.start_time, e.id or 0) for e in entries if e.start_time is not None]
    return (0, min(starts)) if starts else (1, (None, min((e.id or 0) for e in entries)))


def group_sort_key(layout: str, entries: Sequence[TimeEntry]) -> tuple:
    """Order of lines: by the layout's task and person names, then by the first entry's date."""
    first = entries[0]
    if layout == LAYOUT_TASK:
        names = (_name_key(_task_name(first)),)
    elif layout == LAYOUT_PERSON:
        names = (_name_key(_person_name(first)),)
    elif layout == LAYOUT_TASK_PERSON:
        names = (_name_key(_task_name(first)), _name_key(_person_name(first)))
    elif layout == LAYOUT_PROJECT:
        names = (_name_key(_project_name(first)),)
    else:
        names = ()
    return names + (_first_start(entries),)


@dataclass
class TimeEntryLines:
    """Invoice lines built from time entries, plus the hours that had no rate."""

    items: List[InvoiceItem]
    missing_rates: List[MissingRate]
    layout: str = LAYOUT_TASK
    template: str = ""

    @property
    def warnings(self) -> List[str]:
        return [m.message() for m in self.missing_rates]


def build_time_entry_lines(
    invoice_id: Optional[int],
    entries: Iterable[Union[TimeEntry, ProcessedTimeEntry, BillableTimeEntry]],
    *,
    layout: Optional[str] = None,
    template: Optional[str] = None,
    group: Optional[bool] = None,
    group_by_task: Optional[bool] = None,
    project_name: Optional[str] = None,
    currency: Optional[str] = None,
    date_format: Optional[str] = None,
) -> TimeEntryLines:
    """Create InvoiceItem instances (``kind="time"``) from time entries, rate resolved per entry.

    ``layout`` decides which entries share a line (``HOURS_LAYOUTS``; ``none`` adds no lines) and
    ``template`` what each line reads (default per layout). Inside a layout the entries are split
    by rate, so quantity x unit price always equals the line amount; the lines of a split group
    end with their rate (``format_rate_suffix``). Quantity is rounded to 2 places before it is
    multiplied by the rate. ``group`` / ``group_by_task`` are the older switches, used when no
    layout is given. Caller adds items to the session.
    """
    layout = normalize_layout(layout) or legacy_layout(group, group_by_task)
    template = normalize_template(template) or default_line_template(layout)
    billable = normalize_billable_entries(entries)
    if layout == LAYOUT_NONE or not billable:
        return TimeEntryLines(items=[], missing_rates=[], layout=layout, template=template)
    date_format = date_format or invoice_date_format()

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
            missing[key].hours += round_quantity(bte.billable_hours)
            missing[key].entry_ids.append(entry.id)

    # group key -> rate -> billable entries
    groups: Dict[tuple, Dict[Decimal, List[BillableTimeEntry]]] = {}
    for bte, rate in rated:
        groups.setdefault(group_key(layout, bte.entry), {}).setdefault(rate, []).append(bte)

    def entries_of(btes: Sequence[BillableTimeEntry]) -> List[TimeEntry]:
        return [b.entry for b in btes]

    ordered_groups = sorted(
        groups.values(),
        key=lambda by_rate: group_sort_key(layout, sorted(entries_of(sum(by_rate.values(), [])), key=_entry_order)),
    )

    items: List[InvoiceItem] = []
    for by_rate in ordered_groups:
        split = len(by_rate) > 1
        for rate, btes in sorted(by_rate.items(), key=lambda pair: (_first_start(entries_of(pair[1])), pair[0])):
            if sum((b.billable_hours for b in btes), Decimal("0")) <= 0:
                continue
            # Each entry's hours are rounded before they are added up, so a line's quantity is the sum of
            # what its entries show and the total is the same in every layout
            hours = sum((round_quantity(b.billable_hours) for b in btes), Decimal("0"))
            btes = sorted(btes, key=lambda b: _entry_order(b.entry))
            item = InvoiceItem(
                invoice_id=invoice_id,
                description=line_description(
                    template,
                    entries_of(btes),
                    layout=layout,
                    rate_suffix=format_rate_suffix(rate, currency) if split else "",
                    date_format=date_format,
                    project_name=project_name,
                ),
                quantity=round_quantity(hours),
                unit_price=rate,
                time_entry_ids=",".join(str(b.entry.id) for b in btes),
            )
            item.kind = "time"
            items.append(item)
    return TimeEntryLines(items=items, missing_rates=list(missing.values()), layout=layout, template=template)


def _entry_order(entry: TimeEntry) -> tuple:
    return (entry.start_time is None, entry.start_time or 0, entry.id or 0)


def describe_lines(
    lines: Sequence[Tuple[InvoiceItem, Sequence[TimeEntry]]],
    *,
    layout: Optional[str],
    template: Optional[str],
    currency: Optional[str] = None,
    date_format: Optional[str] = None,
    project_name: Optional[str] = None,
) -> Dict[int, str]:
    """New descriptions for existing time lines (index in ``lines`` -> text), from their entries.

    Lines whose entries fall in the same layout group (they differ by rate) get the rate suffix.
    Lines without entries are left out.
    """
    layout = normalize_layout(layout) or LAYOUT_TASK
    if layout == LAYOUT_NONE:
        layout = LAYOUT_TASK
    template = normalize_template(template) or default_line_template(layout)
    date_format = date_format or invoice_date_format()
    keys: Dict[int, tuple] = {}
    for index, (_item, entries) in enumerate(lines):
        if entries:
            keys[index] = group_key(layout, sorted(entries, key=_entry_order)[0])
    shared = {key for key in keys.values() if list(keys.values()).count(key) > 1}
    result: Dict[int, str] = {}
    for index, key in keys.items():
        item, entries = lines[index]
        result[index] = line_description(
            template,
            sorted(entries, key=_entry_order),
            layout=layout,
            rate_suffix=format_rate_suffix(item.unit_price, currency) if key in shared else "",
            date_format=date_format,
            project_name=project_name,
        )
    return result


def resolve_hours_layout_from_form(form, settings_default_group: bool = True) -> Optional[str]:
    """Layout chosen on the generate-from-time form: ``hours_layout``, else the older checkbox.

    Returns None when the form says nothing, so the caller falls back to the project's last layout.
    """
    layout = normalize_layout(form.get("hours_layout"))
    if layout:
        return layout
    if form.get("per_entry_lines") == "on":
        return LAYOUT_DETAILED
    return None


def layout_examples(
    entries: Sequence[TimeEntry],
    *,
    template: Optional[str] = None,
    currency: Optional[str] = None,
    project_name: Optional[str] = None,
) -> Dict[str, Dict[str, object]]:
    """For each layout: how many lines ``entries`` make and the first line's description.

    ``template`` applies to every layout; without it each layout uses its default.
    Nothing is added to the session.
    """
    examples: Dict[str, Dict[str, object]] = {}
    for layout in HOURS_LAYOUTS:
        lines = build_time_entry_lines(
            None, entries, layout=layout, template=template, currency=currency, project_name=project_name
        )
        examples[layout] = {
            "lines": len(lines.items),
            "example": lines.items[0].description if lines.items else "",
            "template": lines.template,
        }
    return examples
