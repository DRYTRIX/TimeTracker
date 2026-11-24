"""How hours become invoice lines: layouts, the split by rate and the description template."""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from factories import ClientFactory, ProjectFactory, TimeEntryFactory, UserFactory

from app import db
from app.models import RateOverride, Task
from app.utils.invoice_time_entry_items import (
    DESCRIPTION_MAX_LENGTH,
    HOURS_LAYOUTS,
    build_time_entry_lines,
    layout_examples,
    line_values,
    render_line_template,
)

pytestmark = pytest.mark.unit

DATE_FORMAT = "%d/%m/%Y"


@pytest.fixture
def october(app):
    """Two tasks, two people; Ben's rate goes from 40 to 50 on the 15th.

    Ann: Design 2 h (5th), Meetings 1 h (6th). Ben: Design 3 h (7th), Design 1 h (20th, at 50),
    Meetings 0.5 h (21st, at 50). Total: 6 h at 40 and 1.5 h at 50 = 315.00.
    """
    cl = ClientFactory(name="Layout Client", default_hourly_rate=None)
    project = ProjectFactory(name="Layout Project", client_id=cl.id, hourly_rate=Decimal("40.00"))
    ann = UserFactory(username="ann", full_name="Ann")
    ben = UserFactory(username="ben", full_name="Ben")
    db.session.flush()
    design = Task(name="Design", project_id=project.id, status="todo", created_by=ann.id)
    meetings = Task(name="Meetings", project_id=project.id, status="todo", created_by=ann.id)
    db.session.add_all([design, meetings])
    db.session.add(
        RateOverride(
            project_id=project.id, user_id=ben.id, hourly_rate=Decimal("50.00"), effective_from=date(2026, 10, 15)
        )
    )
    db.session.flush()

    def entry(user, task, day, hours, notes=None):
        start = datetime(2026, 10, day, 9, 0)
        return TimeEntryFactory(
            user_id=user.id,
            project_id=project.id,
            task_id=task.id,
            start_time=start,
            end_time=start + timedelta(hours=hours),
            notes=notes,
            billable=True,
        )

    entries = [
        entry(ann, design, 5, 2, "Wireframes"),
        entry(ann, meetings, 6, 1, "Kickoff"),
        entry(ben, design, 7, 3, "Layout"),
        entry(ben, design, 20, 1, "Layout"),
        entry(ben, meetings, 21, 0.5),
    ]
    db.session.commit()
    return {"project": project, "entries": entries}


def _build(october, layout, template=None):
    return build_time_entry_lines(
        1, october["entries"], layout=layout, template=template, currency="EUR", date_format=DATE_FORMAT
    )


def _rows(lines):
    return [(item.description, item.quantity, item.unit_price, item.total_amount) for item in lines.items]


def _total(lines):
    return sum((item.total_amount for item in lines.items), Decimal("0"))


def test_detailed_is_one_line_per_entry(october):
    lines = _build(october, "detailed")
    assert _rows(lines) == [
        ("05/10/2026 - Design - Ann: Wireframes", Decimal("2.00"), Decimal("40.00"), Decimal("80.00")),
        ("06/10/2026 - Meetings - Ann: Kickoff", Decimal("1.00"), Decimal("40.00"), Decimal("40.00")),
        ("07/10/2026 - Design - Ben: Layout", Decimal("3.00"), Decimal("40.00"), Decimal("120.00")),
        ("20/10/2026 - Design - Ben: Layout", Decimal("1.00"), Decimal("50.00"), Decimal("50.00")),
        # No note: no hanging ": "
        ("21/10/2026 - Meetings - Ben", Decimal("0.50"), Decimal("50.00"), Decimal("25.00")),
    ]
    assert all(item.kind == "time" for item in lines.items)


def test_by_task_splits_a_task_by_rate_and_names_the_rate(october):
    assert _rows(_build(october, "task")) == [
        ("Design – 40.00 EUR/h", Decimal("5.00"), Decimal("40.00"), Decimal("200.00")),
        ("Design – 50.00 EUR/h", Decimal("1.00"), Decimal("50.00"), Decimal("50.00")),
        ("Meetings – 40.00 EUR/h", Decimal("1.00"), Decimal("40.00"), Decimal("40.00")),
        ("Meetings – 50.00 EUR/h", Decimal("0.50"), Decimal("50.00"), Decimal("25.00")),
    ]


def test_by_person_shows_the_period_of_each_line(october):
    assert _rows(_build(october, "person")) == [
        ("05/10/2026-06/10/2026 - Ann", Decimal("3.00"), Decimal("40.00"), Decimal("120.00")),
        ("07/10/2026 - Ben – 40.00 EUR/h", Decimal("3.00"), Decimal("40.00"), Decimal("120.00")),
        ("20/10/2026-21/10/2026 - Ben – 50.00 EUR/h", Decimal("1.50"), Decimal("50.00"), Decimal("75.00")),
    ]


def test_by_task_and_person(october):
    assert [row[0] for row in _rows(_build(october, "task_person"))] == [
        "Design - Ann",
        "Design - Ben – 40.00 EUR/h",
        "Design - Ben – 50.00 EUR/h",
        "Meetings - Ann",
        "Meetings - Ben",
    ]


def test_one_line_per_project_and_rate(october):
    assert _rows(_build(october, "project")) == [
        (
            "Layout Project (05/10/2026-07/10/2026) – 40.00 EUR/h",
            Decimal("6.00"),
            Decimal("40.00"),
            Decimal("240.00"),
        ),
        (
            "Layout Project (20/10/2026-21/10/2026) – 50.00 EUR/h",
            Decimal("1.50"),
            Decimal("50.00"),
            Decimal("75.00"),
        ),
    ]


