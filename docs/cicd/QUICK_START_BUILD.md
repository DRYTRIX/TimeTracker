# Quick Start: Build Configuration

## 🚀 Set Up Official Builds in 5 Minutes

### Step 1: Get Your Keys (2 min)

**PostHog:**
- Go to https://posthog.com → Create project
- Copy your API key (starts with `phc_`)

**Sentry:**
- Go to https://sentry.io → Create project  
- Copy your DSN (starts with `https://`)

### Step 2: Add to GitHub (1 min)

```
Your Repo → Settings → Secrets and variables → Actions → New secret
```

Add two secrets:
```
Name: POSTHOG_API_KEY
Value: phc_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx

Name: SENTRY_DSN  
Value: https://xxx@xxx.ingest.sentry.io/xxx
```

### Step 3: Trigger Build (1 min)

```bash
git tag v3.0.0
git push origin v3.0.0
```

Watch the build at: **Actions tab → Build and Publish Official Release**

### Step 4: Verify (1 min)

```bash
docker pull ghcr.io/YOUR_USERNAME/timetracker:v3.0.0
docker run -p 5000:5000 ghcr.io/YOUR_USERNAME/timetracker:v3.0.0
```

Open http://localhost:5000 → You'll see the setup page!

---

## How It Works

### Official Build
```
GitHub Actions replaces placeholders with real keys:
%%POSTHOG_API_KEY_PLACEHOLDER%% → phc_abc123...

Result: Analytics work out of the box (if user opts in)
```

### Self-Hosted Build
```
Placeholders remain:
%%POSTHOG_API_KEY_PLACEHOLDER%% → Stays as is

Result: No analytics unless user provides own keys
```

---

## Configuration Priority

```
1. Environment Variables (User Override)
   export POSTHOG_API_KEY="my-key"
   ↓
2. Built-in Defaults (Official Builds)
   phc_abc123... (from GitHub Actions)
   ↓
3. Disabled (Self-Hosted)
   %%PLACEHOLDER%% → Empty
```

---

## Key Files

| File | Purpose |
|------|---------|
| `app/config/analytics_defaults.py` | Placeholders get replaced here |
| `.github/workflows/build-and-publish.yml` | Injects keys during build |
| `.github/workflows/build-dev.yml` | Dev builds (no injection) |

---

## Common Commands

### Check Build Type
```bash
docker run --rm IMAGE \
  python3 -c "from app.config.analytics_defaults import is_official_build; \
  print('Official' if is_official_build() else 'Self-hosted')"
```

### View Configuration
```bash
docker run --rm IMAGE \
  python3 -c "from app.config.analytics_defaults import get_analytics_config; \
  import json; print(json.dumps(get_analytics_config(), indent=2))"
```

### Override Keys
```bash
docker run -e POSTHOG_API_KEY="custom" IMAGE
```

---

## Troubleshooting

**Build fails with "placeholder not replaced"?**
→ Check GitHub Secrets are set correctly (exact names)

**No events in PostHog?**
→ Enable telemetry in admin dashboard (/admin/telemetry)

**Want to disable analytics?**
→ Just don't enable telemetry during setup (it's disabled by default)

---

## Privacy Notes

- ✅ Telemetry is **opt-in** (disabled by default)
- ✅ Users can disable anytime
- ✅ No PII ever collected
- ✅ Self-hosted = complete privacy

---

## Full Documentation

- **Setup Guide:** `GITHUB_ACTIONS_SETUP.md`
- **Technical Details:** `README_BUILD_CONFIGURATION.md`
- **Official vs Self-Hosted:** `docs/OFFICIAL_BUILDS.md`
- **Complete Summary:** `BUILD_CONFIGURATION_SUMMARY.md`

---

**That's it!** Your official builds now have analytics configured while respecting user privacy. 🎉

