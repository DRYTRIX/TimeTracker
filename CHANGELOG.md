# Changelog

All notable changes to TimeTracker will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- **PDF layout: decorative image persistence and PDF preview (Issue #432)** — Decorative images now survive save/load: image URLs are synced onto groups before generating the template, injected into the saved design JSON using position-based matching, and restored from the saved JSON onto the canvas on load. Empty decorative image elements are no longer added to the ReportLab template, and the PDF generator skips empty or invalid image sources and validates base64 data URIs, preventing a mostly-black or broken PDF preview.

### Added
- **ZugFerd / Factur-X support for invoice PDFs** — When enabled in Admin → Settings → Peppol e-Invoicing, exported invoice PDFs embed EN 16931 UBL XML as `ZUGFeRD-invoice.xml`, producing hybrid human- and machine-readable invoices. Uses the same UBL as Peppol; these PDFs can be sent via Peppol or email. New setting `invoices_zugferd_pdf`, migration `128_add_invoices_zugferd_pdf`, dependency `pikepdf`, and [docs/admin/configuration/PEPPOL_EINVOICING.md](docs/admin/configuration/PEPPOL_EINVOICING.md) updated for both Peppol and ZugFerd.
- **Subcontractor role and assigned clients** — Users with the Subcontractor role can be restricted to specific clients and their projects. Admins assign clients in Admin → Users → Edit user (section "Assigned Clients (Subcontractor)"). Scope is applied to clients, projects, time entries, reports, invoices, timer, and API v1; direct access to other clients/projects returns 403. New table `user_clients`, migration `127_add_user_clients_table`, and docs in [docs/SUBCONTRACTOR_ROLE.md](docs/SUBCONTRACTOR_ROLE.md).
- Additional features and improvements in development

## [4.19.0] - 2025-02-13

### Added
- **REST API v1** - CRM and time approvals: `/api/v1/deals`, `/api/v1/leads`, `/api/v1/clients/<id>/contacts`, `/api/v1/contacts/<id>`, `/api/v1/time-entry-approvals` (list, get, approve, reject, cancel, request-approval, bulk-approve). New API token scopes: `read:deals`, `write:deals`, `read:leads`, `write:leads`, `read:contacts`, `write:contacts`, `read:time_approvals`, `write:time_approvals`.
- **Documentation** - Service layer and BaseCRUD pattern ([docs/development/SERVICE_LAYER_AND_BASE_CRUD.md](docs/development/SERVICE_LAYER_AND_BASE_CRUD.md)); RBAC permission model ([docs/development/RBAC_PERMISSION_MODEL.md](docs/development/RBAC_PERMISSION_MODEL.md)).

### Changed
- **API responses** - Projects and new CRM/approvals API v1 routes use standardized `error_response` / `forbidden_response` / `not_found_response` from `app.utils.api_responses`.
- **Templates** - All templates consolidated under `app/templates/`; root `templates/` removed and extra Jinja loader removed.
- **Version** - README, FEATURES_COMPLETE.md, and docs reference `setup.py` as single source of truth for version (4.19.0).
- **Refactored examples** - `projects_refactored_example.py`, `timer_refactored.py`, `invoices_refactored.py` marked as reference-only in module docstrings.

## [4.14.0] - 2025-01-27

### Changed
- **Version Update** - Updated to version 4.14.0
- **Documentation** - Comprehensive README and documentation updates for clarity and completeness
- **Technology Stack** - Added complete technology stack overview to README
- **Quick Start** - Enhanced with prerequisites, clearer instructions, and troubleshooting links
- **System Requirements** - Added detailed system requirements section
- **Documentation Organization** - Improved organization by use case and user type

### Fixed
- **Version Consistency** - Fixed version inconsistencies across all documentation files
- **Documentation Links** - Fixed broken links and improved navigation
- **Feature Documentation** - Added comprehensive links to feature guides throughout README

## [4.13.2] - 2025-01-27

### Changed
- **Version Update** - Updated to version 4.13.2
- **Documentation** - Comprehensive README and documentation updates for clarity and completeness

### Fixed
- **Version Consistency** - Fixed version inconsistencies across all documentation files

## [4.8.8] - 2025-01-27

### Changed
- **Version Update** - Updated to version 4.8.8
- **Documentation** - Comprehensive project analysis and documentation updates

### Fixed
- **Version Consistency** - Fixed version inconsistencies across documentation files

## [4.8.0] - TBD

### Added
- Additional features and improvements (details to be documented)

### Changed
- Version management improvements

## [4.7.1] - TBD

### Added
- Additional features and improvements (details to be documented)

### Fixed
- Bug fixes and stability improvements

## [4.7.0] - TBD

### Added
- Additional features and improvements (details to be documented)

### Changed
- Performance optimizations
- Code quality improvements

## [4.6.0] - 2025-12-14

### Added
- **Comprehensive Issue/Bug Tracking System** - Complete issue and bug tracking functionality with full lifecycle management

## [4.5.1] - 2025-12-13

### Changed
- **Performance Optimization** - Optimized task listing queries and improved version management
- **Version Management** - Enhanced version management system

## [4.5.0] - 2025-12-12

### Added
- **Advanced Report Builder** - Iterative report generation with email distribution capabilities
- **Quick Task Creation** - Create tasks directly from the Start Timer modal for faster workflow
- **Kanban Board Enhancements** - Added user filter and flexible column layout options
- **PWA Install UI** - Improved Progressive Web App installation user interface

### Fixed
- **Permission and Role Management** - Fixed bugs in permission and role management system

### Changed
- **Error Handling** - Improved error handling throughout the application
- **Performance Logging** - Enhanced performance logging and monitoring

## [4.4.1] - 2025-12-08

### Added
- **Custom Reports Enhancement** - Enhanced custom reports and scheduled reports functionality

### Fixed
- **Dashboard Cache Invalidation** - Fixed dashboard cache invalidation when editing timer entries (#342)
- **Custom Field Definitions** - Fixed graceful handling of missing custom_field_definitions table (#344)

## [4.4.0] - 2025-12-03

### Added
- **Project Custom Fields** - Add custom fields to projects for enhanced project tracking
- **File Attachments** - File attachment support for projects and clients
- **Salesman-Based Report Splitting** - Report splitting and email distribution based on salesperson assignments

### Changed
- **Performance Optimization** - Optimized task queries and fixed N+1 performance issues
- **Version Update** - Updated setup.py version to 4.4.0

## [4.3.2] - 2025-12-02

### Added
- **Custom Field Filtering** - Custom field filtering and display for clients, projects, and time entries
- **Client Count Tracking** - Client count tracking and cleanup for custom field definitions
- **Unpaid Hours Report** - New unpaid hours report with Ajax filtering and Excel export
- **Time Entries Overview** - New time entries overview page with AJAX filters and bulk mark as paid
- **Configurable Duplicate Detection** - Configurable duplicate detection fields for CSV client import
- **Enhanced Audit Logging** - Improved error handling and diagnostic tools for audit logging

### Changed
- **Offline Sync** - Enhanced offline sync functionality and performance improvements
- **Error Handling** - Improved error handling throughout the application
- **Docker Healthchecks** - Enhanced Docker healthcheck functionality

## [4.3.1] - 2025-12-01

### Changed
- **Offline Sync** - Enhanced offline sync functionality and performance improvements

## [4.3.0] - 2025-12-01

### Added
- **Custom Field Filtering** - Custom field filtering and display for clients, projects, and time entries
- **Client Count Tracking** - Client count tracking and cleanup for custom field definitions
- **Unpaid Hours Report** - New unpaid hours report with Ajax filtering and Excel export
- **Time Entries Overview** - New time entries overview page with AJAX filters and bulk mark as paid
- **Configurable Duplicate Detection** - Configurable duplicate detection fields for CSV client import
- **Enhanced Audit Logging** - Improved error handling and diagnostic tools for audit logging

### Changed
- **Error Handling** - Improved error handling throughout the application
- **Docker Healthchecks** - Enhanced Docker healthcheck functionality
- **Offline Sync** - Enhanced offline sync functionality

## [4.2.1] - 2025-12-01

### Fixed
- **AUTH_METHOD=none** - Fixed authentication method when set to none
- **Schema Verification** - Added comprehensive schema verification

## [4.2.0] - 2025-11-30

### Added
- **CSV Import/Export** - CSV import/export for clients with custom fields and contacts
- **Global Custom Field Definitions** - Global custom field definitions with link template support
- **Paid Status Tracking** - Paid status tracking for time entries with invoice reference
- **OAuth Credentials Dropdown** - Converted OAuth credentials section to dropdown in System Settings

---

## Release Notes Format

Each release includes:
- **Added** - New features
- **Changed** - Changes in existing functionality
- **Deprecated** - Soon-to-be removed features
- **Removed** - Removed features
- **Fixed** - Bug fixes
- **Security** - Security improvements

For detailed information about each release, see the [GitHub Releases](https://github.com/drytrix/TimeTracker/releases) page.
