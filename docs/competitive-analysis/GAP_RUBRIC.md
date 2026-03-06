# Competitive Gap Scoring Rubric

This document scores each missing or underpowered capability from the Competitive Feature Gap Analysis plan by **user impact**, **revenue impact**, and **implementation complexity**. Scores use a 1–5 scale (1 = lowest, 5 = highest). **Priority** is derived from (user + revenue) / complexity to favor high impact with feasible effort.

**Primary audience:** Individuals/Freelancers (scores weighted toward this segment where relevant).

---

## Scoring Definitions

| Dimension | 1 | 2 | 3 | 4 | 5 |
|-----------|---|---|---|---|---|
| **User impact** | Niche; few users care | Some power users | Common workflow improvement | Broad daily/weekly value | Critical for adoption/retention |
| **Revenue impact** | No monetization path | Indirect (retention) | Enables upsell or reduces churn | Clear conversion/expansion | Direct revenue or major differentiator |
| **Implementation complexity** | Large (6+ months, many systems) | High (3–6 months) | Medium (1–3 months) | Low (weeks) | Small (days to a few weeks) |

**Priority formula:** `(UserImpact + RevenueImpact) / Complexity` — higher is better. Ties broken by user impact, then revenue impact.

---

## Gap Scores

### 1. Formal timesheet periods and locking workflow

| Dimension | Score | Notes |
|-----------|-------|------|
| User impact | 4 | Essential for teams and freelancers who bill by period; reduces disputes and rework. |
| Revenue impact | 4 | Expected by mid-market/enterprise; reduces churn and supports compliance. |
| Implementation complexity | 3 | New period model, lock rules, UI for submit/approve/close; touches reports and exports. |
| **Priority** | **2.67** | High impact, moderate effort. |

---

### 2. PTO / leave + holiday and time-off workflow

| Dimension | Score | Notes |
|-----------|-------|------|
| User impact | 4 | Affects availability, capacity, and payroll; expected in any multi-person setup. |
| Revenue impact | 3 | Reduces churn in team/agency segment; enables capacity features. |
| Implementation complexity | 3 | Leave types, policies, approval flow, calendar/availability and report integration. |
| **Priority** | **2.33** | Strong value, moderate effort. |

---

### 3. Payroll-ready exports and payroll connectors

| Dimension | Score | Notes |
|-----------|-------|------|
| User impact | 5 | Directly unblocks “get paid” and payroll runs; high frustration if missing. |
| Revenue impact | 4 | Strong retention and differentiation for freelancers and small teams. |
| Implementation complexity | 2 | Templates + connectors: medium (format design, 1–2 integrations). |
| **Priority** | **4.50** | Very high impact relative to effort. |

---

### 4. Automated activity capture parity (desktop timeline / autotracker)

| Dimension | Score | Notes |
|-----------|-------|------|
| User impact | 4 | Reduces tracking friction and improves accuracy; privacy controls are mandatory. |
| Revenue impact | 3 | Differentiation vs. Toggl/Clockify; can support premium positioning. |
| Implementation complexity | 5 | Desktop agent, privacy UX, sync, and rules; large scope. |
| **Priority** | **1.40** | High value but high cost. |

---

### 5. Native accounting depth for freelancers

| Dimension | Score | Notes |
|-----------|-------|------|
| User impact | 3 | Improves reconciliation and trust; power users care most. |
| Revenue impact | 3 | Deepens stickiness and supports accounting integrations. |
| Implementation complexity | 4 | Reconciliation flows, matching, possibly double-entry concepts. |
| **Priority** | **1.50** | Valuable but complex. |

---

### 6. Mobile/desktop parity for non-tracking (invoicing, expenses, reporting)

| Dimension | Score | Notes |
|-----------|-------|------|
| User impact | 5 | Freelancers often work on the go; invoicing and expenses on mobile is expected. |
| Revenue impact | 4 | Reduces “web-only” churn and supports mobile-first users. |
| Implementation complexity | 3 | Reuse API; net-new screens and flows in Flutter/Electron. |
| **Priority** | **3.00** | High impact, moderate effort. |

---

### 7. Robust recurring cost engine

| Dimension | Score | Notes |
|-----------|-------|------|
| User impact | 3 | Improves project cost and forecasting accuracy. |
| Revenue impact | 2 | Indirect (better reporting, retention). |
| Implementation complexity | 2 | Extend project-cost model and UI; well-scoped. |
| **Priority** | **2.50** | Good ROI. |

---

### 8. Mileage GPS feature (backend complete; UI/routes missing)

| Dimension | Score | Notes |
|-----------|-------|------|
| User impact | 3 | Important for field/mileage-heavy freelancers and teams. |
| Revenue impact | 2 | Niche differentiator; completes expense story. |
| Implementation complexity | 1 | Service/model exist; add routes and UI only. |
| **Priority** | **5.00** | Quick win. |

---

### 9. Field workforce controls (geofencing, attendance policies)

| Dimension | Score | Notes |
|-----------|-------|------|
| User impact | 2 | Relevant mainly to field/operations teams. |
| Revenue impact | 2 | Niche; supports specific verticals. |
| Implementation complexity | 5 | Geofencing, policies, mobile integration; large. |
| **Priority** | **0.80** | Low priority for freelancer-first roadmap. |

---

### 10. Clear “focus mode” product packaging for solo users

| Dimension | Score | Notes |
|-----------|-------|------|
| User impact | 4 | Simplifies onboarding and daily use; reduces overwhelm. |
| Revenue impact | 3 | Better conversion and retention for individuals. |
| Implementation complexity | 1 | Mostly UX: defaults, onboarding, optional feature flags. |
| **Priority** | **7.00** | Very high ROI; mainly product/UX work. |

---

## Summary: Ranked by Priority

| Rank | Capability | Priority | Phase suggestion |
|------|------------|----------|------------------|
| 1 | Focus mode packaging for solo users | 7.00 | Phase 1 (quick) |
| 2 | Mileage GPS UI/routes (backend done) | 5.00 | Phase 1 (quick) |
| 3 | Payroll-ready exports and payroll connectors | 4.50 | Phase 1 |
| 4 | Mobile/desktop parity (invoicing, expenses, reporting) | 3.00 | Phase 1 |
| 5 | Formal timesheet periods and locking | 2.67 | Phase 2 |
| 6 | Recurring cost engine | 2.50 | Phase 1 or 2 |
| 7 | PTO/leave and time-off workflow | 2.33 | Phase 2 |
| 8 | Native accounting depth | 1.50 | Backlog |
| 9 | Automated activity capture parity | 1.40 | Backlog |
| 10 | Field workforce controls | 0.80 | Backlog |

---

## Recommended Phase Allocation

- **Phase 1 (freelancer-critical):** Focus mode packaging, mileage GPS UI, payroll exports/connectors, mobile/desktop parity for invoicing/expenses/reporting, optional start on recurring costs.
- **Phase 2 (enterprise controls):** Timesheet period close and locking, PTO/time-off workflow, capacity and compliance reporting.
- **Backlog:** Native accounting depth, automated activity capture, field workforce controls (revisit if targeting operations/field verticals).
