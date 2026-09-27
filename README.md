# TimeTracker

<div align="center">

<img src="app/static/images/timetracker-logo.svg" alt="TimeTracker" width="120">

### Self-hosted time tracking, invoicing and Peppol e-invoicing for freelancers and teams — with no per-seat fees.

[![GitHub stars](https://img.shields.io/github/stars/drytrix/TimeTracker?style=social)](https://github.com/drytrix/TimeTracker)
[![Docker Pulls](https://img.shields.io/docker/pulls/drytrix/timetracker)](https://hub.docker.com/r/drytrix/timetracker)
[![Latest Release](https://img.shields.io/github/v/release/drytrix/TimeTracker)](https://github.com/drytrix/TimeTracker/releases/latest)
[![License: GPL-3.0](https://img.shields.io/github/license/drytrix/TimeTracker)](LICENSE)

<img src="assets/screenshots/Dashboard.png" alt="TimeTracker Dashboard" width="800">

**[Live demo](https://timetracker-demo.drytrix.com)** · **[Website](https://timetracker.drytrix.com)** · **[Docs](docs/README.md)** · **[Changelog](CHANGELOG.md)**

</div>

---

## Quick start (60 seconds)

No git clone, no certificate warning — plain HTTP on port 8080 with bundled PostgreSQL:

```bash
curl -fsSLO https://raw.githubusercontent.com/drytrix/TimeTracker/main/docker-compose.nas.yml
echo "SECRET_KEY=$(openssl rand -hex 32)" > .env
docker compose -f docker-compose.nas.yml up -d
# open http://localhost:8080 — first login creates the admin
```

**Latest release: v5.17.2** — see [CHANGELOG.md](CHANGELOG.md).

More install paths (HTTPS production, NAS UI paste, cloud): [Install options](#install-options).

---

## Why TimeTracker?

- **Peppol & EN 16931 e-invoicing** — Send invoices yourself via the bundled [Peppol Bridge](docs/admin/configuration/PEPPOL_BRIDGE.md); embed Factur-X / ZUGFeRD XML in PDFs. No paid SaaS middleman for e-invoicing.
- **Self-hosted** — Your timers, clients, and invoices stay on your server (Docker, NAS, VPS, or Raspberry Pi).
- **GPL-3.0 open source** — Free to use, modify, and run commercially; features are never locked behind a paywall.
- **No per-user pricing** — Unlimited users and projects; optional one-time supporter key only hides donate prompts.

| Feature | TimeTracker | Traditional Time Trackers |
|---------|-------------|---------------------------|
| **Self-Hosted** | ✅ Complete data control | ❌ Cloud-only, subscription fees |
| **Open Source** | ✅ Free to use & modify | ❌ Proprietary, locked features |
| **Persistent Timers** | ✅ Runs server-side | ❌ Browser-dependent |
| **Docker Ready** | ✅ Deploy anywhere | ⚠️ Complex setup |
| **Invoicing Built-in** | ✅ Track to bill workflow | ❌ Requires integration |
| **No User Limits** | ✅ Unlimited users | ❌ Per-user pricing |

---

## What is TimeTracker?

TimeTracker is a **self-hosted, web-based time tracking application** designed for freelancers, teams, and businesses who need professional time management with complete control over their data.

**Perfect for:**
- **Freelancers** tracking billable hours across multiple clients
- **Small Teams** managing projects and tracking productivity
- **Agencies** needing detailed reporting and client billing
- **Privacy-focused organizations** wanting self-hosted solutions

UI layout and navigation conventions: [UI Guidelines](docs/UI_GUIDELINES.md).

---

## ✨ Features

TimeTracker includes **130+ features** across 13 major categories. See the [Complete Features Documentation](docs/FEATURES_COMPLETE.md) for a comprehensive overview.

**📖 Quick Links:**
- [📋 Complete Features List](docs/FEATURES_COMPLETE.md) — All features in detail
- [⏱️ Time Tracking](docs/FEATURES_COMPLETE.md#time-tracking-features) — Timer and time entry features
- [📊 Project Management](docs/FEATURES_COMPLETE.md#project-management) — Projects, tasks, and organization
- [🧾 Invoicing](docs/INVOICE_FEATURE_README.md) — Invoice generation and billing
- [💰 Financial Management](docs/FEATURES_COMPLETE.md#financial-management) — Expenses, payments, and tracking
- [📈 Reporting & Analytics](docs/FEATURES_COMPLETE.md#reporting--analytics) — Reports and insights

### ⏱️ **Smart Time Tracking**
- **One-Click Timers** — Start tracking with a single click
- **Persistent Timers** — Timers keep running even after browser closes
- **Idle Detection** — Automatic pause after configurable idle time
- **Manual Entry** — Add historical time entries with notes and tags
- **Bulk Time Entry** — Create multiple entries for consecutive days with weekend skipping ([Guide](docs/BULK_TIME_ENTRY_README.md))
- **Time Entry Templates** — Save and reuse common time entries for faster logging ([Guide](docs/TIME_ENTRY_TEMPLATES.md))
- **Calendar View** — Visual calendar interface for viewing and managing time entries ([Guide](docs/CALENDAR_FEATURES_README.md))
- **Focus Sessions** — Pomodoro-style focus session tracking
- **Recurring Time Blocks** — Weekly recurring time block templates
- **Time Rounding** — Configurable rounding intervals ([Guide](docs/TIME_ROUNDING_PREFERENCES.md))
- **Real-time Updates** — See live timer updates across all devices via WebSocket

### 📊 **Project & Task Management**
- **Unlimited Projects & Tasks** — Organize work your way
- **Client Management** — Store client details, contacts, and billing rates ([Guide](docs/CLIENT_MANAGEMENT_README.md))
- **Task Board** — Visual task management with priorities and assignments
- **Kanban Board** — Drag-and-drop task management with customizable columns
- **Task Management** — Complete task tracking system ([Guide](docs/TASK_MANAGEMENT_README.md))
- **Issue & Bug Tracking** — Full lifecycle issue and bug tracking system
- **Status Tracking** — Monitor progress from to-do to completion
- **Budget Tracking** — Monitor project budgets with alerts and forecasting ([Guide](docs/BUDGET_ALERTS_AND_FORECASTING.md))
- **Project Costs** — Track direct project expenses
- **Task Comments** — Collaborate with threaded comments on tasks
- **Markdown Support** — Rich text formatting in project and task descriptions
- **Project Favorites** — Quick access to frequently used projects

### 💼 **CRM & Sales Management** 🆕
- **Multiple Contacts per Client** — Manage unlimited contacts with roles and designations
- **Sales Pipeline** — Visual Kanban-style pipeline for tracking deals and opportunities
- **Deal Management** — Track deal value, probability, stages, and expected close dates
- **Lead Management** — Capture, score, and convert leads into clients or deals
- **Communication History** — Track all emails, calls, meetings, and notes with contacts
- **Deal Activities** — Complete activity tracking for sales processes
- **Lead Activities** — Track all interactions and activities for leads
- **Lead Scoring** — Automated lead scoring (0-100) for prioritization
- **Lead Conversion** — Convert leads to clients or deals with one click

### 🧾 **Professional Invoicing**
- **Generate from Time** — Convert tracked hours to invoices automatically
- **Invoice System** — Complete invoicing solution ([Guide](docs/INVOICE_FEATURE_README.md))
- **Custom Line Items** — Add manual items for expenses or services
- **Tax Calculation** — Automatic tax calculations with configurable rates
- **PDF Export** — Professional PDF invoice generation with customizable layouts
- **PDF Invoice Layout** — Customize invoice and quote PDF layouts via Admin > PDF Layout; Items table includes time entries, extra goods, and expenses ([Guide](docs/PDF_LAYOUT_CUSTOMIZATION.md), [Extra Goods in PDF](docs/INVOICE_EXTRA_GOODS_PDF_EXPORT.md))
- **Status Tracking** — Track draft, sent, paid, and overdue invoices
- **Company Branding** — Add logos and custom company information
- **Expense Integration** — Include tracked expenses in invoices
- **Recurring Invoices** — Automate recurring billing
- **Multi-Currency** — Support for multiple currencies with conversion
- **Invoice Email** — Send invoices directly to clients
- **Peppol & ZugFerd e-Invoicing (EN 16931)** — Send via Peppol (generic or native); embed EN 16931 XML in PDFs (ZugFerd/Factur-X); optional PDF/A-3 and veraPDF ([Setup Guide](docs/admin/configuration/PEPPOL_EINVOICING.md))

### 💰 **Financial Management**
- **Expense Tracking** — Track business expenses with receipts and categories ([Guide](docs/EXPENSE_TRACKING.md))
- **Payment Tracking** — Monitor invoice payments and payment methods ([Guide](docs/PAYMENT_TRACKING.md))
- **Reimbursement Management** — Handle expense approvals and reimbursements
- **Billable Expenses** — Mark expenses as billable and add to invoices
- **Payment Gateway Integration** — Track gateway transactions and fees
- **Mileage Tracking** — Track business mileage with rate calculation
- **Per Diem Tracking** — Manage per diem expenses and rates
- **Multi-Currency** — Support for multiple currencies with conversion

### 📈 **Analytics & Reporting**
- **Visual Dashboards** — Charts and graphs for quick insights; dashboard includes **time-by-project chart (last 7 days)** and **weekly goal progress bar**
- **Summary Report** — Today/week/month hours with **time-by-project** and **daily trend (14 days)** charts; **export summary as PDF**
- **Detailed Reports** — Time breakdown by project, user, or date range
- **CSV Export** — Export data for external analysis
- **Billable vs Non-billable** — Separate tracking for accurate billing
- **Custom Date Ranges** — Flexible reporting periods
- **Saved Filters** — Save frequently used report filters for quick access
- **User Analytics** — Individual performance metrics and productivity insights
- **Budget Alerts** — Automatic alerts when budget thresholds are exceeded ([Guide](docs/BUDGET_ALERTS_AND_FORECASTING.md))
- **Budget Forecasting** — Predict project completion dates based on burn rates
- **Weekly Time Goals** — Set and track weekly hour targets ([Guide](docs/WEEKLY_TIME_GOALS.md))
- **Overtime Tracking** — Monitor and report overtime hours

### 🔐 **Multi-User & Security**
- **Role-Based Access Control** — Granular permissions system with custom roles ([Guide](docs/ADVANCED_PERMISSIONS.md))
- **User Management** — Add team members and manage access
- **Self-Hosted** — Complete control over your data
- **Flexible Authentication** — Username-only, OIDC/SSO (Azure AD, Authelia, etc.) ([Setup Guide](docs/admin/configuration/OIDC_SETUP.md))
- **Session Management** — Secure cookies and session handling
- **Profile Pictures** — Users can upload profile pictures
- **API Tokens** — Generate tokens for API access and integrations ([API Docs](docs/api/REST_API.md))
- **Audit Logs** — Track all system activity and user actions

### ⌨️ **Productivity Features**
- **Command Palette** — Keyboard-driven navigation with shortcuts (Ctrl+K / Cmd+K) ([Guide](docs/COMMAND_PALETTE_USAGE.md))
- **Keyboard Shortcuts** — 50+ shortcuts for lightning-fast navigation and actions
- **Quick Search** — Enhanced instant search with autocomplete and categorized results (Ctrl+K)
- **Floating quick hub** — Bottom-right dock: unified Actions menu (timer, log time, new task/project/client, reports), optional team chat toggle with a fixed viewport panel, and AI Helper; see [UI guidelines](docs/UI_GUIDELINES.md#floating-hub-authenticated-layout)
- **Enhanced Data Tables** — Sortable, filterable, inline-editable tables with bulk operations
- **Email Notifications** — Configurable email alerts for tasks, invoices, and more
- **Toast Notifications** — Beautiful in-app notifications; **post-timer toast** shows "Logged Xh on Project" with link to time entries
- **Weekly Summaries** — Optional weekly time tracking summaries via email (enable in Settings)
- **Remind to Log** — Optional end-of-day email reminder to log time (Settings → Remind me to log time at end of day; set time in your timezone)
- **Activity Feed** — Track recent activity across the system
- **Saved Filters** — Save frequently used report filters for quick access
- **Recently Viewed** — Quick access to recently viewed items
- **Favorites System** — Mark frequently used projects, clients, and tasks as favorites

### 🛠️ **Technical Excellence**
- **Docker Ready** — Deploy in minutes with Docker Compose
- **Database Flexibility** — PostgreSQL for production, SQLite for testing
- **Responsive Design** — Mobile-first design works perfectly on desktop, tablet, and mobile
- **Native Mobile & Desktop Apps** — Flutter mobile app (iOS/Android) and Electron desktop app with time tracking, offline support, and API integration ([Build Guide](scripts/README-BUILD.md), [Docs](docs/mobile-desktop-apps/README.md))
- **Real-time Sync** — WebSocket support for live updates across devices
- **Automatic Backups** — Scheduled database backups (configurable)
- **Progressive Web App (PWA)** — Install as mobile app with offline support and background sync
- **Monitoring Stack** — Built-in Prometheus, Grafana, Loki for observability
- **Internationalization** — Multiple language support (i18n) with translation system
- **REST API** — Comprehensive REST API with token authentication and scoping
- **HTTPS Support** — Automatic HTTPS setup with self-signed or trusted certificates
- **Modern Architecture** — Service layer pattern, repository pattern, schema validation
- **Performance Optimized** — Query optimization, eager loading, reduced N+1 queries
- **Accessibility** — WCAG 2.1 AA compliant with full keyboard navigation and screen reader support

---

---

## 📸 Screenshots

<div align="center">

### 🔐 Simple Login & User Management
<div>
  <img src="assets/screenshots/Login.png" alt="Login" width="45%" style="display: inline-block; margin: 5px;">
  <img src="assets/screenshots/Profile.png" alt="Profile" width="45%" style="display: inline-block; margin: 5px;">
</div>

*Simple username-based authentication and customizable user profiles with avatar support*

---

### 📁 Projects & Tasks — Stay Organized
<div>
  <img src="assets/screenshots/Projects.png" alt="Projects" width="45%" style="display: inline-block; margin: 5px;">
  <img src="assets/screenshots/Tasks.png" alt="Tasks" width="45%" style="display: inline-block; margin: 5px;">
</div>

*Manage multiple projects and break them down into actionable tasks*

---

### 📋 Kanban Board — Visual Task Management
<img src="assets/screenshots/Kanban.png" alt="Kanban Board" width="700">

*Drag-and-drop task management with customizable columns and visual workflow*

---

### ⏱️ Time Tracking — Flexible & Powerful
<div>
  <img src="assets/screenshots/LogTime.png" alt="Log Time" width="45%" style="display: inline-block; margin: 5px;">
  <img src="assets/screenshots/TimeEntryTemplates.png" alt="Time Entry Templates" width="45%" style="display: inline-block; margin: 5px;">
</div>

*Manual time entry and reusable templates for faster logging*

---

### 🧾 Invoicing & Clients — Professional Billing
<div>
  <img src="assets/screenshots/Invoices.png" alt="Invoices" width="45%" style="display: inline-block; margin: 5px;">
  <img src="assets/screenshots/Clients.png" alt="Client Management" width="45%" style="display: inline-block; margin: 5px;">
</div>

*Generate invoices from tracked time and manage client relationships*

---

### 📊 Reports & Analytics — Data-Driven Insights
<div>
  <img src="assets/screenshots/Reports.png" alt="Reports" width="45%" style="display: inline-block; margin: 5px;">
  <img src="assets/screenshots/UserReports.png" alt="User Reports" width="45%" style="display: inline-block; margin: 5px;">
</div>

*Comprehensive reporting and user analytics for informed decisions*

---

### 🛠️ Admin Dashboard — Complete Control
<img src="assets/screenshots/AdminDashboard.png" alt="Admin Dashboard" width="700">

*Manage users, configure settings, and monitor system health*

---

### 🎯 Easy Creation — Streamlined Workflows
<div>
  <img src="assets/screenshots/CreateProject.png" alt="Create Project" width="30%" style="display: inline-block; margin: 5px;">
  <img src="assets/screenshots/CreateTask.png" alt="Create Task" width="30%" style="display: inline-block; margin: 5px;">
  <img src="assets/screenshots/CreateClient.png" alt="Create Client" width="30%" style="display: inline-block; margin: 5px;">
</div>

*Simple, intuitive forms for creating projects, tasks, and clients*

</div>

---

## Install options

| Method | Best for | Get started |
|--------|----------|-------------|
| **One-command (above)** | Homelab, quick try | `docker-compose.nas.yml` + `SECRET_KEY` |
| **Docker image** | Servers, VPS | `docker pull ghcr.io/drytrix/timetracker:latest` or [Docker Hub](https://hub.docker.com/r/drytrix/timetracker) |
| **NAS compose** | QNAP, Synology, Portainer | Paste [`docker-compose.nas.yml`](docker-compose.nas.yml) — [NAS guide](docs/admin/deployment/NAS_DEPLOYMENT.md) |
| **GitHub Release** | Compose files + desktop/mobile | [Releases](https://github.com/drytrix/TimeTracker/releases) |
| **Cloud (Render)** | Managed hosting | [![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/drytrix/TimeTracker) |

**Full list of install paths:** [Distribution Guide](docs/admin/deployment/DISTRIBUTION.md) (Portainer templates, Unraid, Railway, Fly.io, Coolify, [Docker Hub](https://hub.docker.com/r/drytrix/timetracker))

> **Docker Hub namespace:** images are published at [`drytrix/timetracker`](https://hub.docker.com/r/drytrix/timetracker) (formerly `driesp/timetracker`).

For a full step-by-step guide, see **[INSTALLATION.md](INSTALLATION.md)**.

### Prerequisites

- **Docker** (20.10+) and **Docker Compose** (2.0+)
- **2GB+ RAM** available for Docker containers
- **Port 8080** (HTTP) or **80/443** (HTTPS production)

> **New to Docker?** See [Docker Installation Guide](https://docs.docker.com/get-docker/) for your platform.

### Option 1: NAS / one-file compose (recommended for first try)

Same stack as [Quick start](#quick-start-60-seconds). Paste [`docker-compose.nas.yml`](docker-compose.nas.yml) into Container Station, Synology Container Manager, or Portainer; set `SECRET_KEY`; open `http://<host>:8080`.

Works on **QNAP**, **Synology**, **Unraid/Portainer**, and other Docker-capable NAS devices (amd64 and arm64).

**Full guide:** [NAS Deployment Guide](docs/admin/deployment/NAS_DEPLOYMENT.md)

### Option 2: Production with HTTPS

Clone the repo and use the root compose file (nginx + self-signed cert):

```bash
git clone https://github.com/drytrix/TimeTracker.git
cd TimeTracker
cp env.example .env
# Set a strong SECRET_KEY, TZ, and CURRENCY in .env
docker compose up -d
# Access at https://localhost — accept the self-signed certificate warning
```

**First login creates the admin account.** For setup problems, see [INSTALLATION.md](INSTALLATION.md).

**Default install (no bundled AI):** the main `docker-compose.yml` starts the app and PostgreSQL only. Optional Ollama: see [AI Helper](#ai-helper-ollama-or-hosted).

**Complete setup guide:** [`docs/admin/configuration/DOCKER_COMPOSE_SETUP.md`](docs/admin/configuration/DOCKER_COMPOSE_SETUP.md) · **Uninstall:** [UNINSTALL.md](UNINSTALL.md)

**Troubleshooting:** [Docker Startup](docs/admin/configuration/DOCKER_STARTUP_TROUBLESHOOTING.md) · [CSRF](docs/admin/security/CSRF_TROUBLESHOOTING.md) · [Database](docker/TROUBLESHOOTING_DB_CONNECTION.md)

### Option 3: Docker with plain HTTP (development)

```bash
git clone https://github.com/drytrix/TimeTracker.git
cd TimeTracker
docker compose -f docker-compose.example.yml up -d
# Access at http://localhost:8080
```

### Option 4: Quick test with SQLite

```bash
git clone https://github.com/drytrix/TimeTracker.git
cd TimeTracker
docker compose -f docker/docker-compose.local-test.yml up --build
# Access at http://localhost:8080
```

No PostgreSQL or `.env` required. SQLite is not recommended for production.

**Need help?** [Getting Started Guide](docs/GETTING_STARTED.md)

---

## 💻 System Requirements

### Minimum Requirements

**For Small Teams (1-5 users):**
- **CPU**: 1 core (2.0 GHz+)
- **RAM**: 2 GB
- **Storage**: 10 GB free space
- **OS**: Linux, macOS, or Windows (with Docker)
- **Docker**: 20.10+ and Docker Compose 2.0+

**For Production (5+ users):**
- **CPU**: 2+ cores (2.4 GHz+)
- **RAM**: 4 GB
- **Storage**: 20 GB free space (SSD recommended)
- **OS**: Linux (Ubuntu 20.04+, Debian 11+, or similar)
- **Docker**: 20.10+ and Docker Compose 2.0+
- **PostgreSQL**: 13+ (included in Docker Compose)

### Recommended Requirements

**For Optimal Performance:**
- **CPU**: 4+ cores (3.0 GHz+)
- **RAM**: 8 GB
- **Storage**: 50+ GB SSD
- **Network**: Stable internet connection (for updates and optional telemetry)
- **Backup**: Automated backup solution for database

### Platform Support

- ✅ **Linux** (Ubuntu, Debian, CentOS, RHEL, etc.)
- ✅ **macOS** (Intel and Apple Silicon)
- ✅ **Windows** (Windows 10/11 with WSL2 or Docker Desktop)
- ✅ **Raspberry Pi** (Raspberry Pi 4 with 2GB+ RAM)
- ✅ **Cloud Platforms** (AWS, Azure, GCP, DigitalOcean, etc.)

### Database Options

- **PostgreSQL** (Recommended for production)
  - Version 13+ required
  - Included in Docker Compose setup
  - Supports all features including full-text search

- **SQLite** (Development/Testing only)
  - No setup required
  - Suitable for single-user or testing
  - Limited concurrent write performance

### Browser Support

TimeTracker works with all modern browsers:
- ✅ Chrome/Edge 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Opera 76+

**📖 For detailed requirements, see [Requirements Documentation](docs/REQUIREMENTS.md)**

---

## 💡 Use Cases

### For Freelancers
Track time across multiple client projects, generate professional invoices, and understand where your time goes. TimeTracker helps you bill accurately and identify your most profitable clients.

### For Teams
Assign tasks, track team productivity, and generate reports for stakeholders. See who's working on what, identify bottlenecks, and optimize team performance.

### For Agencies
Manage multiple clients and projects simultaneously. Track billable hours, generate client invoices, and analyze project profitability — all in one place.

### For Personal Projects
Even if you're not billing anyone, understanding where your time goes is valuable. Track personal projects, hobbies, and learning activities to optimize your time.

---

## 📚 Documentation

Comprehensive documentation is available in the [`docs/`](docs/) directory. See the [Documentation Index](docs/README.md) for a complete overview.

### 📖 Documentation by Use Case

**For New Users:**
- **[Getting Started Guide](docs/GETTING_STARTED.md)** — Complete beginner's tutorial (⭐ Start here!)
- **[Installation Guide](INSTALLATION.md)** — Step-by-step installation (Docker, SQLite test)
- **[Docker Public Setup](docs/admin/configuration/DOCKER_PUBLIC_SETUP.md)** — Production deployment
- **[Quick Start Guide](docs/guides/QUICK_START_GUIDE.md)** — Get up and running quickly

**For Administrators:**
- **[Docker Compose Setup](docs/admin/configuration/DOCKER_COMPOSE_SETUP.md)** — Production deployment guide
- **[Configuration Guide](docs/admin/configuration/DOCKER_COMPOSE_SETUP.md)** — All configuration options
- **[Uninstall / remove data](UNINSTALL.md)** — Tear down Docker, volumes, and optional AI (Ollama); [AI helper only](UNINSTALL.md#disabling-or-removing-the-ai-helper)
- **[OIDC/SSO Setup](docs/admin/configuration/OIDC_SETUP.md)** — Enterprise authentication
- **[Email Configuration](docs/admin/configuration/EMAIL_CONFIGURATION.md)** — Email setup
- **[Version Management](docs/admin/deployment/VERSION_MANAGEMENT.md)** — Updates and releases

**For Developers:**
- **[Contributing](CONTRIBUTING.md)** — How to contribute (quick link)
- **[Contributing Guidelines (full)](docs/development/CONTRIBUTING.md)** — Setup, standards, PR process
- **[Development Guide](docs/DEVELOPMENT.md)** — Run locally, test, release process
- **[Architecture](docs/ARCHITECTURE.md)** — System overview and design
- **[Project Structure](docs/development/PROJECT_STRUCTURE.md)** — Codebase layout
- **[API Documentation](docs/API.md)** — API quick reference · [Full REST API](docs/api/REST_API.md)
- **[Database Migrations](migrations/README.md)** — Schema management
- **[CI/CD Documentation](docs/cicd/CI_CD_DOCUMENTATION.md)** — Build and deployment

**For Troubleshooting:**
- **[Docker Startup Issues](docs/admin/configuration/DOCKER_STARTUP_TROUBLESHOOTING.md)** — Common startup problems
- **[CSRF Token Issues](docs/admin/security/CSRF_TROUBLESHOOTING.md)** — Fix CSRF errors
- **[Database Connection](docker/TROUBLESHOOTING_DB_CONNECTION.md)** — Database issues
- **[Solution Guide](docs/SOLUTION_GUIDE.md)** — General problem solving

### 🎯 Feature Documentation

**Core Features:**
- **[📋 Complete Features Overview](docs/FEATURES_COMPLETE.md)** — All 130+ features (⭐ Complete reference!)
- **[Time Tracking](docs/FEATURES_COMPLETE.md#time-tracking-features)** — Timer and entry features
- **[Task Management](docs/TASK_MANAGEMENT_README.md)** — Task tracking system
- **[Client Management](docs/CLIENT_MANAGEMENT_README.md)** — Client relationships
- **[Invoice System](docs/INVOICE_FEATURE_README.md)** — Invoice generation

**Advanced Features:**
- **[Calendar & Bulk Entry](docs/CALENDAR_FEATURES_README.md)** — Calendar view and bulk operations
- **[Bulk Time Entry](docs/BULK_TIME_ENTRY_README.md)** — Create multiple entries
- **[Time Entry Templates](docs/TIME_ENTRY_TEMPLATES.md)** — Reusable templates
- **[Expense Tracking](docs/EXPENSE_TRACKING.md)** — Business expenses
- **[Payment Tracking](docs/PAYMENT_TRACKING.md)** — Invoice payments
- **[Budget Alerts & Forecasting](docs/BUDGET_ALERTS_AND_FORECASTING.md)** — Budget monitoring
- **[Weekly Time Goals](docs/WEEKLY_TIME_GOALS.md)** — Weekly targets

**Productivity:**
- **[Command Palette](docs/COMMAND_PALETTE_USAGE.md)** — Keyboard shortcuts
- **[Role-Based Permissions](docs/ADVANCED_PERMISSIONS.md)** — Access control
- **[Multiple instances (independent companies)](docs/MULTI_INSTANCE_SETUP.md)** — One deployment per company

**Integrations & Apps:**
- **[Mobile & Desktop Apps](docs/mobile-desktop-apps/README.md)** — Flutter mobile and Electron desktop apps
- **[Build Guide (Mobile & Desktop)](scripts/README-BUILD.md)** — Build scripts for Android, iOS, Windows, macOS, Linux
- **[Peppol & ZugFerd e-Invoicing](docs/admin/configuration/PEPPOL_EINVOICING.md)** — Peppol sending and ZugFerd/Factur-X PDF embedding (EN 16931)
- **[API Documentation](docs/api/REST_API.md)** — REST API reference
- **[API Token Scopes](docs/api/API_TOKEN_SCOPES.md)** — Token permissions

### 🔧 Technical Documentation

- **[Project Structure](docs/development/PROJECT_STRUCTURE.md)** — Codebase architecture
- **[Database Migrations](migrations/README.md)** — Schema management
- **[Version Management](docs/admin/deployment/VERSION_MANAGEMENT.md)** — Release process
- **[CSRF Configuration](docs/admin/security/CSRF_CONFIGURATION.md)** — Security setup
- **[CI/CD Setup](docs/cicd/CI_CD_DOCUMENTATION.md)** — Continuous integration

### 🔒 Security & Configuration

- **[HTTPS Setup (Auto)](docs/admin/security/README_HTTPS_AUTO.md)** — Automatic HTTPS
- **[HTTPS Setup (mkcert)](docs/admin/security/README_HTTPS.md)** — Manual HTTPS
- **[CSRF Troubleshooting](docs/admin/security/CSRF_TROUBLESHOOTING.md)** — CSRF issues
- **[CSRF IP Access Fix](docs/admin/security/CSRF_IP_ACCESS_FIX.md)** — IP access issues
- **[OIDC/SSO Setup](docs/admin/configuration/OIDC_SETUP.md)** — Enterprise auth

### 🤝 Contributing

- **[Contributing Guidelines](docs/development/CONTRIBUTING.md)** — How to contribute
- **[Code of Conduct](docs/development/CODE_OF_CONDUCT.md)** — Community standards
- **[Development Setup](docs/development/LOCAL_TESTING_WITH_SQLITE.md)** — Local development

### 📋 Reference

- **[📋 Changelog](CHANGELOG.md)** — Complete release history (⭐ See what's new!)
- **[Requirements](docs/REQUIREMENTS.md)** — System requirements
- **[Documentation Index](docs/README.md)** — Complete documentation overview

---

## 🐳 Deployment

### Local Development
```bash
# Start with HTTPS (recommended)
docker-compose up -d

# Or use plain HTTP for development
docker-compose -f docker-compose.example.yml up -d
```

### Production Deployment

#### Option 1: Build from Source
```bash
# Clone the repository
git clone https://github.com/drytrix/TimeTracker.git
cd TimeTracker

# Configure your .env file
cp env.example .env
# Edit .env with production settings:
# - Set a strong SECRET_KEY: python -c "import secrets; print(secrets.token_hex(32))"
# - Configure TZ (timezone) and CURRENCY
# - Set PostgreSQL credentials (POSTGRES_PASSWORD, etc.)

# Start the application
docker-compose up -d
```

#### Option 2: Use Pre-built Images
```bash
# Use the remote compose file with published images
docker-compose -f docker/docker-compose.remote.yml up -d
```

> **⚠️ Security Note:** Always set a unique `SECRET_KEY` in production! See [CSRF Configuration](docs/admin/security/CSRF_CONFIGURATION.md) for details.

## AI Helper (Ollama or hosted)

TimeTracker includes an optional **server-side AI helper** for the web app and API clients. **New installs default to AI off** (`AI_ENABLED=false` in `env.example` and in the root `docker-compose.yml` app service) so time tracking works without downloading a large language model.

- **Enable (any setup)**: set `AI_ENABLED=true` (environment or **Admin → System Settings → AI Helper**).
- **Ollama**: set `AI_PROVIDER=ollama`, `AI_MODEL=...`, and `AI_BASE_URL` to `http://ollama:11434` when Ollama runs in Docker on the same Compose network, or `http://127.0.0.1:11434` when Ollama runs on the host.
- **Hosted OpenAI-compatible**: set `AI_PROVIDER=openai_compatible` and `AI_API_KEY=...`

The AI helper is exposed as:

- Session web UI JSON: `POST /api/ai/chat` (same-origin, login required)
- REST API v1: `POST /api/v1/ai/chat` (API token required, scopes `read:ai`/`write:ai`)

**Time entry suggestions** (when `AI_ENABLED=true`):

- `GET /api/ai/suggest` — deterministic suggestions from recent patterns and active tasks; optional `?q=` filters by notes/project name; `?rich=true` merges LLM suggestions when configured. AI failures return deterministic results only.
- **Start Timer** modal: horizontal suggestion chips above the project field (refresh for LLM-enhanced suggestions).
- **Log Time** form: “✦ Autofill” popover and ghost-text autocomplete on the notes field (`app/static/js/ai_autocomplete.js`).

All suggestion UI is hidden when AI is disabled (`ai_enabled` in template context).

### Bundled Ollama service (Docker Compose, opt-in)

The root `docker-compose.yml` defines a CPU-only **`ollama`** service and a one-shot **`ollama-init`** sidecar that pulls `AI_MODEL` (default `llama3.1`, ~4.7 GB) into the `ollama_data` volume. These services use the Compose **`ai`** profile so they **do not start by default**.

**Enable bundled Ollama:**

1. In `.env`, set `AI_ENABLED=true`, `AI_PROVIDER=ollama`, `AI_BASE_URL=http://ollama:11434`, and your desired `AI_MODEL`.
2. Start the stack with the profile:

   ```bash
   docker compose --profile ai up -d
   ```

- The app reaches Ollama at `http://ollama:11434` over the Docker network — no host ports need to be opened.
- Change the model by setting `AI_MODEL` in `.env` (e.g. `AI_MODEL=qwen2.5:3b` for lighter hardware) and re-running `docker compose --profile ai up -d`; the init sidecar will pull the new model when needed.
- Pulled models are cached in the `ollama_data` named volume, so subsequent boots are faster.
- Verify in the UI: **Admin → System Settings → AI helper**, then click *Test connection*.
- To pull additional models manually: `docker compose exec ollama ollama pull <model>` (with the `ai` profile active).
- **Hosted provider only (no Ollama containers):** set `AI_PROVIDER=openai_compatible`, `AI_BASE_URL`, and `AI_API_KEY` in `.env`; keep `docker compose up -d` without the `ai` profile.

**Disable or remove AI** (turn off LLM calls, stop Ollama, revoke tokens, delete `ollama_data` safely): [UNINSTALL.md](UNINSTALL.md#disabling-or-removing-the-ai-helper).

### Encrypting stored secrets (recommended)

To store sensitive settings (OAuth secrets, mail password, AI API key, Peppol token, 2FA secret) encrypted at rest, set:

- `SETTINGS_ENCRYPTION_KEY` (Fernet key), or
- `SETTINGS_ENCRYPTION_KEY_FILE` (file path with the key on the first line)

### Raspberry Pi Deployment
TimeTracker runs perfectly on Raspberry Pi 4 (2GB+ RAM):
```bash
# Same Docker commands work on ARM architecture
docker-compose up -d
```

### HTTPS Configuration

#### Automatic HTTPS (Easiest)
```bash
# Uses self-signed certificates (generated automatically)
docker-compose up -d
# Access at https://localhost (accept browser warning)
```

#### Manual HTTPS with mkcert (No Browser Warnings)
```bash
# Use mkcert for locally-trusted certificates
docker-compose -f docker/docker-compose.https-mkcert.yml up -d
```
**📖 See [HTTPS Setup Guide](docs/admin/security/README_HTTPS.md) for detailed instructions.** HTTPS helper scripts live in `scripts/` (e.g. from project root: `bash scripts/setup-https-mkcert.sh`, `bash scripts/start-https.sh`).

### Monitoring & Analytics
```bash
# Alternate compose files (local-test, remote, analytics, https) are in docker/; use -f docker/docker-compose.xxx.yml

# Deploy with full monitoring stack (Prometheus, Grafana, Loki)
docker-compose -f docker-compose.yml -f docker/docker-compose.analytics.yml --profile monitoring up -d
# Grafana: http://localhost:3000
# Prometheus: http://localhost:9090
```

**📖 See [Deployment Guide](docs/admin/configuration/DOCKER_PUBLIC_SETUP.md) for detailed instructions**  
**📖 See [Docker Compose Setup](docs/admin/configuration/DOCKER_COMPOSE_SETUP.md) for configuration options**

---

## 🔧 Configuration

TimeTracker is highly configurable through environment variables. For a comprehensive list and recommended values, see:

- [`docs/admin/configuration/DOCKER_COMPOSE_SETUP.md`](docs/admin/configuration/DOCKER_COMPOSE_SETUP.md)
- [`env.example`](env.example)

Common settings:

```bash
# Timezone and locale
TZ=America/New_York
CURRENCY=USD

# Timer behavior
SINGLE_ACTIVE_TIMER=true
IDLE_TIMEOUT_MINUTES=30
ROUNDING_MINUTES=1

# User management
# Note: Only the first username in ADMIN_USERNAMES is auto-created during initialization.
# Additional usernames must self-register (if ALLOW_SELF_REGISTER=true) or be created manually.
ADMIN_USERNAMES=admin,manager
ALLOW_SELF_REGISTER=false

# Security (production)
SECRET_KEY=your-secure-random-key
SESSION_COOKIE_SECURE=true
```

---

## 📊 Analytics & Telemetry

TimeTracker includes **optional** analytics and monitoring features to help improve the application and understand how it's being used. All analytics features are:

- ✅ **Disabled by default** — You must explicitly opt-in
- ✅ **Privacy-first** — No personally identifiable information (PII) is collected
- ✅ **Self-hostable** — Run your own analytics infrastructure
- ✅ **Transparent** — All data collection is documented

### What We Collect (When Enabled)

#### 1. **Structured Logs** (Always On, Local Only)
- Request logs and error messages stored **locally** in `logs/app.jsonl`
- Used for troubleshooting and debugging
- **Never leaves your server**

#### 2. **Prometheus Metrics** (Always On, Self-Hosted)
- Request counts, latency, and performance metrics
- Exposed at `/metrics` endpoint for your Prometheus server
- **Stays on your infrastructure**

#### 3. **Error Monitoring** (Optional - Sentry)
- Captures uncaught exceptions and performance issues
- Helps identify and fix bugs quickly
- **Opt-in:** Set `SENTRY_DSN` environment variable

#### 4. **Product Analytics** (Optional - Grafana OTLP)
- Tracks feature usage and user behavior patterns with advanced features:
  - **Person Properties**: Role, auth method, login history
  - **Group Analytics**: Segment by version, platform, deployment
  - **Rich Context**: Browser, device, environment on every event
- **Sink config:** Set `GRAFANA_OTLP_ENDPOINT` and `GRAFANA_OTLP_TOKEN`

**Rollouts and kill switches** in this application are not driven by remote PostHog feature flags. Use **environment variables** and [`app/config.py`](app/config.py) (for example `DEMO_MODE`, `ALLOW_SELF_REGISTER`, `ENABLE_TELEMETRY`, `SINGLE_ACTIVE_TIMER`). **Per-user UI visibility** preferences are stored on the user record in the database, not in PostHog. With **`DEMO_MODE`**, the auto-created login is a standard **user** (no admin or settings access); see [`docs/deploy/RENDER.md`](docs/deploy/RENDER.md) for demo setup and upgrading old demo databases.

#### 5. **Installation Telemetry** (Optional, Anonymous)
- Sends anonymous installation data via Grafana OTLP with:
  - Anonymized fingerprint (SHA-256 hash, cannot be reversed)
  - Application version
  - Platform information
- **No PII:** No IP addresses, usernames, or business data
- **Opt-in:** Set `ENABLE_TELEMETRY=true` for detailed analytics; base telemetry remains anonymous

### How to Enable Analytics

```bash
# Enable Sentry error monitoring (optional)
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
SENTRY_TRACES_RATE=0.1  # 10% sampling for performance traces

# Configure Grafana Cloud OTLP sink (optional)
GRAFANA_OTLP_ENDPOINT=https://otlp-gateway-prod-eu-west-2.grafana.net/otlp/v1/logs
GRAFANA_OTLP_TOKEN=your-grafana-otlp-token

# Enable detailed analytics (optional)
ENABLE_TELEMETRY=true
TELE_SALT=your-unique-salt
APP_VERSION=1.0.0
```

### Self-Hosting Analytics

You can self-host all analytics services for complete control:

```bash
# Use docker-compose with monitoring profile
docker-compose --profile monitoring up -d
```

This starts:
- **Prometheus** — Metrics collection and storage
- **Grafana** — Visualization dashboards
- **Loki** (optional) — Log aggregation
- **Promtail** (optional) — Log shipping

### Privacy & Data Protection

> **Telemetry**: TimeTracker can optionally send anonymized usage data to help improve the product (errors, feature usage, install counts). All telemetry is **opt-in**. No personal data is collected. To disable telemetry, set `ENABLE_TELEMETRY=false` or simply don't set the environment variable (disabled by default).

**What we DON'T collect:**
- ❌ Email addresses or usernames
- ❌ IP addresses
- ❌ Project names or descriptions
- ❌ Time entry notes or client data
- ❌ Any personally identifiable information (PII)

**Your rights:**
- 📥 **Access**: View all collected data
- ✏️ **Rectify**: Correct inaccurate data
- 🗑️ **Erase**: Delete your data at any time
- 📤 **Export**: Export your data in standard formats

**📖 See [Privacy Policy](docs/privacy.md) for complete details**  
**📖 See [Analytics Documentation](docs/analytics.md) for configuration**  
**📖 See [Events Schema](docs/events.md) for tracked events**

---

## 🛣️ Roadmap

### Planned Features
- 📊 **Advanced Analytics** — More charts, insights, and reporting options
- 🔌 **API Extensions** — Additional RESTful API endpoints for integrations
- 🔔 **Push Notifications** — Real-time browser notifications
- 📱 **Mobile & Desktop App Enhancements** — Additional features for the native Flutter mobile and Electron desktop apps
- 🤖 **Automation Rules** — Automated workflows and task assignments
- 📈 **Advanced Forecasting** — AI-powered project timeline predictions


---

## Technology stack

Flask, SQLAlchemy, PostgreSQL/SQLite, Tailwind CSS, Docker — see [Architecture](docs/ARCHITECTURE.md) · [Project Structure](docs/development/PROJECT_STRUCTURE.md) · [UI Guidelines](docs/UI_GUIDELINES.md).

---

## 🤝 Contributing

We welcome contributions! Whether it's:

- 🐛 **Bug Reports** — Help us identify issues
- 💡 **Feature Requests** — Share your ideas
- 📝 **Documentation** — Improve our docs
- 💻 **Code Contributions** — Submit pull requests

### Quick Start for Contributors

1. **Fork and Clone**
   ```bash
   git clone https://github.com/your-username/TimeTracker.git
   cd TimeTracker
   ```

2. **Set Up Development Environment**
   ```bash
   # Use SQLite for quick local testing
   docker-compose -f docker/docker-compose.local-test.yml up -d
   ```

3. **Make Your Changes**
   - Follow the [Contributing guidelines](CONTRIBUTING.md) and [full Contributing doc](docs/development/CONTRIBUTING.md)
   - Write tests for new features
   - Update documentation as needed

4. **Submit a Pull Request**
   - Create a clear description of your changes
   - Reference any related issues
   - Ensure all tests pass

**📖 [CONTRIBUTING.md](CONTRIBUTING.md)** — Quick contributing overview  
**📖 [Full Contributing Guidelines](docs/development/CONTRIBUTING.md)** — Setup, standards, PR process  
**📖 [DEVELOPMENT.md](docs/DEVELOPMENT.md)** — Run locally, tests, releases  
**📖 [Local Testing with SQLite](docs/development/LOCAL_TESTING_WITH_SQLITE.md)** — Docker SQLite setup

---

## 📄 License

TimeTracker is licensed under the **GNU General Public License v3.0**.

This means you can:
- ✅ Use it commercially
- ✅ Modify and adapt it
- ✅ Distribute it
- ✅ Use it privately

**See [LICENSE](LICENSE) for full details**

---

## Support

If TimeTracker saves you money, **[a star on GitHub](https://github.com/drytrix/TimeTracker) helps others find it.**

- **Support the project / hide donate prompts:** [Support & Purchase Key](https://timetracker.drytrix.com/support.html) — donate or buy a one-time key to remove donate prompts in your instance
- **Documentation:** [`docs/`](docs/)
- **Bug reports:** [Open an issue](https://github.com/drytrix/TimeTracker/issues)
- **Discussions:** [GitHub Discussions](https://github.com/drytrix/TimeTracker/discussions)

---

<div align="center">

**[★ Star on GitHub](https://github.com/drytrix/TimeTracker)**

Built with care for the time-tracking community

</div>
