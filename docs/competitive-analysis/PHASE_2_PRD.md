# Phase 2 PRD: Enterprise Controls

**Version:** 1.0  
**Status:** Draft  
**Audience:** Teams, agencies, and organizations requiring governance, capacity planning, and compliance.  
**Prerequisite:** Phase 1 (timesheet period close, payroll exports, mobile/desktop parity) is assumed delivered or in progress.  
**Related:** [GAP_RUBRIC.md](GAP_RUBRIC.md), [PHASE_1_PRD.md](PHASE_1_PRD.md), Competitive Feature Gap Analysis plan.

---

## 1. Purpose and Goals

Phase 2 adds enterprise-grade controls so that teams and organizations can:

1. **PTO / leave and time-off workflow** — Manage leave types, balances, requests, and approvals; surface availability in capacity and scheduling.
2. **Policy locking and approval chains** — Configurable approval chains and lock policies (e.g. who can approve, when periods lock, override rules) for audit and compliance.
3. **Capacity and compliance reporting** — Capacity views (who is available, utilization), and compliance-oriented reports (audit trail, locked-period summary, labor law-friendly exports).

Success is measured by: adoption of time-off and approval workflows, reduced manual reconciliation, and use of capacity/compliance reports for planning and audits.

---

## 2. Scope

### In scope

- **Time-off (PTO/leave):** Leave types, accrual or allowance, request/submit, approve/reject, calendar visibility, and integration with capacity (e.g. “available hours” excludes time-off).
- **Approval chains and policies:** Multi-step or role-based approval for timesheets; configurable lock rules (e.g. auto-lock N days after period end); optional delegation and override with audit.
- **Capacity reporting:** View of capacity by person/team (e.g. expected hours, allocated vs available), optionally by project; simple utilization metrics.
- **Compliance reporting:** Audit-friendly exports (who changed what and when), locked-period summary report, and optional labor-law-oriented export formats (e.g. required fields for jurisdiction).

### Out of scope for Phase 2

- Full workforce scheduling (e.g. shift planning) — only capacity visibility and time-off integration.
- Payroll processing (pay runs, tax calc) — Phase 1 export/connector remains the handoff.
- Automated activity capture, geofencing, or field workforce controls (backlog).
- Custom workflow engine (e.g. drag-and-drop approval designer) — fixed approval chain and policy options only.

---

## 3. User Stories and Requirements

### 3.1 PTO / leave and time-off workflow

| ID | Role | Story | Acceptance criteria |
|----|------|--------|---------------------|
| L1 | Admin | As an admin, I can define leave types (e.g. vacation, sick, unpaid) with optional accrual rules. | Leave types have name, code, paid/unpaid, optional annual allowance or accrual rate; at least one type is configurable. |
| L2 | User | As a user, I can request time-off for selected dates and leave type. | User selects date range and leave type; optional comment; request is submitted for approval. |
| L3 | Approver | As an approver, I can approve or reject time-off requests with a comment. | List of pending requests; approve/reject with optional comment; requester is notified. |
| L4 | User | As a user, I can see my balance (allowance used/remaining) per leave type. | Balance shown in UI and API; updated when requests are approved (and optionally when cancelled). |
| L5 | User/Admin | As a user or admin, I can see time-off on a calendar or in capacity view so I know who is out. | Calendar and capacity views show approved time-off; capacity “available hours” excludes approved leave. |
| L6 | Admin | As an admin, I can set organization holidays so they are excluded from capacity. | Holiday calendar (date or date range, optional name); used in capacity and reporting. |

**Requirements:**

- **Leave types:** Name, code, paid/unpaid, optional allowance (e.g. days per year) or accrual (e.g. X hours per month). At least one default type (e.g. “Vacation”).
- **Requests:** Start/end date, leave type, requester, status (draft, submitted, approved, rejected). Optional: half-day, attachment.
- **Approval:** Same or separate approver role from timesheet approval; configurable (e.g. manager, or admin). Notifications on submit/approve/reject.
- **Balance:** Per user per leave type; simple model (allowance − approved days/hours). Optional: carry-over rules (Phase 2.1).
- **Calendar:** Time-off visible in existing calendar view (or dedicated calendar); filter by user/team.
- **Holidays:** Admin-maintained list of dates (or ranges); non-working for capacity; optional per-locale.
- **API:** CRUD for leave types, requests, balances; list approved time-off by user/date range for capacity and reports.
- **Capacity integration:** When computing “available hours” for a user in a period, subtract approved time-off and holidays. No need for full scheduling; focus on “available” vs “allocated” (from time entries).

### 3.2 Policy locking and approval chains

| ID | Role | Story | Acceptance criteria |
|----|------|--------|---------------------|
| A1 | Admin | As an admin, I can set who is allowed to approve timesheets (e.g. by role or by manager). | Configurable approver assignment (e.g. user’s manager, or users with “approver” role); at least one approver per submitter (or per team). |
| A2 | Admin | As an admin, I can set a rule that periods auto-lock N days after period end. | Optional auto-lock: e.g. “lock 7 days after week end”; when triggered, period moves to closed and entries are locked. |
| A3 | Admin | As an admin, I can allow a designated role to override a locked period (e.g. for corrections) with an audit log. | Override creates an audit record (who, when, what period, reason); optional reason field; optional approval for override. |
| A4 | Approver | As an approver, I see a clear chain: submitter → me → (optional) next approver, and I can approve or reject with comment. | If multi-step approval is supported: each step shows current approver and history; reject returns to submitter with comment. |
| A5 | Auditor | As an auditor, I can see a log of approval and lock actions. | Audit log includes: period, action (submitted, approved, rejected, closed, override), user, timestamp, optional comment. Exportable. |

