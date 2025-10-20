# Telemetry Transparency Notice

## Overview

TimeTracker includes embedded analytics configuration to help us understand how the software is used and improve it for everyone. **However, telemetry is completely opt-in and disabled by default.**

## Your Control

### Default State: Disabled
When you first access TimeTracker, you'll see a setup page where you can:
- ✅ **Enable telemetry** - Help us improve TimeTracker
- ⬜ **Keep it disabled** - Complete privacy (default choice)

### Change Anytime
You can toggle telemetry on/off at any time:
1. Login as administrator
2. Go to **Admin → Telemetry Dashboard**
3. Click **Enable** or **Disable** button

## What We Collect (Only If You Enable It)

### ✅ What We Track
- **Event types**: e.g., "timer.started", "project.created"
- **Internal numeric IDs**: e.g., user_id=5, project_id=42
- **Timestamps**: When events occurred
- **Platform info**: OS type, Python version, app version
- **Anonymous fingerprint**: Hashed installation ID (cannot identify you)

### ❌ What We NEVER Collect
- Email addresses or usernames
- Project names or descriptions
- Time entry notes or descriptions
- Client names or business information
- IP addresses
- Any personally identifiable information (PII)

## Complete Event List

All tracked events are documented in [`docs/all_tracked_events.md`](./all_tracked_events.md).

Examples:
- `auth.login` - User logged in (only user_id, no username)
- `timer.started` - Timer started (entry_id, project_id)
- `project.created` - Project created (project_id, no project name)
- `task.status_changed` - Task status changed (task_id, old_status, new_status)

## Why Can't I Override the Keys?

Analytics keys are embedded at build time and cannot be overridden for consistency:

### Reasons
1. **Unified insights**: Helps us understand usage across all installations
2. **Feature prioritization**: Shows which features are most used
3. **Bug detection**: Helps identify issues affecting users
4. **Community improvement**: Better product for everyone

### Your Protection
Even with embedded keys:
- ✅ Telemetry is **disabled by default**
- ✅ You must **explicitly opt-in**
- ✅ You can **disable anytime**
- ✅ **No PII** is ever collected
- ✅ **Open source** - you can audit the code

## Technical Details

### How Keys Are Embedded

During the build process, GitHub Actions replaces placeholders:
```python
# Before build (in source code)
POSTHOG_API_KEY_DEFAULT = "%%POSTHOG_API_KEY_PLACEHOLDER%%"

# After build (in Docker image)
POSTHOG_API_KEY_DEFAULT = "phc_abc123..."  # Real key
```

### No Environment Override

Unlike typical configurations, these keys cannot be overridden via environment variables:
```bash
# This will NOT work (intentionally)
export POSTHOG_API_KEY="my-key"

# Telemetry control is via the admin dashboard toggle only
```

### Code Location

All analytics code is open source:
- Configuration: [`app/config/analytics_defaults.py`](../app/config/analytics_defaults.py)
- Telemetry logic: [`app/utils/telemetry.py`](../app/utils/telemetry.py)
- Event tracking: Search for `log_event` and `track_event` in route files
- Build process: [`.github/workflows/build-and-publish.yml`](../.github/workflows/build-and-publish.yml)

## Data Flow

### When Telemetry is Enabled

```
User Action (e.g., start timer)
    ↓
Application code calls track_event()
    ↓
Check: Is telemetry enabled?
    ├─ No → Stop (do nothing)
    └─ Yes → Continue
         ↓
    Add context (no PII)
    ↓
    Send to PostHog
    ↓
    Also log locally (logs/app.jsonl)
```

### When Telemetry is Disabled

```
User Action (e.g., start timer)
    ↓
Application code calls track_event()
    ↓
Check: Is telemetry enabled?
    └─ No → Stop immediately
    
No data sent anywhere.
Only local logging (for debugging).
```

## Privacy Compliance

### GDPR Compliance
- ✅ **Consent-based**: Explicit opt-in required
- ✅ **Right to withdraw**: Can disable anytime
- ✅ **Data minimization**: Only collect what's necessary
- ✅ **No PII**: Cannot identify individuals
- ✅ **Transparency**: Fully documented

### Your Rights
1. **Right to disable**: Toggle off anytime
2. **Right to know**: All events documented
3. **Right to audit**: Open source code
4. **Right to verify**: Check logs locally

## Frequently Asked Questions

### Q: Why embed keys instead of making them configurable?
**A:** To ensure consistent telemetry across all installations, helping us improve the product for everyone. However, you maintain full control via the opt-in toggle.

### Q: Can you track me personally?
**A:** No. We only collect event types and numeric IDs. We cannot identify users, see project names, or access any business data.

### Q: What if I want complete privacy?
**A:** Simply keep telemetry disabled (the default). No data will be sent to our servers.

### Q: Can I audit what's being sent?
**A:** Yes! Check `logs/app.jsonl` to see all events logged locally. The code is also open source for full transparency.

### Q: What happens to my data?
**A:** Data is stored in PostHog (privacy-focused analytics) and Sentry (error monitoring). Both are GDPR-compliant services.

### Q: Can I self-host analytics?
**A:** The keys are embedded, so you cannot use your own PostHog/Sentry instances. However, you can disable telemetry entirely for complete privacy.

### Q: How long is data retained?
**A:** PostHog: 7 years (configurable). Sentry: 90 days. Both follow data retention best practices.

### Q: Can I see what data you have about me?
**A:** Since we only collect anonymous numeric IDs, we cannot associate data with specific users. All data is anonymized by design.

## Trust & Transparency

### Our Commitment
- 🔒 **Privacy-first**: Opt-in, no PII, user control
- 📖 **Transparent**: Open source, documented events
- 🎯 **Purpose-driven**: Only collect what helps improve the product
- ⚖️ **Ethical**: Respect user choices and privacy

### Verification
You can verify our claims:
1. **Read the code**: All analytics code is in the repository
2. **Check the logs**: Events logged locally in `logs/app.jsonl`
3. **Inspect network**: Use browser dev tools to see what's sent
4. **Review events**: Complete list in `docs/all_tracked_events.md`

## Contact

If you have privacy concerns or questions:
- Open an issue on GitHub
- Review the privacy policy: [`docs/privacy.md`](./privacy.md)
- Check all tracked events: [`docs/all_tracked_events.md`](./all_tracked_events.md)

---

## Summary

✅ **Telemetry is OPT-IN** (disabled by default)  
✅ **You control it** (enable/disable anytime)  
✅ **No PII collected** (ever)  
✅ **Fully transparent** (open source, documented)  
✅ **GDPR compliant** (consent, minimization, rights)  

**Your privacy is respected. Your choice is honored.**

