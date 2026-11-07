# Unraid Community Applications — submission package

Do **not** submit the `main`/`develop` default branch. Those trees include `AndroidManifest.xml` (and other non-Container XML), which CA reports as `not_unraid_application`.

Use the template-only branch **`unraid-ca`** (only `ca_profile.xml` + Container templates + LICENSE/README).

Copies for manual Unraid installs also live under [`templates/unraid/`](../../templates/unraid/) on `develop`/`main`.

## Submit URL

[ca.unraid.net/submit/new](https://ca.unraid.net/submit/new)

## Form values (copy-paste)

| Field | Value |
|-------|--------|
| **Repository / Project** | `https://github.com/DRYTRIX/TimeTracker` |
| **Branch** | `unraid-ca` (required) |
| **Support** | `https://github.com/DRYTRIX/TimeTracker/issues` |
| **Icon** | `https://raw.githubusercontent.com/DRYTRIX/TimeTracker/main/app/static/images/timetracker-logo-icon.svg` |
| **Overview** | Self-hosted time tracking, invoicing, and Peppol e-invoicing for freelancers and teams. |
| **Category** | Productivity: Tools |

### Template XML URLs (raw, `unraid-ca` branch)

```
https://raw.githubusercontent.com/DRYTRIX/TimeTracker/unraid-ca/timetracker-db.xml
https://raw.githubusercontent.com/DRYTRIX/TimeTracker/unraid-ca/timetracker-app.xml
https://raw.githubusercontent.com/DRYTRIX/TimeTracker/unraid-ca/ca_profile.xml
```

## Checklist before submit

- [x] Branch [`unraid-ca`](https://github.com/DRYTRIX/TimeTracker/tree/unraid-ca) contains only CA files (no Android XML)
- [x] Root `ca_profile.xml` with non-empty `<Profile>`
- [x] Container templates: `timetracker-app.xml`, `timetracker-db.xml`
- [x] `Repository` / `TemplateURL` / `WebUI` fields set
- [ ] In CA submit: repo URL + **branch `unraid-ca`**, then Validate → Scan
- [ ] After approval, note the CA listing in DISTRIBUTION.md

### Expected warning (OK to leave)

**Duplicate Docker apps (1)** for `postgres:16-alpine` is expected — that image is already in CA. Moderators review companion DB templates; do not remove TimeTracker-DB unless they ask.

**Blocked without login:** Community Apps submission requires an Unraid account (Sign In step).

## Install order for CA users

1. Deploy **TimeTracker-DB** first (creates `timetracker` network + Postgres).
2. Deploy **TimeTracker** app on the same network; set `SECRET_KEY` (`openssl rand -hex 32`).
3. Open `http://<host>:8080`.

## Related

- [DISTRIBUTION.md — Unraid](../admin/deployment/DISTRIBUTION.md#unraid-community-applications)
