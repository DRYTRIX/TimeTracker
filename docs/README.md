# TimeTracker Documentation

Welcome to the comprehensive TimeTracker documentation. Everything you need to install, configure, use, and contribute to TimeTracker.

---

## 📖 Quick Links

- **[🚀 Getting Started Guide](GETTING_STARTED.md)** — Complete beginner tutorial (⭐ Start here!)
- **[Main README](../README.md)** — Product overview and quick start
- **[Installation Guide](#-installation--deployment)** — Get TimeTracker running
- **[Feature Guides](#-feature-documentation)** — Learn what TimeTracker can do
- **[Troubleshooting](#-troubleshooting)** — Solve common issues

---

## 🚀 Installation & Deployment

### Getting Started
- **[🚀 Getting Started Guide](GETTING_STARTED.md)** — Complete beginner tutorial (⭐ Start here!)
- **[Requirements](REQUIREMENTS.md)** — System requirements and dependencies
- **[Docker Public Setup](DOCKER_PUBLIC_SETUP.md)** — Production deployment with Docker
- **[Local Testing with SQLite](LOCAL_TESTING_WITH_SQLITE.md)** — Quick test without database setup

### Database & Migrations
- **[Database Migrations](../migrations/README.md)** — Database schema management with Flask-Migrate
- **[Migration Guide](../migrations/MIGRATION_GUIDE.md)** — Migrate existing databases
- **[Enhanced Database Startup](ENHANCED_DATABASE_STARTUP.md)** — Automatic database initialization
- **[Database Startup Fix](DATABASE_STARTUP_FIX_README.md)** — Database connection troubleshooting

### Docker & Containers
- **[Docker Startup Troubleshooting](DOCKER_STARTUP_TROUBLESHOOTING.md)** — Fix Docker issues
- **[Docker Startup Configuration](../docker/STARTUP_MIGRATION_CONFIG.md)** — Container startup behavior
- **[Docker Connection Troubleshooting](../docker/TROUBLESHOOTING_DB_CONNECTION.md)** — Database connection in Docker

---

## ✨ Feature Documentation

### Complete Features Reference
- **[📋 Complete Features Overview](FEATURES_COMPLETE.md)** — Comprehensive documentation of all 120+ features across 12 categories (⭐ Start here for complete feature list!)

### Core Features
- **[Task Management](TASK_MANAGEMENT_README.md)** — Complete task tracking system
- **[Task Management Overview](TASK_MANAGEMENT.md)** — Task management concepts
- **[Client Management](CLIENT_MANAGEMENT_README.md)** — Manage clients and relationships
- **[Client Notes](CLIENT_NOTES_FEATURE.md)** — Add internal notes about clients
- **[Invoice System](INVOICE_FEATURE_README.md)** — Generate and track invoices
- **[Enhanced Invoice System](ENHANCED_INVOICE_SYSTEM_README.md)** — Advanced invoicing features
- **[Calendar Features](CALENDAR_FEATURES_README.md)** — Calendar view and bulk entry

### Financial Features
- **[Expense Tracking](EXPENSE_TRACKING.md)** — Track business expenses
- **[Payment Tracking](PAYMENT_TRACKING.md)** — Track invoice payments
- **[Budget Alerts & Forecasting](BUDGET_ALERTS_AND_FORECASTING.md)** — Monitor project budgets

### Productivity Features
- **[Command Palette](COMMAND_PALETTE_USAGE.md)** — Keyboard shortcuts and quick actions
- **[Bulk Time Entry](BULK_TIME_ENTRY_README.md)** — Create multiple time entries at once
- **[Weekly Time Goals](WEEKLY_TIME_GOALS.md)** — Set and track weekly hour targets
- **[Toast Notification System](TOAST_NOTIFICATION_SYSTEM.md)** — User feedback and notifications

### Advanced Features
- **[Role-Based Permissions](ADVANCED_PERMISSIONS.md)** — Granular access control system
- **[Logo Upload System](LOGO_UPLOAD_SYSTEM_README.md)** — Brand your invoices
- **[Translation System](TRANSLATION_SYSTEM.md)** — Multi-language support

### Additional Documentation
- **[Mobile Improvements](MOBILE_IMPROVEMENTS.md)** — Mobile-optimized interface
- **[Invoice Interface Improvements](INVOICE_INTERFACE_IMPROVEMENTS.md)** — Invoice UI enhancements
- **[PDF Generation Troubleshooting](PDF_GENERATION_TROUBLESHOOTING.md)** — Fix PDF generation issues

---

## 🔧 Technical Documentation

### Project Structure
- **[Project Structure](PROJECT_STRUCTURE.md)** — Codebase organization and architecture
- **[Solution Guide](SOLUTION_GUIDE.md)** — Technical solutions and patterns

### Development
- **[Contributing Guidelines](CONTRIBUTING.md)** — How to contribute to TimeTracker
- **[Code of Conduct](CODE_OF_CONDUCT.md)** — Community standards and expectations
- **[Version Management](VERSION_MANAGEMENT.md)** — Release process and versioning

### CI/CD
- **[CI/CD Documentation](cicd/)** — Continuous integration and deployment
  - **[Documentation](cicd/CI_CD_DOCUMENTATION.md)** — CI/CD overview
  - **[Quick Start](cicd/CI_CD_QUICK_START.md)** — Get started with CI/CD
  - **[Implementation Summary](cicd/CI_CD_IMPLEMENTATION_SUMMARY.md)** — What was implemented
  - **[GitHub Actions Setup](cicd/GITHUB_ACTIONS_SETUP.md)** — Configure GitHub Actions
  - **[GitHub Actions Verification](cicd/GITHUB_ACTIONS_VERIFICATION.md)** — Verify CI/CD setup

### Release & Images
- **[Release Process](RELEASE_PROCESS.md)** — How to create releases
- **[GitHub Workflow Images](GITHUB_WORKFLOW_IMAGES.md)** — Docker images on GitHub Container Registry

---

## 🛠️ Troubleshooting

### Common Issues
- **[Docker Startup Troubleshooting](DOCKER_STARTUP_TROUBLESHOOTING.md)** — Docker won't start
- **[Database Connection Issues](../docker/TROUBLESHOOTING_DB_CONNECTION.md)** — Can't connect to database
- **[PDF Generation Issues](PDF_GENERATION_TROUBLESHOOTING.md)** — PDFs not generating
- **[Solution Guide](SOLUTION_GUIDE.md)** — General problem solving

### Quick Fixes
- **Port conflicts**: Change `PORT=8081` in docker-compose command
- **Database issues**: Run `docker-compose down -v && docker-compose up -d`
- **Permission errors**: Check file ownership with `chown -R $USER:$USER .`
- **Migration failures**: See [Database Migrations](../migrations/README.md)

---

## 📚 Additional Resources

### Features & Improvements
Detailed documentation about features and improvements is available in:
- **[Implementation Notes](implementation-notes/)** — Development summaries and changelogs
- **[Feature Guides](features/)** — Specific feature documentation

### Implementation Notes
Recent improvements and changes:
- **[Layout & UX Improvements](implementation-notes/IMPLEMENTATION_COMPLETE_SUMMARY.md)** — Complete UI/UX overhaul with 16 major improvements 🆕
- **[High-Impact Features](implementation-notes/HIGH_IMPACT_SUMMARY.md)** — Enhanced search, keyboard shortcuts, and data tables 🆕
- **[Advanced Features](implementation-notes/COMPLETE_ADVANCED_FEATURES_SUMMARY.md)** — Keyboard shortcuts system and quick actions menu
- **[Analytics Improvements](implementation-notes/ANALYTICS_IMPROVEMENTS_SUMMARY.md)**
- **[Calendar Improvements](implementation-notes/CALENDAR_IMPROVEMENTS_SUMMARY.md)**
- **[Command Palette Improvements](implementation-notes/COMMAND_PALETTE_IMPROVEMENTS.md)**
- **[Dashboard & Navbar](implementation-notes/DASHBOARD_NAVBAR_IMPROVEMENTS.md)**
- **[Kanban Improvements](implementation-notes/KANBAN_IMPROVEMENTS.md)**
- **[Notification System](implementation-notes/NOTIFICATION_SYSTEM_SUMMARY.md)**
- **[OIDC Improvements](implementation-notes/OIDC_IMPROVEMENTS.md)**
- **[Reports Improvements](implementation-notes/REPORTS_IMPROVEMENTS_SUMMARY.md)**
- **[Styling Consistency](implementation-notes/STYLING_CONSISTENCY_SUMMARY.md)**
- **[Toast Notifications](implementation-notes/TOAST_NOTIFICATION_IMPROVEMENTS.md)**
- **[Translation Improvements](implementation-notes/TRANSLATION_IMPROVEMENTS_SUMMARY.md)**
- **[Translation Fixes](implementation-notes/TRANSLATION_FIXES_SUMMARY.md)**
- **[UI Improvements](implementation-notes/UI_IMPROVEMENTS_SUMMARY.md)**

### Feature Specific
Feature documentation and quick starts:
- **[Layout Improvements Complete](features/LAYOUT_IMPROVEMENTS_COMPLETE.md)** — Comprehensive UX improvements documentation 🆕
- **[Alembic Migrations](features/ALEMBIC_MIGRATION_README.md)**
- **[Project Costs](features/PROJECT_COSTS_FEATURE.md)**
- **[Project Costs Quick Start](features/QUICK_START_PROJECT_COSTS.md)**
- **[Calendar Quick Start](features/CALENDAR_QUICK_START.md)**
- **[Badges](features/BADGES.md)**
- **[Code Formatting](features/RUN_BLACK_FORMATTING.md)**

---

## 🔍 Documentation by Topic

### For New Users
1. Start with **[Main README](../README.md)** for product overview
2. Review **[Requirements](REQUIREMENTS.md)** to check if your system is compatible
3. Follow **[Docker Public Setup](DOCKER_PUBLIC_SETUP.md)** for installation
4. Explore **[Feature Documentation](#-feature-documentation)** to learn what TimeTracker can do

### For Developers
1. Read **[Contributing Guidelines](CONTRIBUTING.md)** before making changes
2. Review **[Project Structure](PROJECT_STRUCTURE.md)** to understand the codebase
3. Check **[Solution Guide](SOLUTION_GUIDE.md)** for technical patterns
4. Use **[Local Testing with SQLite](LOCAL_TESTING_WITH_SQLITE.md)** for development

### For Administrators
1. Follow **[Docker Public Setup](DOCKER_PUBLIC_SETUP.md)** for deployment
2. Review **[Version Management](VERSION_MANAGEMENT.md)** for updates
3. Set up **[Database Migrations](../migrations/README.md)** for schema management
4. Configure **[CI/CD](cicd/)** for automated deployments

### For Troubleshooting
1. Check **[Docker Startup Troubleshooting](DOCKER_STARTUP_TROUBLESHOOTING.md)**
2. Review **[Database Connection Issues](../docker/TROUBLESHOOTING_DB_CONNECTION.md)**
3. Consult **[Solution Guide](SOLUTION_GUIDE.md)** for common problems
4. Check specific feature documentation if issue is feature-related

---

## 📝 Documentation Structure

```
docs/
├── README.md                          # This file - documentation index
├── REQUIREMENTS.md                    # System requirements
├── PROJECT_STRUCTURE.md               # Codebase architecture
├── CONTRIBUTING.md                    # Contribution guidelines
├── CODE_OF_CONDUCT.md                 # Community standards
│
├── cicd/                              # CI/CD documentation
│   ├── CI_CD_DOCUMENTATION.md
│   ├── CI_CD_QUICK_START.md
│   └── ...
│
├── features/                          # Feature-specific guides
│   ├── ALEMBIC_MIGRATION_README.md
│   ├── PROJECT_COSTS_FEATURE.md
│   └── ...
│
└── implementation-notes/              # Development notes
    ├── ANALYTICS_IMPROVEMENTS_SUMMARY.md
    ├── UI_IMPROVEMENTS_SUMMARY.md
    └── ...
```

---

## 🤝 Contributing to Documentation

Found an error? Want to improve the docs?

1. Check the **[Contributing Guidelines](CONTRIBUTING.md)**
2. Make your changes to the relevant documentation file
3. Test that all links work correctly
4. Submit a pull request with a clear description

Good documentation helps everyone! 📚

---

## 💡 Tips for Using This Documentation

- **Use the search function** in your browser (Ctrl/Cmd + F) to find specific topics
- **Follow links** to related documentation for deeper understanding
- **Start with Quick Links** at the top if you're in a hurry
- **Browse by topic** using the categorized sections
- **Check Implementation Notes** for recent changes and improvements

---

<div align="center">

**Need help?** [Open an issue](https://github.com/drytrix/TimeTracker/issues) or check the [troubleshooting section](#-troubleshooting)

**Want to contribute?** See our [Contributing Guidelines](CONTRIBUTING.md)

---

[⬆ Back to Top](#timetracker-documentation)

</div>
