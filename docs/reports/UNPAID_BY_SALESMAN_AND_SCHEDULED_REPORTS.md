# Unpaid Reports and Scheduled Per-Salesman Distribution

This guide explains how to create (1) a report that includes only **unpaid time entries**, and (2) a **scheduled report** that iterates by salesman, filters to each salesman's clients, and emails each report to the corresponding salesman (e.g. KF to kf@test.de, XY to XY@test.de).

## 1. Unpaid-Only Report

### Definition of "Unpaid"

In the Report Builder, **Unpaid = billable, not yet on any invoice.**  
Time entries are treated as unpaid when:

- `billable = True`
- `paid = False`
- The entry is **not** referenced in any `InvoiceItem.time_entry_ids`

This matches the logic in `UnpaidHoursService`. The separate `/reports/unpaid-hours` page uses a different rule (it excludes only entries in *fully paid* invoices and still includes unbilled and entries in unpaid/partially paid invoices). For the Custom Report Builder and scheduled reports, the definition above applies.

### Creating an Unpaid-Only Report in the Report Builder

1. Go to **Reports → Report Builder**.
2. Use the **Unpaid time entries** quick-start button in the sidebar, or:
   - Drag **Time Entries** onto the canvas.
   - In **Filters**, enable **Unpaid Hours Only**.
   - Set **Start Date** and **End Date** (e.g. last 30 days or last month).
3. Optionally restrict by **Project** or **Custom Field** (e.g. salesman).
4. **Preview** or **Save** the report (e.g. name: "Unpaid time entries").

The **Unpaid time entries** preset sets: Time Entries, Unpaid only, and the last 30 days.

---

## 2. Scheduled Report: Unpaid by Salesman, One Email per Salesman

You can schedule the unpaid-only report so that it is **split by salesman**: one report per salesman containing only that salesman’s clients’ unpaid entries, each sent to that salesman’s email.

### Prerequisites

- **Client custom field for salesman**  
  Clients must have a custom field (e.g. `salesman`) with values like `KF`, `XY`. Time entries are attributed to a salesman via the client (from the project or the direct client on the entry).

- **Per-salesman email**  
  Use either:
  - **SalesmanEmailMapping** (see below), or
  - An **email template** (e.g. `{value}@test.de` or `{value_lower}@test.de` for lowercase).

### Step 1: Create the Report Template (Saved View)

1. In **Report Builder**, create a report as in **§ 1**:
   - Data source: **Time Entries**
   - **Unpaid Hours Only** = on
   - Set a date range (or leave default; it can be overridden by “Use previous calendar month” on the schedule).
2. **Save** the report (e.g. name: **Unpaid time entries**).

### Step 2: Create the Schedule

1. Go to **Reports → Scheduled Reports → Create**.
2. **Report View**: choose the saved “Unpaid time entries” view.
3. **Frequency**: **Monthly** (or another cadence).
4. **Use previous calendar month as date range** (if available): enable for monthly “last month” reports.
5. **Split report by custom field value**: enable.
6. **Custom Field Name**: `salesman` (or your field name).
7. **Email distribution**:
   - **All reports to recipients below**: every salesman’s report goes to the same addresses.
   - **Per value: SalesmanEmailMapping table**: use `SalesmanEmailMapping` (see § 3).
   - **Per value: email from template**: e.g. `{value}@test.de` or `{value_lower}@test.de`.
8. If **Template**:
   - **Recipient email template**: `{value}@test.de` or `{value_lower}@test.de`.
   - `{value}` = the raw value (e.g. `KF` → `KF@test.de`).
   - `{value_lower}` = lowercase (e.g. `KF` → `kf@test.de`).
9. **Email Recipients**: required. With Mapping or Template, these are used as **fallback** when no address is found for a value.

### Behaviour at Run Time

- The schedule runs (e.g. monthly) and loads the saved view’s config.
- If **Use previous calendar month** is on and cadence is monthly, the report’s date range is set to the previous month.
- For each distinct `salesman` value (from clients with time entries in that range), the system:
  - Builds a report with **Unpaid only** and **custom_field_filter = { salesman: value }** (only that salesman’s clients).
  - Resolves the recipient from **Mapping** or **Template** (or fallback).
  - Sends that report in a **separate email** to that recipient.

Example: Report for KF with unpaid entries for KF’s clients → `KF@test.de` or `kf@test.de`; same for XY.

---

## 3. SalesmanEmailMapping (for “Per value: SalesmanEmailMapping table”)

When **Email distribution** is **Per value: SalesmanEmailMapping table**, the system looks up the salesman value (e.g. `KF`, `XY`) in `SalesmanEmailMapping` and uses the configured email.

### Configuring Mappings

Ensure there is a row per salesman initial (or value) with:

- **salesman_initial**: e.g. `KF`, `XY`
- **email_address**: direct address, or
- **email_pattern**: e.g. `{value}@test.de`, or
- **domain**: used as `{initial}@domain`

`get_email_for_initial` returns, in order: `email_address`, or the result of `email_pattern` with `{value}` replaced, or `{salesman_initial}@{domain}`.

### When to Use Mapping vs Template

- **Mapping**: useful when addresses are not following a simple pattern, or when you manage them in the `SalesmanEmailMapping` UI/data.
- **Template**: useful when all addresses follow one pattern (e.g. `{value_lower}@test.de`).

---

## 4. Relation to `send_monthly_unpaid_hours_reports`

The task `send_monthly_unpaid_hours_reports` (e.g. 1st of the month at 09:00) is a **fixed** job: unpaid hours by salesman, `SalesmanEmailMapping` only, and a dedicated email layout. It does not use a Saved Report View or the Report Builder.

The **scheduled report** flow (Reports → Scheduled Reports) is more flexible:

- Any saved view (including “Unpaid time entries” from Report Builder).
- **Template** or **Mapping** for per-salesman emails.
- **Use previous calendar month** for monthly runs.
- Custom cadence and saved view filters.

You can use both: the fixed task for a simple default, and scheduled reports for customisation.

---

## 5. Files and Components

- **Report Builder**: `app/templates/reports/builder.html` (Unpaid only, Unpaid preset), `app/routes/custom_reports.py` (`generate_report_data`, `unpaid_only`, `custom_field_filter`).
- **Unpaid logic**: `app/services/unpaid_hours_service.py` (`UnpaidHoursService.get_unpaid_time_entries`).
- **Scheduled reports**: `app/services/scheduled_report_service.py` (`_generate_and_send_custom_field_reports`, `_get_recipients_for_field_value`, `use_last_month_dates`), `app/templates/reports/schedule_form.html` (distribution, template, use last month).
- **SalesmanEmailMapping**: `app/models/salesman_email_mapping.py`.