def test_none_adds_no_lines(october):
    assert _build(october, "none").items == []


def test_every_layout_bills_the_same_total_and_each_line_is_quantity_times_price(october):
    for layout in HOURS_LAYOUTS:
        lines = _build(october, layout)
        if layout == "none":
            continue
        assert _total(lines) == Decimal("315.00"), layout
        for item in lines.items:
            assert item.total_amount == item.quantity * item.unit_price
        linked = sorted(int(i) for item in lines.items for i in item.time_entry_ids.split(","))
        assert linked == sorted(e.id for e in october["entries"]), layout


def test_older_switches_map_to_layouts(october):
    assert len(build_time_entry_lines(1, october["entries"], group=False).items) == 5
    assert len(build_time_entry_lines(1, october["entries"], group=True, group_by_task=False).items) == 2
    assert len(build_time_entry_lines(1, october["entries"]).items) == 4


def test_template_with_every_placeholder_on_several_entries(october):
    design_at_40 = [october["entries"][0], october["entries"][2]]
    values = line_values(design_at_40, date_format=DATE_FORMAT)
    assert values == {
        "date": "05/10/2026-07/10/2026",
        "project": "Layout Project",
        "task": "Design",
        "person": "Ann, Ben",
        "note": "Wireframes\nLayout",
    }
    (item,) = build_time_entry_lines(
        1,
        design_at_40,
        layout="task",
        template="{project}: {task} by {person} ({date})\n{note}",
        date_format=DATE_FORMAT,
    ).items
    assert item.description == "Layout Project: Design by Ann, Ben (05/10/2026-07/10/2026)\nWireframes\nLayout"


def test_notes_are_listed_once(october):
    ben_design = [october["entries"][2], october["entries"][3]]
    assert line_values(ben_design)["note"] == "Layout"


@pytest.mark.parametrize(
    "template, values, expected",
    [
        ("{date} - {task} - {person}: {note}", {"date": "d", "person": "p", "note": "n"}, "d - p: n"),
        ("{date} - {task} - {person}: {note}", {"date": "d", "task": "t", "person": "p"}, "d - t - p"),
        ("{date} - {task} - {person}: {note}", {"task": "t", "note": "n"}, "t: n"),
        ("{project} ({date})", {"project": "P"}, "P"),
        ("{project} ({date})", {"date": "d"}, "d"),
        ("Hours: {task}", {"task": "t"}, "Hours: t"),
        ("{task} - {person}", {}, ""),
        ("Fixed text", {}, "Fixed text"),
        ("{unknown} {task}", {"task": "t"}, "{unknown} t"),
    ],
)
def test_empty_placeholders_leave_no_hanging_separators(template, values, expected):
    assert render_line_template(template, values) == expected


def test_an_empty_description_falls_back_to_the_project(october):
    (item,) = build_time_entry_lines(1, [october["entries"][4]], layout="detailed", template="{note}").items
    assert item.description == "Layout Project"


def test_description_is_cut_to_the_column_with_an_ellipsis(october):
    entry = october["entries"][0]
    entry.notes = "x" * 600
    db.session.commit()
    (item,) = build_time_entry_lines(1, [entry], layout="detailed", template="{note}").items
    assert len(item.description) == DESCRIPTION_MAX_LENGTH
    assert item.description.endswith("x…")


def test_a_cut_description_keeps_its_rate(october):
    ben = [october["entries"][2], october["entries"][3]]
    for entry in ben:
        entry.notes = "y" * 600
    db.session.commit()
    lines = build_time_entry_lines(1, ben, layout="task", template="{note}", currency="EUR")
    assert len(lines.items) == 2
    for item in lines.items:
        assert len(item.description) == DESCRIPTION_MAX_LENGTH
        assert item.description.endswith(f"… – {item.unit_price} EUR/h")


def test_layout_examples_give_the_first_line_and_the_count(october):
    examples = layout_examples(october["entries"], currency="EUR")
    assert examples["detailed"]["lines"] == 5
    assert examples["task"]["example"] == "Design – 40.00 EUR/h"
    assert examples["none"] == {"lines": 0, "example": "", "template": ""}


def test_each_entry_is_rounded_before_lines_add_up(app):
    """Three entries of 20 minutes at 100: 0.33 h each, 99.00 in every layout (not 1.00 h = 100.00 on one line)."""
    cl = ClientFactory(name="Rounding Client", default_hourly_rate=None)
    project = ProjectFactory(name="Rounding Project", client_id=cl.id, hourly_rate=Decimal("100.00"))
    people = [UserFactory(username=f"rounding-{n}", full_name=f"Person {n}") for n in range(2)]
    db.session.flush()
    task = Task(name="Support", project_id=project.id, status="todo", created_by=people[0].id)
    db.session.add(task)
    db.session.flush()
    entries = []
    for day, person in ((3, people[0]), (4, people[1]), (5, people[0])):
        start = datetime(2026, 10, day, 9, 0)
        entries.append(
            TimeEntryFactory(
                user_id=person.id,
                project_id=project.id,
                task_id=task.id,
                start_time=start,
                end_time=start + timedelta(minutes=20),
                billable=True,
            )
        )
    db.session.commit()

    for layout in HOURS_LAYOUTS:
        lines = build_time_entry_lines(1, entries, layout=layout)
        if layout == "none":
            assert lines.items == []
            continue
        assert _total(lines) == Decimal("99.00"), layout
        assert sum((item.quantity for item in lines.items), Decimal("0")) == Decimal("0.99"), layout
        for item in lines.items:
            assert item.quantity == Decimal("0.33") * len(item.time_entry_ids.split(","))
