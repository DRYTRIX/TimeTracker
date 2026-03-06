# Phase 1 PRD: Freelancer-Critical Gaps

**Version:** 1.0  
**Status:** Draft  
**Audience:** Individuals and freelancers (primary); small teams (secondary).  
**Related:** [GAP_RUBRIC.md](GAP_RUBRIC.md), Competitive Feature Gap Analysis plan.

---

## 1. Purpose and Goals

Phase 1 closes the highest-impact gaps for freelancers and small teams by:

1. **Timesheet period close** — Formal submit/approve/close workflow so time is locked by period and ready for billing/payroll.
2. **Payroll-ready exports and payroll connectors** — Structured exports and optional integrations so users can hand off data to payroll or accounting without manual rework.
3. **Mobile and desktop parity for invoicing, expenses, and reporting** — Core cash-flow actions (invoices, expenses, basic reports) available in mobile and desktop apps, not only on the web.

Success is measured by: reduced time-to-invoice, fewer support requests about “how do I get my data to payroll?”, and increased use of mobile/desktop for invoicing and expenses.

---

## 2. Scope

### In scope

- Timesheet period model and period-based submit/approve/close workflow (with locking).
- Payroll-ready export formats (e.g. CSV/Excel with required fields and optional templates).
- At least one payroll or accounting connector (e.g. export format accepted by a major payroll provider, or sync to QuickBooks/Xero for payroll-related data).
- Mobile app: list/create/edit invoices; list/add expenses; view a basic time/revenue report.
- Desktop app: same as mobile (list/create/edit invoices; list/add expenses; basic report view).
- API support for all new period and export behaviors so mobile/desktop can use them.

### Out of scope for Phase 1

- Full accounting reconciliation or double-entry.
- PTO/leave and time-off (Phase 2).
- Automated activity capture / desktop timeline (backlog).
- Geofencing or field workforce controls (backlog).

### Optional Phase 1 quick wins (from rubric)

- **Focus mode packaging:** Defaults and onboarding that emphasize timer + quick log + invoice for solo users.
- **Mileage GPS UI:** Expose existing GPS mileage backend via routes and UI (start/stop track, create expense from track).

---

## 3. User Stories and Requirements

### 3.1 Timesheet period close

| ID | Role | Story | Acceptance criteria |
|----|------|--------|---------------------|
| T1 | User | As a user, I can submit my time for a given period (e.g. week) so that it is ready for approval. | User selects a period (e.g. week); system validates entries are complete (e.g. no open timer); user submits; period moves to “submitted”. |
| T2 | Approver | As an approver, I can approve or reject a submitted timesheet with a comment. | Approver sees list of submitted periods; can approve or reject with optional comment; submitter is notified. |
| T3 | Admin | As an admin, I can close a period so that no further edits are allowed. | Once closed, time entries in that period are locked (no add/edit/delete); configurable by period type (e.g. weekly/monthly). |
| T4 | User | As a user, I see clearly which periods are draft, submitted, approved, or closed. | UI and API show period status; filters and reports can use it. |

**Requirements:**

- **Period definition:** Support at least weekly period type (e.g. Mon–Sun or configurable start day). Optional: bi-weekly or monthly.
- **Validation:** Before submit, warn or block if there is an active timer or if required fields (e.g. project) are missing on any entry in the period.
- **Locking:** When a period is closed, entries in that period are read-only. Optional: allow admin override with audit log.
- **Notifications:** Optional email/in-app when period is submitted, approved, or rejected.
- **API:** Endpoints for: list periods, get period status, submit period, approve/reject period, close period (admin). Mobile/desktop use these for period status and submit.

### 3.2 Payroll-ready exports and payroll connectors

| ID | Role | Story | Acceptance criteria |
|----|------|--------|---------------------|
| P1 | User | As a user, I can export my time (or my team’s) in a payroll-ready format. | Export includes: user, period, hours, rate (if applicable), project/cost center, and other fields required by a defined payroll template. |
| P2 | Admin | As an admin, I can choose a payroll export template (e.g. provider-specific format). | At least one template (e.g. generic CSV with standard columns); optional second template for a specific payroll product. |
| P3 | User | As a user, I can export approved time only so I don’t send unapproved data to payroll. | Filter: “approved periods only” or “closed periods only” for export. |
| P4 | User | As a user, I can push time (and optionally expenses) to QuickBooks or Xero for payroll/accounting. | Connector syncs approved/closed time (and optionally expenses) to the connected product; documented limitations and field mapping. |

