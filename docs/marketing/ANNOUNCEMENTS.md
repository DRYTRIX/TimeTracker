# Announcement drafts (star / discovery growth)

Use these after the README demo GIF, screenshot paths, and browseable demo are live.
Prefer **shipping a release or fix first**, then posting — empty “please star” posts underperform.

**Also do first:** directory listings in [LISTING_SUBMISSIONS.md](LISTING_SUBMISSIONS.md) and cadence in [PUBLISHING_CHECKLIST.md](PUBLISHING_CHECKLIST.md). HN/Reddit must be submitted from your account (not automated).

## Show HN (Hacker News)

**Title:** Show HN: TimeTracker – self-hosted Toggl/Clockify alternative with Peppol e-invoicing

**Body:**

```text
I built TimeTracker for freelancers and small teams who want timers → invoices on their own server, without per-seat SaaS pricing.

Differentiator vs Toggl/Clockify/Harvest: bundled Peppol / EN 16931 (Factur-X / ZUGFeRD) so you can send compliant e-invoices yourself — not only PDF export.

- Live demo: https://timetracker-demo.drytrix.com (login test / test123!)
- Source: https://github.com/DRYTRIX/TimeTracker
- One-command Docker install in the README

Happy to answer questions about self-hosting, Peppol Bridge, or the Docker/NAS deploy path.
```

Post once at [https://news.ycombinator.com/submit](https://news.ycombinator.com/submit) **after** merging the README/demo fixes and redeploying the Render demo. Do not re-post the same day.

Draft only — HN/Reddit must be submitted from your account (not automated).

## Reddit — r/selfhosted

**Title:** TimeTracker – self-hosted time tracking + PDF/Peppol invoicing (open-source Toggl/Clockify alternative)

**Body:**

```text
Looking for feedback from the self-hosted crowd.

TimeTracker is GPL-3.0: timers, projects, clients, PDF invoices, and Peppol/EN 16931 e-invoicing in one Docker stack — no per-user fees.

- Demo: https://timetracker-demo.drytrix.com (test / test123!)
- Repo: https://github.com/DRYTRIX/TimeTracker
- NAS-friendly compose: docker-compose.nas.yml

Curious what you'd want next for homelab / small-agency use (OIDC, backups, reporting, etc.).
```

Also suitable (adapt tone): r/homelab, r/opensource, country freelancer subs if e-invoicing is relevant.

## Awesome lists

Already listed in [awesome-selfhosted → Time Tracking](https://github.com/awesome-selfhosted/awesome-selfhosted).

Other targets if not yet listed:

- [awesome-docker](https://github.com/veggiemonk/awesome-docker) — only if there is a fitting “Applications” subsection
- [AlternativeTo](https://alternativeto.net/) / [OpenAlternative](https://openalternative.co/) — list as Toggl Track / Clockify / Harvest alternative; lead with Peppol + self-host

## Release → announce habit

1. Cut a release with a crisp highlight (e.g. Peppol Bridge, Factur-X, NAS install).
2. Update demo (Render deploy hook / `TimeTrackerDemoRender` secret).
3. Submit directories from [LISTING_SUBMISSIONS.md](LISTING_SUBMISSIONS.md) / [UNRAID_CA_SUBMIT.md](UNRAID_CA_SUBMIT.md) if not done yet.
4. Post Show HN **or** Reddit (not both the same hour with identical text) — paste from this file; submit from your account at [HN submit](https://news.ycombinator.com/submit) or Reddit.
5. Link the demo credentials every time.

## Paste checklist (before you hit submit)

- [ ] Demo loads; credentials work (`test` / `test123!`)
- [ ] Latest release notes mention the highlight you lead with
- [ ] Title matches the draft (no “please star”)
- [ ] First HN comment (if Show HN) tells the Peppol / self-host story
- [ ] You are **not** cross-posting the same text to HN + Reddit the same hour
