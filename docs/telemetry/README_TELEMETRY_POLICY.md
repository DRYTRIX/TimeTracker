# Telemetry Policy for TimeTracker

## Quick Summary

- 🔒 **Telemetry is OPT-IN** (disabled by default)
- 🎯 **Analytics keys are embedded** (for consistency across all installations)
- ✅ **You control it** (enable/disable anytime in admin dashboard)
- ❌ **No PII collected** (ever)
- 📖 **Fully transparent** (open source, documented)

## Policy Statement

TimeTracker includes embedded analytics configuration to gather anonymous usage insights that help improve the product. However, **all data collection is strictly opt-in and disabled by default**.

## How It Works

### 1. Build Configuration

Analytics keys (PostHog, Sentry) are embedded during the build process:
- **All builds** (including self-hosted) have the same keys
- Keys cannot be overridden via environment variables
- This ensures consistent telemetry for accurate insights

### 2. User Control

Despite embedded keys, **you have complete control**:

#### Default State
- ✅ Telemetry is **DISABLED** by default
- ✅ No data is sent unless you explicitly enable it
- ✅ You are asked during first-time setup

#### Enabling Telemetry
- You must check a box during setup, OR
- You must toggle it on in Admin → Telemetry Dashboard

#### Disabling Telemetry
- Uncheck during setup, OR
- Toggle off in Admin → Telemetry Dashboard
- Takes effect immediately

### 3. What We Collect

Only if you enable telemetry:

```
✅ Event types: "timer.started", "project.created"
✅ Numeric IDs: user_id=5, project_id=42
✅ Timestamps: When events occurred
✅ Platform info: OS, Python version, app version
✅ Anonymous fingerprint: Hashed installation ID

❌ NO usernames, emails, or real names
❌ NO project names or descriptions
❌ NO time entry content or notes
❌ NO client data or business information
❌ NO IP addresses
❌ NO personally identifiable information
```

## Rationale

### Why Embed Keys?

**Goal:** Understand how TimeTracker is used across all installations to:
1. Prioritize feature development
2. Identify and fix bugs
3. Understand usage patterns
4. Improve user experience

**Why not configurable:**
- Ensures consistent data across all installations
- Prevents fragmented analytics
- Enables accurate community insights
- Still respects privacy through opt-in

### Why This Is Privacy-Respecting

1. **Opt-in by default**: No data sent unless you explicitly enable it
2. **No PII**: We only collect anonymous event types and numeric IDs
3. **User control**: Toggle on/off anytime
4. **Transparent**: All events documented, code is open source
5. **GDPR compliant**: Consent-based, minimization, user rights

## Comparison with Other Software

| Software | Telemetry | User Control | PII Collection |
|----------|-----------|--------------|----------------|
| **TimeTracker** | Opt-in (disabled by default) | Full control via toggle | Never |
| VS Code | Opt-out (enabled by default) | Can disable in settings | Minimal |
| Firefox | Opt-out (enabled by default) | Can disable in settings | Minimal |
| Chrome | Enabled by default | Can disable in settings | Some |
| Ubuntu | Opt-in during install | Can disable | Minimal |

**TimeTracker is MORE privacy-respecting than most mainstream software.**

## Technical Implementation

### Code Locations

All telemetry code is open source and auditable:

```
app/config/analytics_defaults.py  # Configuration (keys embedded here)
app/utils/telemetry.py            # Telemetry logic
app/routes/*.py                   # Event tracking calls
.github/workflows/                # Build process
docs/all_tracked_events.md       # Complete event list
```

### Verification

You can verify what's sent:

```bash
# Check local logs
tail -f logs/app.jsonl | grep event_type

# Inspect network traffic
# Use browser dev tools → Network tab

# Review tracked events
cat docs/all_tracked_events.md
```

### How Opt-Out Works

```python
# In app/utils/telemetry.py
def is_telemetry_enabled():
    # Checks user preference from installation config
    return installation_config.get_telemetry_preference()

# In tracking code
def track_event(user_id, event_name, properties):
    if not is_telemetry_enabled():
        return  # Stop immediately - no data sent
    
    # Only reached if user opted in
    posthog.capture(...)
```

## Your Rights

### 1. Right to Disable
Toggle telemetry off anytime in Admin → Telemetry Dashboard.

### 2. Right to Know
All tracked events are documented in `docs/all_tracked_events.md`.

### 3. Right to Audit
Code is open source - review `app/utils/telemetry.py` and route files.

### 4. Right to Verify
Check `logs/app.jsonl` to see what would be sent.

### 5. Right to Data Deletion
Contact us to request deletion (though data is anonymized and cannot be linked to you).

## FAQ

### Q: Why can't I use my own PostHog/Sentry keys?

**A:** To ensure consistent telemetry across all installations. However, you can disable telemetry entirely for complete privacy.

### Q: Is this spyware?

**A:** No. Spyware collects data without consent or knowledge. TimeTracker:
- Requires explicit opt-in
- Is disabled by default
- Collects no PII
- Is fully transparent (open source)

### Q: What if I want zero telemetry?

**A:** Keep telemetry disabled (the default). Zero data will be sent.

### Q: Can you identify me from the data?

**A:** No. We only collect anonymous event types and numeric IDs. We cannot link data to specific users or installations.

### Q: What about Sentry error reports?

**A:** Sentry error monitoring follows the same opt-in rules as PostHog. Disabled by default.

### Q: Can I build without embedded keys?

**A:** The keys are embedded during the build process. However, they're only used if you opt in. With telemetry disabled, the keys are present but unused.

### Q: Is this GDPR compliant?

**A:** Yes:
- ✅ Consent-based (opt-in)
- ✅ Data minimization (no PII)
- ✅ Right to withdraw (disable anytime)
- ✅ Transparency (documented)

## Data Retention

- **PostHog:** 7 years (industry standard for analytics)
- **Sentry:** 90 days (error logs)
- **Local logs:** Rotated daily, kept 30 days

## Contact & Support

If you have privacy concerns:
- Open an issue on GitHub
- Review: `docs/TELEMETRY_TRANSPARENCY.md`
- Review: `docs/privacy.md`
- Email: [your contact email]

## Changes to This Policy

This policy may be updated as the product evolves. Major changes will be:
- Documented in changelog
- Announced in release notes
- Reflected in this document

---

## Commitment

We are committed to:
- 🔒 **Privacy-first design**
- 📖 **Complete transparency**
- ✅ **User control**
- ❌ **No PII collection**
- ⚖️ **Ethical data practices**

**Your privacy is not negotiable. Your choice is respected.**

---

**Last updated:** October 2025  
**Version:** 3.0.0

