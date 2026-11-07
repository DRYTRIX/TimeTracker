# Unraid Community Applications — submission package

Templates already live in [`templates/unraid/`](../../templates/unraid/). Submit them to the official CA catalog so Unraid users can install without copying XML by hand.

## Submit URL

[ca.unraid.net/submit/new](https://ca.unraid.net/submit/new)

## Form values (copy-paste)

| Field | Value |
|-------|--------|
| **Repository / Project** | `https://github.com/DRYTRIX/TimeTracker` |
| **Support** | `https://github.com/DRYTRIX/TimeTracker/issues` |
| **Icon** | `https://raw.githubusercontent.com/DRYTRIX/TimeTracker/main/app/static/images/timetracker-logo-icon.svg` |
| **Overview** | Self-hosted time tracking, invoicing, and Peppol e-invoicing for freelancers and teams. |
| **Category** | Productivity: Tools |

### Template XML URLs (raw)

```
https://raw.githubusercontent.com/DRYTRIX/TimeTracker/main/templates/unraid/timetracker-db.xml
https://raw.githubusercontent.com/DRYTRIX/TimeTracker/main/templates/unraid/timetracker-app.xml
```

Profile metadata (required at **repo root only**): [`ca_profile.xml`](../../ca_profile.xml)

Do **not** put `ca_profile.xml` under `templates/unraid/` — CA will treat it as an app template (`not_unraid_application`) and may flag a duplicate `Name`.

## Checklist before submit

- [x] Root [`ca_profile.xml`](../../ca_profile.xml) with non-empty `<Profile>` (`CommunityApplications` format)
- [x] Only Container templates under `templates/unraid/` (`timetracker-app.xml`, `timetracker-db.xml`)
- [x] `Repository` points at `ghcr.io/drytrix/timetracker:latest` / `postgres:16-alpine`
- [x] `TemplateURL` raw GitHub URLs set on both XMLs
- [x] `Support`, `Project`, `Overview` filled
- [x] `WebUI` = `http://[IP]:[PORT:8080]/` on the app template
- [ ] Changes **pushed** to GitHub (CA reads the remote, not your local disk)
- [ ] Maintainer signs in at ca.unraid.net and submits repo `https://github.com/DRYTRIX/TimeTracker` (moderator review ~1–2 weeks)
- [ ] After approval, note the CA listing in DISTRIBUTION.md

**Blocked without login:** Community Apps submission requires an Unraid account (Sign In step).

## Install order for CA users

1. Deploy **TimeTracker-DB** first (creates `timetracker` network + Postgres).
2. Deploy **TimeTracker** app on the same network; set `SECRET_KEY` (`openssl rand -hex 32`).
3. Open `http://<host>:8080`.

## Related

- [DISTRIBUTION.md — Unraid](../admin/deployment/DISTRIBUTION.md#unraid-community-applications)
