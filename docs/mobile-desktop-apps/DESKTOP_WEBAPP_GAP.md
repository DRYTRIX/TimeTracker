# Desktop vs Webapp Gap Analysis

Living checklist for bringing the Electron desktop client up to speed with the Flask webapp. Supersedes outdated completeness claims in [FINAL_REVIEW.md](FINAL_REVIEW.md) and [REVIEW.md](REVIEW.md).

## Versions

| Component | Version | Source |
|-----------|---------|--------|
| Web / backend | 5.9.3 | `setup.py` |
| Desktop | 5.9.3 | `desktop/package.json` |
| Mobile | 5.8.2 | `mobile/pubspec.yaml` |

## What desktop has

- Username/password login → Bearer `tt_…` token
- Timer start/stop/**pause/resume**, projects, time entries, offline Dexie sync
- Workday clock-in/out and break controls (attendance API)
- Reports summary view
- Invoices, expenses, payments, mileage, quotes, recurring invoices, credit notes
- CRM: leads, deals, client contacts and notes
- Kanban board (columns + task status)
- Workforce (timesheets / time-off / approvals)
- System tray (start/stop/pause/resume), minimize-to-tray, global shortcuts
- React + Vite renderer (primary); legacy esbuild renderer kept as fallback

## Gap matrix (5.8.3 → 5.9.3)

| Area | Web | Mobile | Desktop |
|------|-----|--------|---------|
| Timer pause/resume | Yes | No | Done |
| Reports summary UI | Yes | Partial | Done |
| Workday clock in/out + breaks | Yes | Yes | Done |
| Belgium compliance / corrections UI | Yes | Partial | Deferred |
| Kanban board | Yes (5.9.3) | No | Done |
| CRM (leads/deals/contacts/notes) | Yes | No | Done |
| Payments, mileage, quotes, recurring, credit notes | Yes | Partial | Done |
| Peppol, PDF designer, AI, portal, kiosk | Yes | No | Out of scope |

## Delivery checklist

- [x] Phase 0 — This gap document + supersede notes on stale reviews
- [x] Phase 1 — Version sync, docs hygiene, pause/resume, Reports view, view split
- [x] Phase 2 — Workday / attendance card (match mobile endpoints)
- [x] Phase 3 — Kanban, CRM, finance depth
- [x] Phase 4 — Tests + smoke verification

## Explicitly out of scope

OIDC/LDAP in-app auth, auto-update, Peppol/PDF designer, AI helper, client portal, kiosk, Slack slash commands, inventory, team chat, live mileage GPS tracking, Belgium compliance report / correction UIs.
