# TimeTracker Documentation

Welcome to the comprehensive TimeTracker documentation. Everything you need to install, configure, use, and contribute to TimeTracker.

---

## 📖 Quick Links

- **[🚀 Getting Started Guide](GETTING_STARTED.md)** — Complete beginner tutorial (⭐ Start here!)
- **[Main README](../README.md)** — Product overview and quick start
- **[Installation Guide](../INSTALLATION.md)** — Step-by-step installation (Docker, SQLite)
- **[Architecture](ARCHITECTURE.md)** — System overview and design
- **[Development Guide](DEVELOPMENT.md)** — Run locally, tests, releases
- **[API Quick Reference](API.md)** — REST API overview and examples
- **[Installation & Deployment](#-installation--deployment)** — Get TimeTracker running
- **[Feature Guides](#-feature-documentation)** — Learn what TimeTracker can do
- **[Troubleshooting](#-troubleshooting)** — Solve common issues

---

## 🗺️ Documentation Map

```
docs/
├── 👤 User Documentation
│   ├── Getting Started
│   ├── Feature Guides
│   └── User Guides
│
├── 🔧 Administrator Documentation
│   ├── Configuration
│   ├── Deployment
│   ├── Security
│   └── Monitoring
│
├── 👨‍💻 Developer Documentation
│   ├── Contributing
│   ├── Architecture
│   ├── Development Setup
│   └── Testing
│
└── 📚 Reference
    ├── API Documentation
    ├── Implementation Notes
    └── Reports
```

---

## 👤 User Documentation

### Getting Started
- **[🚀 Getting Started Guide](GETTING_STARTED.md)** — Complete beginner tutorial (⭐ Start here!)
- **[Installation Guide](../INSTALLATION.md)** — Step-by-step installation (root)
- **[Requirements](REQUIREMENTS.md)** — System requirements and dependencies

### User Guides
- **How to deploy**: [Docker Compose Setup](admin/configuration/DOCKER_COMPOSE_SETUP.md) · [Docker Public Setup](admin/configuration/DOCKER_PUBLIC_SETUP.md)
- **[Quick Wins Implementation (Deployment Checklist)](guides/DEPLOYMENT_GUIDE.md)** — Feature implementation status (not deployment steps)
- **[Quick Start Guide](guides/QUICK_START_GUIDE.md)** — Get started quickly
- **[Quick Start Local Development](guides/QUICK_START_LOCAL_DEVELOPMENT.md)** — Local development setup

### Feature Documentation
- **[📋 Complete Features Overview](FEATURES_COMPLETE.md)** — Comprehensive documentation of all 130+ features (⭐ Complete reference!)
- **[Task Management](TASK_MANAGEMENT_README.md)** — Complete task tracking system
- **[Client Management](CLIENT_MANAGEMENT_README.md)** — Manage clients and relationships
- **[Invoice System](INVOICE_FEATURE_README.md)** — Generate and track invoices
- **[Calendar Features](CALENDAR_FEATURES_README.md)** — Calendar view and bulk entry
- **[Expense Tracking](EXPENSE_TRACKING.md)** — Track business expenses
- **[Payment Tracking](PAYMENT_TRACKING.md)** — Track invoice payments
- **[Budget Alerts & Forecasting](BUDGET_ALERTS_AND_FORECASTING.md)** — Monitor project budgets
- **[Command Palette](COMMAND_PALETTE_USAGE.md)** — Keyboard shortcuts and quick actions
- **[Bulk Time Entry](BULK_TIME_ENTRY_README.md)** — Create multiple time entries at once
- **[Time Entry Templates](TIME_ENTRY_TEMPLATES.md)** — Reusable time entry templates
- **[Weekly Time Goals](WEEKLY_TIME_GOALS.md)** — Set and track weekly hour targets
- **[Break Time for timers and manual entries](BREAK_TIME_FEATURE.md)** — Pause timers (break time) and optional break field on manual entries (Issue #561)
- **[Time Rounding](TIME_ROUNDING_PREFERENCES.md)** — Configurable time rounding
- **[Role-Based Permissions](ADVANCED_PERMISSIONS.md)** — Granular access control
- **[Subcontractor role and assigned clients](SUBCONTRACTOR_ROLE.md)** — Restrict users to specific clients and projects

See [features/](features/) for additional feature documentation.

---

## 🔧 Administrator Documentation

### Configuration
- **[Docker Compose Setup](admin/configuration/DOCKER_COMPOSE_SETUP.md)** — Docker deployment guide
- **[Docker Public Setup](admin/configuration/DOCKER_PUBLIC_SETUP.md)** — Production deployment
- **[Docker Startup Troubleshooting](admin/configuration/DOCKER_STARTUP_TROUBLESHOOTING.md)** — Fix startup issues
- **[Email Configuration](admin/configuration/EMAIL_CONFIGURATION.md)** — Email setup
- **[OIDC Setup](admin/configuration/OIDC_SETUP.md)** — OIDC/SSO authentication setup
- **[Support visibility](admin/configuration/SUPPORT_VISIBILITY.md)** — Hide donate/support UI with a purchased key; [purchase key](https://timetracker.drytrix.com/support.html)

### Deployment
- **[Version Management](admin/deployment/VERSION_MANAGEMENT.md)** — Managing versions
- **[Release Process](admin/deployment/RELEASE_PROCESS.md)** — Release workflow
- **[Official Builds](admin/deployment/OFFICIAL_BUILDS.md)** — Official build information

### Security
- **[Security Documentation](admin/security/)** — Security guides and configuration
- **[CSRF Configuration](admin/security/CSRF_CONFIGURATION.md)** — CSRF token setup
- **[CSRF Troubleshooting](admin/security/CSRF_TROUBLESHOOTING.md)** — Fix CSRF errors
- **[HTTPS Setup (Auto)](admin/security/README_HTTPS_AUTO.md)** — Automatic HTTPS
- **[HTTPS Setup (mkcert)](admin/security/README_HTTPS.md)** — Manual HTTPS with mkcert
- See [admin/security/](admin/security/) for all security-related documentation

### Monitoring
- **[Monitoring Documentation](admin/monitoring/)** — Monitoring and analytics setup
- See [admin/monitoring/](admin/monitoring/) for telemetry and analytics guides

**📖 See [admin/README.md](admin/README.md) for complete administrator documentation**

---

## 👨‍💻 Developer Documentation

### Terminology

Use consistent terms in code, API, and user-facing copy: **time entry** / **time entries**, **client**, **project**, **task**, **invoice**. See [Product/UX Audit](PRODUCT_UX_AUDIT.md) for full context and naming recommendations.

### Getting Started
- **[Contributor Guide](development/CONTRIBUTOR_GUIDE.md)** — Architecture, local dev, testing, adding routes/services/templates, versioning
- **[Contributing](../CONTRIBUTING.md)** — How to contribute (root; quick overview)
- **[Contributing Guidelines (full)](development/CONTRIBUTING.md)** — Setup, standards, PR process
- **[Development Guide](DEVELOPMENT.md)** — Run locally, tests, releases
- **[Architecture](ARCHITECTURE.md)** — System overview and design
- **[Code of Conduct](development/CODE_OF_CONDUCT.md)** — Community standards
- **[Project Structure](development/PROJECT_STRUCTURE.md)** — Codebase organization and architecture

### Development Setup
- **[Local Testing with SQLite](development/LOCAL_TESTING_WITH_SQLITE.md)** — Quick local testing setup
- **[Local Development with Analytics](development/LOCAL_DEVELOPMENT_WITH_ANALYTICS.md)** — Development setup with analytics

### Testing
- **[Testing Quick Reference](TESTING_QUICK_REFERENCE.md)** — Testing overview
- **[Testing Coverage Guide](TESTING_COVERAGE_GUIDE.md)** — Coverage documentation
- See [testing/](testing/) for additional testing documentation

### CI/CD
- **[CI/CD Documentation](cicd/)** — Continuous integration and deployment
  - **[Documentation](cicd/CI_CD_DOCUMENTATION.md)** — CI/CD overview
  - **[Quick Start](cicd/CI_CD_QUICK_START.md)** — Get started with CI/CD
  - **[Implementation Summary](cicd/CI_CD_IMPLEMENTATION_SUMMARY.md)** — What was implemented
  - **[GitHub Actions Setup](cicd/GITHUB_ACTIONS_SETUP.md)** — Configure GitHub Actions

### Technical Documentation
- **[Solution Guide](SOLUTION_GUIDE.md)** — Technical solutions and patterns
- **[Frontend Quality Gates](development/FRONTEND_QUALITY_GATES.md)** — Accessibility, performance, and modernization (web, desktop, mobile)
- **[Database Migrations](../migrations/README.md)** — Database schema management
- **[Implementation Notes](implementation-notes/)** — Development notes and summaries

### Product & Roadmap
- **[Competitive Analysis](competitive-analysis/README.md)** — Feature gap analysis and phase PRDs

**📖 See [development/README.md](development/README.md) for complete developer documentation**

---

## 📚 API Documentation

- **[API Quick Reference](API.md)** — Overview and quick examples
- **[REST API](api/REST_API.md)** — Complete API reference with all endpoints (⭐ Full reference!)
- **[API Token Scopes](api/API_TOKEN_SCOPES.md)** — Understanding token permissions and scopes
- **[API Versioning](api/API_VERSIONING.md)** — API versioning strategy
- **[API Enhancements](api/API_ENHANCEMENTS.md)** — Recent API improvements

**📖 See [api/README.md](api/README.md) for complete API documentation**

### Quick API Examples

**Authentication:**
```bash
curl -H "Authorization: Bearer YOUR_API_TOKEN" \
     https://your-domain.com/api/v1/projects
```

**Create Time Entry:**
```bash
curl -X POST -H "Authorization: Bearer YOUR_API_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"project_id": 1, "start_time": "2025-01-27T09:00:00", "end_time": "2025-01-27T17:00:00"}' \
     https://your-domain.com/api/v1/time-entries
```

See [REST API Documentation](api/REST_API.md) for complete examples and endpoint details.

---

## 🚀 Installation & Deployment

### Quick Start
1. **[Installation Guide](../INSTALLATION.md)** — Step-by-step installation (root)
2. **[Getting Started Guide](GETTING_STARTED.md)** — Complete beginner tutorial
3. **[Docker Compose Setup](admin/configuration/DOCKER_COMPOSE_SETUP.md)** — Recommended deployment method
4. **[Requirements](REQUIREMENTS.md)** — System requirements

### Database & Migrations
- **[Database Migrations](../migrations/README.md)** — Database schema management with Flask-Migrate
- **[Migration Guide](../migrations/MIGRATION_GUIDE.md)** — Migrate existing databases
- **[Enhanced Database Startup](ENHANCED_DATABASE_STARTUP.md)** — Automatic database initialization
- **[Database Startup Fix](DATABASE_STARTUP_FIX_README.md)** — Database connection troubleshooting
- **[Docker Connection Troubleshooting](../docker/TROUBLESHOOTING_DB_CONNECTION.md)** — Database connection in Docker

---

## 🛠️ Troubleshooting

### Common Issues
- **[Docker Startup Troubleshooting](admin/configuration/DOCKER_STARTUP_TROUBLESHOOTING.md)** — Docker won't start
- **[Database Connection Issues](../docker/TROUBLESHOOTING_DB_CONNECTION.md)** — Can't connect to database
- **[PDF Generation Issues](PDF_GENERATION_TROUBLESHOOTING.md)** — PDFs not generating
- **[Solution Guide](SOLUTION_GUIDE.md)** — General problem solving
- **[Troubleshooting Transaction Error](TROUBLESHOOTING_TRANSACTION_ERROR.md)** — Transaction issues

### Quick Fixes
- **Port conflicts**: Change `PORT=8081` in docker-compose command
- **Database issues**: Run `docker-compose down -v && docker-compose up -d`
- **Permission errors**: Check file ownership with `chown -R $USER:$USER .`
- **Migration failures**: See [Database Migrations](../migrations/README.md)

---

## 📝 Additional Resources

### Implementation Notes
Recent improvements and changes are documented in [implementation-notes/](implementation-notes/):
- Layout & UX improvements
- Feature implementations
- Bug fixes and improvements
- Architecture changes

### Reports & Analysis
Analysis reports and summaries are available in [reports/](reports/):
- Bugfix summaries
- Audit reports
- Translation analysis

### Feature-Specific Documentation
Detailed feature documentation is available in [features/](features/):
- Feature guides
- Quick start guides
- Implementation status

### User Guides
Additional user guides are available in [user-guides/](user-guides/):
- Step-by-step guides
- Tips and tricks
- Best practices

---

## 🔍 Documentation by Role

### For New Users
1. Start with **[Main README](../README.md)** for product overview
2. Follow **[Getting Started Guide](GETTING_STARTED.md)** for installation
3. Review **[Requirements](REQUIREMENTS.md)** to check system compatibility
4. Explore **[Feature Documentation](#-feature-documentation)** to learn features

### For Administrators
1. Follow **[Docker Compose Setup](admin/configuration/DOCKER_COMPOSE_SETUP.md)** for deployment
2. Review **[Version Management](admin/deployment/VERSION_MANAGEMENT.md)** for updates
3. Set up **[Email Configuration](admin/configuration/EMAIL_CONFIGURATION.md)** if needed
4. Configure **[OIDC/SSO](admin/configuration/OIDC_SETUP.md)** for authentication
5. See **[admin/README.md](admin/README.md)** for complete admin documentation

### For Developers
1. Read **[Contributing Guidelines](development/CONTRIBUTING.md)** before making changes
2. Review **[Project Structure](development/PROJECT_STRUCTURE.md)** to understand codebase
3. Check **[Solution Guide](SOLUTION_GUIDE.md)** for technical patterns
4. Use **[Local Testing with SQLite](development/LOCAL_TESTING_WITH_SQLITE.md)** for development
5. See **[development/README.md](development/README.md)** for complete developer documentation

### For Troubleshooting
1. Check **[Docker Startup Troubleshooting](admin/configuration/DOCKER_STARTUP_TROUBLESHOOTING.md)**
2. Review **[Database Connection Issues](../docker/TROUBLESHOOTING_DB_CONNECTION.md)**
3. Consult **[Solution Guide](SOLUTION_GUIDE.md)** for common problems
4. Check specific feature documentation if issue is feature-related

---

## 📁 Documentation Structure

```
docs/
├── README.md                          # This file - documentation index
├── GETTING_STARTED.md                 # Beginner tutorial
├── REQUIREMENTS.md                    # System requirements
├── FEATURES_COMPLETE.md               # Complete features list
│
├── guides/                            # User-facing guides
│   ├── DEPLOYMENT_GUIDE.md
│   ├── QUICK_START_GUIDE.md
│   └── ...
│
├── admin/                             # Administrator documentation
│   ├── configuration/                 # Configuration guides
│   ├── deployment/                    # Deployment guides
│   ├── security/                      # Security documentation
│   └── monitoring/                    # Monitoring & analytics
│
├── development/                       # Developer documentation
│   ├── CONTRIBUTING.md
│   ├── CODE_OF_CONDUCT.md
│   ├── PROJECT_STRUCTURE.md
│   └── ...
│
├── api/                               # API documentation
│   ├── REST_API.md
│   ├── API_TOKEN_SCOPES.md
│   └── ...
│
├── features/                          # Feature-specific guides
│   └── ...
│
├── implementation-notes/              # Development notes
│   └── ...
│
├── testing/                           # Testing documentation
│   └── ...
│
├── reports/                           # Reports & analysis
│   └── ...
│
├── user-guides/                       # Additional user guides
│   └── ...
│
└── cicd/                              # CI/CD documentation
    └── ...
```

---

## 📋 Documentation Audit

A summary of doc accuracy, outdated content, gaps, and contradictions is in [DOCS_AUDIT.md](DOCS_AUDIT.md). Use it when updating or reorganizing docs.

---

## 🤝 Contributing to Documentation

Found an error? Want to improve the docs?

1. Check the **[Contributing Guidelines](development/CONTRIBUTING.md)**
2. Make your changes to the relevant documentation file
3. Test that all links work correctly
4. Submit a pull request with a clear description

Good documentation helps everyone! 📚

---

## 💡 Tips for Using This Documentation

- **Use the search function** in your browser (Ctrl/Cmd + F) to find specific topics
- **Follow links** to related documentation for deeper understanding
- **Start with Quick Links** at the top if you're in a hurry
- **Browse by role** using the role-based sections above
- **Check Implementation Notes** for recent changes and improvements

---

<div align="center">

**Need help?** [Open an issue](https://github.com/drytrix/TimeTracker/issues) or check the [troubleshooting section](#-troubleshooting)

**Want to contribute?** See our [Contributing Guidelines](development/CONTRIBUTING.md)

---

[⬆ Back to Top](#timetracker-documentation)

</div>
