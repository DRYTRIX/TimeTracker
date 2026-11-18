# Support / Donate conversion tracking

TimeTracker records support interactions in `donation_interactions` so you can compare **Supporter key** intent vs tips (Buy Me a Coffee / €5–€25).

## Current CTA layout

As of the key-first conversion fix, everyone sees the **key_first** experience:

- Primary CTA: Become a Supporter (€25)
- Secondary: tip any amount (BMC / €5 / €10 / €25)

The previous four-way A/B (`control` | `key_first` | `cta_alt` | `never_see`) is rolled out to `key_first` in `app/utils/context_processors.py` so metrics are interpretable. Soft prompts are **not** suppressed after tip clicks; they are only suppressed for ~7 days after a **key** checkout click (mid-funnel).

## Data

- Table: `donation_interactions`
- Columns: `interaction_type`, `source`, `variant`, `created_at`, `user_id`

Canonical events:

- `link_clicked` — user clicked a support CTA (segment by `source`)
- `support_license_clicked` / `support_donation_clicked` — modal funnel (via `/donate/track-support-event`)

**Key sources** (treat as Supporter-key intent): `source` ends with `_key`, or contains `license` (e.g. `donate_page_key`, `dashboard_widget_key`, `about_page_key`, `admin_settings_key`, `license_page_key`, `milestone_key`).

**Tip sources**: e.g. `donate_page_hero`, `support_modal_bmc`, `about_page`, `milestone_bmc`.

## Example: key vs tip CTR (last 30 days)

```sql
-- Clicks by intent (key vs tip)
SELECT
  CASE
    WHEN source LIKE '%_key' OR lower(coalesce(source, '')) LIKE '%license%' THEN 'key'
    ELSE 'tip_or_other'
  END AS intent,
  COUNT(*) AS clicks
FROM donation_interactions
WHERE interaction_type = 'link_clicked'
  AND created_at >= NOW() - INTERVAL '30 days'
GROUP BY 1;

-- Share of key clicks among all support link clicks
SELECT
  ROUND(
    100.0 * SUM(CASE WHEN source LIKE '%_key' OR lower(coalesce(source, '')) LIKE '%license%' THEN 1 ELSE 0 END)
    / NULLIF(COUNT(*), 0),
    1
  ) AS key_click_pct
FROM donation_interactions
WHERE interaction_type = 'link_clicked'
  AND created_at >= NOW() - INTERVAL '30 days';
```

## 4-week review checklist

After shipping the conversion changes, wait ~4 weeks and compare:

1. **Key click share** — `%` of `link_clicked` that are key sources (SQL above); expect this to rise vs tip-first period.
2. **Absolute key purchases** — Stripe / email key issuances on the checkout service; should stop declining relative to new installs (Docker pulls / demo usage).
3. **Activations** — instances with `settings.donate_ui_hidden = true` (if you can query fleets) or support inbox volume.
4. **Soft-prompt health** — `support_prompt_shown` still fires after BMC clicks (tip must not kill the key funnel).

## Re-enabling experiments later

To A/B again, restore variant assignment in `app/utils/context_processors.py` (e.g. `user_id % N`) and branch templates carefully. Prefer testing copy/CTA order without reintroducing “remove prompts / never see this” as the headline.
