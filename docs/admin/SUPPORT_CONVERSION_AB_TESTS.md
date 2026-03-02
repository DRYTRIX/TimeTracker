# Support / Donate conversion A/B tests

TimeTracker supports in-product A/B tests for support and key-purchase CTAs. Variants are assigned stably per user (by `user_id % 3`) and recorded with every support interaction so you can compare conversion by variant.

## Variants

- **control** — Default: donate-first hero, “Support updates” copy.
- **key_first** — Hero shows “Remove prompts with key” as primary button, then Donate.
- **cta_alt** — Alternate CTA copy: “Donate to support development — or get a key to remove prompts”.

## Data

- Table: `donation_interactions`
- Columns used for experiments: `interaction_type`, `source`, `variant`, `created_at`, `user_id`

Canonical events:

- `banner_impression` — Support banner was shown (source: `banner`).
- `banner_dismissed` — User dismissed the banner.
- `link_clicked` — User clicked a support CTA (source: e.g. `header`, `banner_bmc`, `banner_key`, `donate_page_hero`, `donate_page_key`, `dashboard_widget`, `about_page`).

## Example: CTR by variant

```sql
-- Clicks per variant (link_clicked)
SELECT variant, COUNT(*) AS clicks
FROM donation_interactions
WHERE interaction_type = 'link_clicked'
  AND created_at >= NOW() - INTERVAL '30 days'
GROUP BY variant;

-- Banner impression -> click rate by variant
SELECT
  variant,
  COUNT(DISTINCT CASE WHEN interaction_type = 'banner_impression' THEN user_id END) AS impressions,
  COUNT(DISTINCT CASE WHEN interaction_type = 'link_clicked' THEN user_id END) AS clickers
FROM donation_interactions
WHERE created_at >= NOW() - INTERVAL '30 days'
  AND source = 'banner' OR (interaction_type = 'link_clicked' AND source LIKE 'banner%')
GROUP BY variant;
```

(Adjust for your DB dialect and date range.)

## Rolling out a winner

1. Run the experiment for at least 2–4 weeks and compare CTR (and, if available, key purchases) by variant.
2. In `app/utils/context_processors.py`, set `support_ab_variant` to the winning variant for everyone, e.g. `support_ab_variant = "key_first"` (remove the `current_user.id % 3` logic).
3. Optionally remove variant-specific template branches in `app/templates/main/donate.html` and keep only the winning layout/copy.
4. Keep the `variant` column and tracking for future experiments.

## Turning experiments off

To show the same experience to all users (no A/B), set in the context processor:

```python
support_ab_variant = "control"
```

and do not pass `variant` from the frontend, or keep sending it; both will record as `control`.