**Requirements:**

- **Approval chain:** Build on Phase 1 period submit/approve/close. Add: configurable approver (e.g. by role, by manager, or by list). Optional: two-step approval (e.g. team lead then admin).
- **Lock policies:** (1) Manual close (admin) — already in Phase 1. (2) Auto-lock: configurable “close period N days after period end” (e.g. 7 days). Optional: “lock when all approvers have approved.”
- **Override:** Role or permission “override locked period”; when used, require reason (optional but recommended); write to audit log. Optional: require second approval for override.
- **Audit log:** All submit, approve, reject, close, override actions stored with: period, user, action, timestamp, comment/reason. Query and export for compliance.
- **API:** Endpoints for policy config (admin), approval chain resolution, and audit log (filter by period, user, action, date range).
- **UI:** Admin settings for approval chain and lock rules; audit log viewer and export (CSV/Excel).

### 3.3 Capacity and compliance reporting

| ID | Role | Story | Acceptance criteria |
|----|------|--------|---------------------|
| C1 | Manager | As a manager, I can see capacity by person or team for a date range (e.g. expected hours, allocated, available). | View: user or team, period; expected hours (e.g. FTE × working days minus time-off and holidays); allocated (from time entries); available = expected − allocated − time-off. |
| C2 | Manager | As a manager, I can see utilization (allocated / expected) per person or team. | Utilization % or ratio; filter by period, team, project; export. |
| C3 | Admin/Auditor | As an admin, I can run a report of all locked periods and who approved/closed them. | Report: period, status (closed), closed-by, closed-at, approvers and approval timestamps; exportable. |
| C4 | Admin/Auditor | As an admin, I can export an audit trail of time entry and approval changes for a given period or user. | Export: entry id, user, change type (create, edit, delete, approve, lock), changed-by, changed-at, old/new values or summary; format suitable for compliance. |
| C5 | Admin | As an admin, I can produce a labor-compliance-oriented export (e.g. required fields for my jurisdiction). | At least one preset or template (e.g. “EU working time” or “US overtime”) with required fields; export filtered by date range and optionally user/team. |

**Requirements:**

- **Capacity:** Model “expected hours” per user per period: e.g. working days in period × hours per day (configurable per user or default), minus approved time-off and holidays. “Allocated” = sum of time entry hours in period. “Available” = expected − allocated (or expected − time-off first, then allocated). Display by user and optionally by team; support date range and filters.
- **Utilization:** Allocated / expected (%). Report by user, team, or project; period selector; export.
- **Locked-period report:** List closed periods with who closed them and when; optional list of approvers and approval dates. Export CSV/Excel.
- **Audit trail export:** Log of changes to time entries and to approval/period state (submit, approve, reject, close, override). Fields: entity, action, user, timestamp, optional old/new value or link to detail. Export for date range and optionally user/role.
- **Compliance export:** One or more presets (e.g. “Standard labor export”) with fixed columns (e.g. user, date, start, end, break, total hours, project, approved, locked). Document which jurisdictions or use cases each preset supports. Filter by period, user, team; export CSV/Excel.
- **API:** Endpoints for capacity summary, utilization, locked-period report, and audit export (with appropriate permissions).
- **UI:** Capacity view (table or simple chart); utilization report; compliance and audit report pages with filters and export.

---

## 4. Non-Functional Requirements

- **Security and permissions:** Time-off and approval chain respect roles; only designated approvers and admins can approve or override; audit log is tamper-evident (append-only, no delete).
- **Performance:** Capacity and utilization for 50 users and 1 year of data compute in &lt; 10 s; audit export for 1 year in &lt; 30 s.
- **Compatibility:** Phase 1 period close and export remain unchanged; Phase 2 adds policies and reporting on top.
- **Localization:** Date/time and numbers follow existing i18n; leave type names and report labels translatable.

---

## 5. Dependencies and Constraints

- **Phase 1:** Period model, submit/approve/close, and locking must be in place. Phase 2 extends approval (chains, policies) and adds lock policies and override.
- **Existing models:** Users, roles, time entries, projects. New: leave types, time-off requests, holidays (or calendar events), approval policy config, audit log entries.
- **Existing API:** Period and approval endpoints from Phase 1. Phase 2 adds leave, policy, capacity, and compliance endpoints.
- **Reporting:** Reuse existing report infrastructure where possible (filters, export); add new report types and presets.

---

## 6. Success Metrics (Targets)

- **Adoption:** X% of workspaces with 5+ users enable time-off and at least one approval/lock policy within 6 months of release.
- **Compliance:** Support tickets related to “audit trail” or “locked period proof” decrease; positive feedback on compliance export.
- **Capacity:** Usage of capacity and utilization reports by manager/admin roles (track via feature usage if available).

---

## 7. Open Questions

- Multi-step approval: support in Phase 2 or defer to Phase 2.1?
- Accrual rules: simple allowance only in Phase 2, or also accrual (e.g. X days per month)?
- Labor presets: which jurisdictions to support in first compliance template?

---

## 8. Appendix: Relationship to Phase 1

| Phase 1 deliverable | Phase 2 extension |
|---------------------|-------------------|
| Period submit/approve/close | Approval chain (who approves), lock policies (auto-lock, override), audit log. |
| Payroll export | Compliance export (audit-friendly and labor-oriented presets). |
| Mobile/desktop parity | Optional: time-off request and approval from mobile/desktop; capacity view in app or web only (TBD). |

Phase 2 does not replace Phase 1; it adds governance and visibility required by teams and enterprises while keeping the freelancer-focused flows intact.