**Requirements:**

- **Export formats:** CSV and Excel with configurable columns. At least one “payroll” preset: user identifier, name, period start/end, total hours, billable flag, project/code, rate, amount (if applicable).
- **Templates:** Admin can save/select export templates (column set + filters). One template marked as “payroll default”.
- **Approval gating:** Export UI and API support “only approved” or “only closed” periods.
- **Connectors:** Phase 1 delivers at least one of: (a) improved QuickBooks/Xero sync for time (and optionally expenses), or (b) a documented export format that matches a specific payroll provider’s import. Full bidirectional sync is out of scope; one-way export/sync is in scope.
- **API:** Export endpoint (or report endpoint with format=payroll) that returns payroll-ready data for given period and filters.

### 3.3 Mobile and desktop parity (invoicing, expenses, reporting)

| ID | Role | Story | Acceptance criteria |
|----|------|--------|---------------------|
| M1 | User | As a mobile/desktop user, I can list and open my invoices. | List shows key fields (number, client, amount, status); tap/click opens detail. |
| M2 | User | As a mobile/desktop user, I can create and send a new invoice from tracked time. | User selects period/project/entries; system generates draft invoice; user can edit line items and send (email). |
| M3 | User | As a mobile/desktop user, I can list and add expenses. | List with filters; add expense (amount, category, date, receipt photo optional); link to project. |
| M4 | User | As a mobile/desktop user, I can view a simple time or revenue report. | At least one report: time by project or by period, or revenue/billable summary; same date range and filter options as web where feasible. |

**Requirements:**

- **API:** Mobile and desktop consume existing or new API endpoints. Ensure:
  - Invoices: list, get, create, update, “send” (email).
  - Expenses: list, get, create, update; optional file upload for receipt.
  - Reports: time summary and/or revenue summary by period, project, user (permissions apply).
- **UI:** Mobile (Flutter) and desktop (Electron) add screens for: Invoice list and detail; Invoice create/edit; Expense list and add; Report (one summary view). Reuse existing API tokens and auth.
- **Offline:** Optional: cache invoice and expense list for offline viewing; sync when back online. Not required for Phase 1 MVP if time-consuming.
- **Consistency:** Same business rules as web (e.g. who can see which invoices/expenses, rounding, currency).

---

## 4. Non-Functional Requirements

- **Performance:** Period list and export for 1 year of data for a single user complete in &lt; 5 s under normal load.
- **Security:** Period close and approval actions are permission-controlled; export and connector data respect role and scope.
- **Compatibility:** Existing web flows (timer, time entries, invoicing, expenses) continue to work; period close is additive (e.g. optional per workspace or per role).
- **Accessibility:** New web UI meets existing WCAG 2.1 AA expectations; mobile/desktop follow platform guidelines.

---

## 5. Dependencies and Constraints

- **Existing models:** Time entries, projects, users, approvals (per-entry). Period model is new; period status and lock logic are new.
- **Existing API:** `api_v1` time-entries, invoices, expenses, reports. Extend with period endpoints and payroll export.
- **Mobile/desktop:** Current apps use timer, time entries, projects, tasks. Add invoicing, expenses, and one report; reuse existing auth and API client patterns.
- **Integrations:** QuickBooks and Xero connectors exist; extend for time (and optionally expenses) sync if chosen for Phase 1.

---

## 6. Success Metrics (Targets)

- **Adoption:** X% of active workspaces use at least one of: period submit, payroll export, or mobile/desktop invoice or expense action within 3 months of release (target TBD).
- **Support:** Reduction in “how do I export for payroll?” and “can I invoice from the app?” type tickets.
- **Usage:** Increase in mobile/desktop share of invoice and expense creation (measure via API or analytics if available).

---

## 7. Open Questions

- Period type: weekly only for MVP or also bi-weekly/monthly?
- Payroll connector: prioritize QuickBooks/Xero time sync vs. a specific payroll vendor CSV format?
- Mobile receipt upload: use existing attachment API or new endpoint?

---

## 8. Appendix: Optional Quick Wins

- **Focus mode:** Default dashboard and onboarding path for “solo freelancer”: timer, quick log, “Create invoice from time” and “Add expense” prominent; hide or de-emphasize CRM/inventory for this mode.
- **Mileage GPS UI:** Expose `GPSTrackingService` and `MileageTrack` via REST routes and a simple web UI (start/stop track, create expense from track). Mobile can call same API later.

These can be scheduled in Phase 1 if capacity allows, or immediately after the three main pillars.
