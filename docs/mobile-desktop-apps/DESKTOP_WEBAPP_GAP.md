# Desktop vs Webapp Gap Analysis

Living checklist for bringing the Electron desktop client up to speed with the Flask webapp. Supersedes outdated completeness claims in [FINAL_REVIEW.md](FINAL_REVIEW.md) and [REVIEW.md](REVIEW.md).

## Versions

| Component | Version | Source |
|-----------|---------|--------|
| Web / backend | 5.19.1 | `setup.py` / `VERSION` |
| Desktop | 5.19.1 | `desktop/package.json` |
| Mobile | 5.19.1 | `mobile/pubspec.yaml` |

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

## Gap matrix (current)

| Area | Web | Mobile | Desktop |
|------|-----|--------|---------|
| Timer pause/resume | Yes | Yes | Done |
| Reports summary UI | Yes | Partial | Done |
| Workday clock in/out + breaks | Yes | Yes | Done |
| Belgium compliance / corrections UI | Yes | Partial | Deferred |
| Kanban board | Yes | Yes | Done |
| CRM (leads/deals/contacts/notes) | Yes | Yes (hub) | Done |
| Payments, mileage, quotes, recurring, credit notes | Yes | Partial | Done |
| Offline sync (idempotent queue) | PWA | Yes | Done |
| API login + 2FA | Yes | Yes | Done |
| Failed offline-queue UI | N/A | Phase 6 | Phase 6 |
| Peppol, PDF designer, AI, portal, kiosk | Yes | Out of scope | Out of scope |
| Inventory | Yes | Out of scope | Out of scope |

## Delivery checklist

- [x] Phase 0 — This gap document + supersede notes on stale reviews
- [x] Phase 1 — Version sync, docs hygiene, pause/resume, Reports view, view split
- [x] Phase 2 — Workday / attendance card (match mobile endpoints)
- [x] Phase 3 — Kanban, CRM, finance depth
- [x] Phase 4 — Tests + smoke verification

## Explicitly out of scope

OIDC/LDAP in-app auth, auto-update, Peppol/PDF designer, AI helper, client portal, kiosk, Slack slash commands, inventory, team chat, live mileage GPS tracking, Belgium compliance report / correction UIs.
