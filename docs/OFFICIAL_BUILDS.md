# Official Builds vs Self-Hosted

TimeTracker supports two deployment models with different analytics configurations.

## Official Builds

Official builds are published on GitHub Container Registry with analytics pre-configured for community support.

### Characteristics

- **Analytics Keys:** PostHog and Sentry keys are embedded at build time
- **Telemetry:** Opt-in during first-time setup (disabled by default)
- **Privacy:** No PII is ever collected, even with telemetry enabled
- **Updates:** Automatic community insights help improve the product
- **Support:** Anonymous usage data helps prioritize features

### Using Official Builds

```bash
# Pull the official image
docker pull ghcr.io/YOUR_USERNAME/timetracker:latest

# Run with default configuration
docker-compose up -d
```

On first access, you'll see the setup page where you can:
- ✅ Enable telemetry to support community development
- ⬜ Disable telemetry for complete privacy (default)

### What Gets Tracked (If Enabled)

- Event types (e.g., "timer.started", "project.created")
- Internal numeric IDs (no usernames or emails)
- Anonymous installation fingerprint
- Platform and version information

### What's NEVER Tracked

- ❌ Email addresses or usernames
- ❌ Project names or descriptions
- ❌ Time entry notes or content
- ❌ Client information or business data
- ❌ IP addresses
- ❌ Any personally identifiable information

## Self-Hosted Builds

Self-hosted builds give you complete control over analytics and telemetry.

### Build Your Own Image

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/timetracker.git
cd timetracker

# Build without embedded keys
docker build -t timetracker:self-hosted .

# Run your build
docker run -p 5000:5000 timetracker:self-hosted
```

### Configuration Options

#### Option 1: No Analytics (Default)
No configuration needed. Analytics placeholders remain empty.

```bash
# Just run it
docker-compose up -d
```

#### Option 2: Your Own Analytics

Provide your own PostHog/Sentry keys:

```bash
# .env file
POSTHOG_API_KEY=your-posthog-key
POSTHOG_HOST=https://your-posthog-instance.com
SENTRY_DSN=your-sentry-dsn
```

#### Option 3: Official Keys (If You Have Them)

If you have the official keys, you can use them:

```bash
export POSTHOG_API_KEY="official-key"
docker-compose up -d
```

## Comparison

| Feature | Official Build | Self-Hosted |
|---------|---------------|-------------|
| Analytics Keys | Embedded | User-provided or none |
| Telemetry Default | Opt-in (disabled) | Opt-in (disabled) |
| Privacy | No PII ever | No PII ever |
| Updates | Via GitHub Releases | Manual builds |
| Support Data | Optional community sharing | Private only |
| Customization | Standard | Full control |

## Transparency & Trust

### Official Build Process

1. **GitHub Actions Trigger:** Tag pushed (e.g., `v3.0.0`)
2. **Placeholder Replacement:** Analytics keys injected from GitHub Secrets
3. **Docker Build:** Image built with embedded keys
4. **Image Push:** Published to GitHub Container Registry
5. **Release Creation:** Changelog and notes generated

### Verification

You can verify the build process:

```bash
# Check if this is an official build
docker run ghcr.io/YOUR_USERNAME/timetracker:latest python3 -c \
  "from app.config.analytics_defaults import is_official_build; \
   print('Official build' if is_official_build() else 'Self-hosted')"
```

### Source Code Availability

All code is open source:
- Analytics configuration: `app/config/analytics_defaults.py`
- Build workflow: `.github/workflows/build-and-publish.yml`
- Telemetry code: `app/utils/telemetry.py`

## Override Priority

Configuration is loaded in this priority order (highest first):

1. **Environment Variables** (user override)
2. **Built-in Defaults** (from GitHub Actions for official builds)
3. **Empty/Disabled** (for self-hosted without config)

This means you can always override official keys with your own:

```bash
# Even in an official build, you can use your own keys
export POSTHOG_API_KEY="my-key"
docker-compose up -d
```

## Privacy Guarantees

### For Official Builds
- ✅ Telemetry is **opt-in** (disabled by default)
- ✅ Can be disabled anytime in admin dashboard
- ✅ No PII is ever collected
- ✅ Open source code for full transparency

### For Self-Hosted
- ✅ Complete control over all analytics
- ✅ Can disable entirely by not providing keys
- ✅ Can use your own PostHog/Sentry instances
- ✅ Same codebase, just without embedded keys

## FAQ

**Q: Will the official build send my data without permission?**
A: No. Telemetry is disabled by default. You must explicitly enable it during setup or in admin settings.

**Q: Can I audit what data is sent?**
A: Yes. All tracked events are documented in `docs/all_tracked_events.md` and logged locally in `logs/app.jsonl`.

**Q: Can I use the official build without telemetry?**
A: Yes! Just leave telemetry disabled during setup. The embedded keys are only used if you opt in.

**Q: What's the difference between official and self-hosted?**
A: Official builds have analytics keys embedded (but still opt-in). Self-hosted builds require you to provide your own keys or run without analytics.

**Q: Can I switch from official to self-hosted?**
A: Yes. Your data is stored locally in the database. Just migrate your `data/` directory and database to a self-hosted instance.

**Q: Are the analytics keys visible in the official build?**
A: They're embedded in the built image (not in source code). This is standard practice for analytics (like mobile apps).

## Building Official Releases

### Prerequisites

1. GitHub repository with Actions enabled
2. GitHub Secrets configured:
   - `POSTHOG_API_KEY`: Your PostHog project API key
   - `SENTRY_DSN`: Your Sentry project DSN

### Release Process

```bash
# Create and push a version tag
git tag v3.0.0
git push origin v3.0.0

# GitHub Actions will automatically:
# 1. Inject analytics keys
# 2. Build Docker image
# 3. Push to GHCR
# 4. Create GitHub Release
```

### Manual Trigger

You can also trigger builds manually:

1. Go to Actions tab in GitHub
2. Select "Build and Publish Official Release"
3. Click "Run workflow"
4. Enter version (e.g., `3.0.0`)
5. Click "Run workflow"

## Support

- **Official Builds:** GitHub Issues, Community Forum
- **Self-Hosted:** GitHub Issues, Documentation
- **Privacy Concerns:** See `docs/privacy.md`
- **Security Issues:** See `SECURITY.md`

---

**Remember:** Whether you use official or self-hosted builds, TimeTracker respects your privacy. Telemetry is always opt-in, transparent, and never collects PII.

