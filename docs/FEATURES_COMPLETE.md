# TimeTracker - Complete Features Documentation

**Version:** 3.9.0  
**Last Updated:** 2025-01-27

---

## Table of Contents

1. [Overview](#overview)
2. [Time Tracking Features](#time-tracking-features)
3. [Project Management](#project-management)
4. [Task Management](#task-management)
5. [Client Management](#client-management)
6. [Invoicing & Billing](#invoicing--billing)
7. [Financial Management](#financial-management)
8. [Reporting & Analytics](#reporting--analytics)
9. [User Management & Security](#user-management--security)
10. [Productivity Features](#productivity-features)
11. [Administration](#administration)
12. [Integration & API](#integration--api)
13. [Technical Features](#technical-features)

---

## Overview

TimeTracker is a comprehensive, self-hosted time tracking and project management application designed for freelancers, teams, and businesses. This document provides a complete overview of all available features.

---

## Time Tracking Features

### Core Time Tracking

#### 1. **One-Click Timers**
- Start tracking time with a single click
- Quick timer start from dashboard, projects, or tasks
- Visual timer display with running time
- Multiple timer support (configurable)

#### 2. **Persistent Timers**
- Server-side timer persistence
- Timers continue running after browser closes
- Automatic timer recovery on login
- Cross-device synchronization

#### 3. **Manual Time Entry**
- Add historical time entries
- Flexible date/time selection
- Notes and tags support
- Billable/non-billable flagging
- Project and task association

#### 4. **Timer Management**
- Start, stop, pause, and resume timers
- Edit active timers
- Delete timers
- Timer history and audit trail
- Timer duplication for recurring work

#### 5. **Idle Detection**
- Automatic pause after configurable idle time
- Configurable idle timeout (default: 30 minutes)
- User notification on idle detection
- Manual resume after idle pause

### Advanced Time Tracking

#### 6. **Bulk Time Entry**
- Create multiple time entries at once
- Consecutive day entry with weekend skipping
- Batch project/task assignment
- Bulk notes and tags application
- Date range selection

#### 7. **Time Entry Templates**
- Save common time entries as templates
- Quick template application
- Template categories and organization
- One-click timer start from templates
- Template editing and management

#### 8. **Time Entry Duplication**
- Duplicate existing time entries
- Quick copy with date adjustment
- Preserve notes, tags, and project associations
- Batch duplication support

#### 9. **Time Rounding**
- Configurable rounding intervals (1, 5, 15 minutes)
- Per-project rounding rules
- Automatic rounding on entry save
- Rounding preference settings

#### 10. **Calendar View**
- Visual calendar interface for time entries
- Month, week, and day views
- Drag-and-drop time entry editing
- Calendar event creation
- Agenda view with upcoming deadlines

#### 11. **Focus Sessions (Pomodoro)**
- Pomodoro-style focus session tracking
- Configurable session lengths
- Break tracking (short and long breaks)
- Cycle completion tracking
- Interruption logging
- Session notes and outcomes

#### 12. **Recurring Time Blocks**
- Weekly recurring time block templates
- Weekday selection (Mon-Sun)
- Time window definition (start/end times)
- Automatic time entry generation
- Active/inactive block management
- Date range activation windows

#### 13. **Real-time Updates**
- WebSocket support for live updates
- Cross-device timer synchronization
- Real-time dashboard updates
- Live collaboration features

---

## Project Management

### Core Project Features

#### 14. **Project Creation & Management**
- Unlimited projects
- Project name, description, and status
- Client association
- Project archiving and activation
- Project deletion (soft delete)

#### 15. **Project Details**
- Project dashboard with overview
- Time tracking summary
- Budget tracking
- Task list integration
- Team member assignments
- Project notes and documentation

#### 16. **Project Status Management**
- Active/Archived/Inactive status
- Status change history
- Bulk status updates
- Status-based filtering

#### 17. **Project Budgeting**
- Budget amount setting
- Budget consumption tracking
- Budget alerts and notifications
- Burn rate calculation
- Budget vs actual reporting
- Budget forecasting

#### 18. **Project Costs**
- Track direct project expenses
- Cost categories and descriptions
- Cost date tracking
- Cost amount and currency
- Cost reporting and analytics
- Integration with budget tracking

#### 19. **Extra Goods & Services**
- Add non-time-based line items to projects
- Product/service catalog
- Quantity and pricing
- Integration with invoicing
- Goods management per project

#### 20. **Project Favorites**
- Mark projects as favorites
- Quick access to favorite projects
- Favorite project dashboard widget
- Personal project organization

#### 21. **Project Export**
- CSV export of project data
- Time entry export per project
- Project report generation
- Bulk export capabilities

#### 22. **Project Dashboard**
- Visual project overview
- Time tracking charts
- Budget status indicators
- Task completion metrics
- Team activity feed
- Recent time entries

---

## Task Management

### Core Task Features

#### 23. **Task Creation & Management**
- Unlimited tasks per project
- Task name, description, and status
- Task priority levels (Low, Medium, High, Urgent)
- Task assignment to users
- Task due dates and deadlines
- Task tags and categorization

#### 24. **Task Status Tracking**
- Customizable status workflow
- Status-based filtering
- Bulk status updates
- Status change history
- Task completion tracking

#### 25. **Task Priorities**
- Priority level assignment
- Priority-based sorting
- Priority filtering
- Bulk priority updates
- Visual priority indicators

#### 26. **Task Assignment**
- Assign tasks to team members
- Multiple assignee support
- Assignment notifications
- "My Tasks" view
- Overdue tasks tracking

#### 27. **Task Comments**
- Threaded comments on tasks
- Comment editing and deletion
- @mention support
- Comment notifications
- Activity feed integration

#### 28. **Kanban Board**
- Visual drag-and-drop task management
- Customizable columns
- Column reordering
- Task movement between columns
- Column status mapping
- Board filtering and search
- Auto-refresh functionality

#### 29. **Task Board View**
- List view of tasks
- Table view with sorting
- Card view for visual management
- Task grouping options
- Customizable columns

#### 30. **Task Filtering & Search**
- Filter by project, status, priority, assignee
- Date range filtering
- Tag-based filtering
- Full-text search
- Saved filters

#### 31. **Task Export**
- CSV export of tasks
- Filtered export support
- Task detail export
- Bulk export capabilities

#### 32. **Task Activity Tracking**
- Automatic activity logging
- Status change tracking
- Assignment changes
- Comment activity
- Activity feed per task

#### 33. **Bulk Task Operations**
- Bulk delete tasks
- Bulk status updates
- Bulk priority changes
- Bulk assignment
- Bulk project move
- Multi-select task operations

---

## Client Management

### Core Client Features

#### 34. **Client Creation & Management**
- Unlimited clients
- Client name, company, and contact information
- Client address and billing details
- Client status (Active/Inactive)
- Client archiving

#### 35. **Client Details**
- Client dashboard
- Associated projects list
- Total time tracked
- Total revenue
- Invoice history
- Payment history

#### 36. **Client Notes**
- Internal notes about clients
- Note creation and editing
- Note history
- Private notes (admin only)
- Note search and filtering

#### 37. **Client Billing Rates**
- Per-client hourly rates
- Rate override per project
- Rate history tracking
- Multi-currency support
- Rate-based invoicing

#### 38. **Client Prepaid Consumption**
- Track prepaid hours/credits
- Automatic deduction from prepaid balance
- Prepaid balance reporting
- Prepaid expiration tracking

#### 39. **Client Export**
- CSV export of client data
- Client report generation
- Associated data export

---

## Invoicing & Billing

### Core Invoicing Features

#### 40. **Invoice Creation**
- Generate invoices from time entries
- Manual invoice creation
- Invoice templates
- Custom line items
- Multiple invoice formats

#### 41. **Invoice Management**
- Invoice list view with filtering
- Invoice status tracking (Draft, Sent, Paid, Overdue, Cancelled)
- Invoice editing
- Invoice duplication
- Invoice deletion
- Bulk invoice operations

#### 42. **Invoice Items**
- Time entry line items
- Expense line items
- Custom line items
- Item descriptions and quantities
- Unit prices and totals
- Tax calculation per item

#### 43. **Invoice Generation from Time**
- Select time entries for invoicing
- Automatic time entry grouping
- Billable hours calculation
- Rate application
- Time entry filtering

#### 44. **Invoice Templates**
- Customizable invoice templates
- Template selection per invoice
- Template editing
- Default template setting
- Template preview

#### 45. **PDF Invoice Export**
- Professional PDF generation
- Customizable PDF layout
- Company branding (logo)
- PDF template editor
- PDF preview
- PDF download

#### 46. **Invoice Status Management**
- Status workflow (Draft → Sent → Paid)
- Status change tracking
- Overdue invoice detection
- Bulk status updates
- Status-based filtering

#### 47. **Tax Calculation**
- Automatic tax calculation
- Multiple tax rates
- Tax rules per client/project
- Tax inclusion/exclusion
- Tax reporting

#### 48. **Multi-Currency Support**
- Multiple currency support
- Currency selection per invoice
- Exchange rate tracking
- Currency conversion
- Multi-currency reporting

#### 49. **Recurring Invoices**
- Recurring invoice templates
- Weekly, monthly, quarterly, yearly recurrence
- Automatic invoice generation
- Recurring invoice management
- Next generation date tracking

#### 50. **Invoice Email**
- Email invoice to clients
- Email template customization
- Email delivery tracking
- Email history
- Automated email sending

#### 51. **Invoice Numbering**
- Automatic invoice numbering
- Custom numbering format
- Number sequence management
- Number prefix/suffix

#### 52. **Invoice Export**
- CSV export of invoices
- Excel export
- PDF export
- Bulk export
- Filtered export

---

## Financial Management

### Expense Tracking

#### 53. **Expense Recording**
- Track business expenses
- Expense amount and currency
- Expense date tracking
- Vendor information
- Receipt attachment
- Expense categories

#### 54. **Expense Categories**
- Customizable expense categories
- Category management
- Category-based reporting
- Category filtering

#### 55. **Expense Approval Workflow**
- Multi-stage approval process
- Approval status tracking
- Admin approval required
- Approval notifications
- Approval history

#### 56. **Expense Reimbursement**
- Track reimbursement status
- Reimbursement amount tracking
- Reimbursement date
- Reimbursement method
- Reimbursement reporting

#### 57. **Billable Expenses**
- Mark expenses as billable
- Add billable expenses to invoices
- Expense markup
- Expense-to-invoice integration

#### 58. **Expense Filtering & Search**
- Filter by category, status, date range
- Vendor search
- Amount range filtering
- Billable/non-billable filter
- Receipt status filter

#### 59. **Expense Export**
- CSV export of expenses
- Expense report generation
- Category-based export

### Payment Tracking

#### 60. **Payment Recording**
- Record payments against invoices
- Payment amount and currency
- Payment date tracking
- Payment method tracking
- Payment reference numbers

#### 61. **Payment Methods**
- Bank transfer
- Cash
- Check
- Credit card
- Debit card
- PayPal
- Stripe
- Wire transfer
- Other methods

#### 62. **Payment Status**
- Payment status tracking (Completed, Pending, Failed, Refunded)
- Partial payment support
- Payment history per invoice
- Outstanding amount calculation

#### 63. **Payment Gateway Integration**
- Gateway transaction ID tracking
- Gateway fee recording
- Net amount calculation
- Gateway-specific fields

#### 64. **Payment Statistics**
- Payment summary statistics
- Payment method breakdown
- Payment status analytics
- Monthly payment trends
- Payment reporting

### Additional Financial Features

#### 65. **Mileage Tracking**
- Track business mileage
- Mileage rate calculation
- Mileage reimbursement
- Mileage reporting

#### 66. **Per Diem Tracking**
- Per diem rate management
- Per diem expense tracking
- Per diem reporting
- Rate configuration

---

## Reporting & Analytics

### Core Reporting Features

#### 67. **Time Reports**
- Time entry reports by project, user, date range
- Billable vs non-billable breakdown
- Time summary reports
- Detailed time reports
- Custom date ranges

#### 68. **Project Reports**
- Project time summary
- Project budget reports
- Project cost reports
- Project profitability analysis
- Project completion metrics

#### 69. **User Reports**
- Individual user time reports
- User productivity metrics
- User activity reports
- User performance comparison
- User time goals tracking

#### 70. **Invoice Reports**
- Invoice summary reports
- Payment reports
- Outstanding invoice reports
- Revenue reports
- Invoice status reports

#### 71. **Expense Reports**
- Expense summary by category
- Expense trends
- Reimbursement reports
- Billable expense reports

#### 72. **Saved Filters**
- Save frequently used report filters
- Quick filter application
- Filter sharing (admin)
- Filter management

#### 73. **Report Export**
- CSV export of reports
- Excel export
- PDF report generation
- Scheduled report emails

### Analytics Dashboard

#### 74. **Visual Dashboards**
- Charts and graphs for insights
- Time tracking visualizations
- Revenue charts
- Project status overview
- User activity metrics

#### 75. **Hours Analytics**
- Hours by day, week, month
- Hours by project
- Hours by user
- Hours by hour of day
- Billable vs non-billable charts

#### 76. **Revenue Analytics**
- Revenue trends over time
- Revenue by project
- Revenue by client
- Payment analytics
- Revenue vs payments comparison

#### 77. **Project Analytics**
- Project efficiency metrics
- Budget consumption trends
- Burn rate analysis
- Completion estimates
- Resource allocation analysis

#### 78. **Task Analytics**
- Task completion rates
- Task duration analysis
- Task priority distribution
- Task assignment metrics
- Task status trends

#### 79. **Overtime Tracking**
- Overtime hour calculation
- Overtime reporting
- Overtime trends
- Overtime alerts

#### 80. **Weekly Trends**
- Weekly time trends
- Week-over-week comparison
- Weekly goal tracking
- Weekly summary reports

#### 81. **Budget Alerts & Forecasting**
- Budget consumption monitoring
- Budget threshold alerts (80%, 100%)
- Over-budget alerts
- Burn rate calculation
- Completion date estimation
- Cost trend analysis
- Resource allocation breakdown

#### 82. **Weekly Time Goals**
- Set weekly hour targets
- Track progress against goals
- Goal status management (Active, Completed, Failed, Cancelled)
- Goal statistics and success rate
- Daily breakdown of goal progress
- Streak tracking

---

## User Management & Security

### User Management

#### 83. **User Accounts**
- User creation and management
- Username-based authentication
- User profiles with avatars
- User roles and permissions
- User activation/deactivation
- User deletion

#### 84. **Profile Management**
- User profile editing
- Avatar upload
- Profile picture management
- Personal settings
- Timezone preferences
- Language preferences

#### 85. **Role-Based Access Control (RBAC)**
- Granular permission system
- Custom roles creation
- Role assignment to users
- Permission categories
- System roles (Super Admin, Admin, Manager, User, Viewer)
- Permission checking in code and templates

#### 86. **Authentication Methods**
- Username-only authentication
- OIDC/SSO support (Azure AD, Authelia, etc.)
- Session management
- Secure cookie handling
- Session timeout configuration

#### 87. **API Tokens**
- Generate API tokens for integrations
- Token scopes and permissions
- Token expiration
- Token management
- Token security

#### 88. **User Preferences**
- Timezone settings
- Date format preferences
- Time format preferences
- Currency preferences
- Language selection
- Notification preferences

---

## Productivity Features

### Navigation & Search

#### 89. **Command Palette**
- Keyboard-driven navigation (press `?`)
- Quick action execution
- Search across all features
- Command shortcuts
- Context-aware commands

#### 90. **Keyboard Shortcuts**
- Global shortcuts (Ctrl+K for search, Ctrl+/ for command palette)
- Navigation shortcuts (g d for dashboard, g p for projects)
- Action shortcuts (c p for create project, t s for start timer)
- Table shortcuts (Ctrl+A for select all, Delete for delete)
- Editing shortcuts (Ctrl+S for save, Escape for close)
- Customizable shortcuts

#### 91. **Quick Search**
- Fast search across projects, tasks, clients
- Search suggestions
- Recent searches
- Search filters
- Keyboard shortcut: Ctrl+K

#### 92. **Activity Feed**
- Recent activity tracking
- Activity by user, project, task
- Activity filtering
- Activity notifications
- Activity history

### Notifications

#### 93. **Email Notifications**
- Configurable email alerts
- Task assignment notifications
- Invoice notifications
- Deadline reminders
- Weekly summaries

#### 94. **Toast Notifications**
- In-app notifications
- Success/error messages
- Action confirmations
- Real-time updates
- Notification history

#### 95. **Weekly Summaries**
- Optional weekly time tracking summaries
- Email delivery
- Summary customization
- Summary scheduling

---

## Administration

### System Administration

#### 96. **Admin Dashboard**
- System overview
- User management
- System settings
- Health monitoring
- Quick statistics

#### 97. **System Settings**
- Application configuration
- Timer settings (idle timeout, rounding)
- User management settings
- Security settings
- Email configuration
- Telemetry settings

#### 98. **User Management**
- Create, edit, delete users
- User role assignment
- User activation/deactivation
- User permission management
- User activity monitoring

#### 99. **Backup & Restore**
- Manual backup creation
- Scheduled backups
- Backup download
- Backup restoration
- Backup management

#### 100. **Logo & Branding**
- Company logo upload
- Logo management
- Logo removal
- Logo in PDF invoices
- Logo in email templates

#### 101. **PDF Layout Customization**
- Customizable PDF invoice layout
- PDF template editor
- Layout preview
- Default layout setting
- Layout reset

#### 102. **Email Configuration**
- SMTP server configuration
- Email template management
- Email sending test
- Email delivery status
- Email template editing

#### 103. **Telemetry Management**
- Telemetry enable/disable
- Telemetry data viewing
- Privacy settings
- Analytics configuration

#### 104. **Audit Logs**
- System activity logging
- User action tracking
- Entity change history
- Audit log filtering
- Audit log export

#### 105. **OIDC/SSO Configuration**
- OIDC provider setup
- SSO configuration
- User mapping
- OIDC debugging
- SSO testing

---

## Integration & API

### REST API

#### 106. **REST API v1**
- Comprehensive REST API
- Token-based authentication
- JSON request/response
- Pagination support
- Error handling

#### 107. **API Endpoints**
- Projects API (CRUD)
- Time Entries API (CRUD)
- Tasks API (CRUD)
- Clients API (CRUD)
- Invoices API (CRUD)
- Users API (read)
- Reports API

#### 108. **API Authentication**
- API token generation
- Bearer token authentication
- API key header authentication
- Token scopes
- Token permissions

#### 109. **API Documentation**
- OpenAPI/Swagger specification
- Interactive API docs
- Endpoint documentation
- Request/response examples
- Authentication guide

### Import/Export

#### 110. **Data Import**
- CSV import of time entries
- Project import
- Client import
- Task import
- Import validation
- Import error handling

#### 111. **Data Export**
- CSV export of all data types
- Excel export
- PDF export
- Bulk export
- Filtered export
- Scheduled exports

---

## Technical Features

### Deployment & Infrastructure

#### 112. **Docker Support**
- Docker Compose configuration
- Multiple deployment profiles
- Production-ready setup
- Development setup
- Local testing setup

#### 113. **Database Support**
- PostgreSQL for production
- SQLite for testing/development
- Database migrations (Alembic)
- Migration management
- Database backup/restore

#### 114. **HTTPS Support**
- Automatic HTTPS setup
- Self-signed certificates
- mkcert integration
- Manual certificate setup
- SSL/TLS configuration

#### 115. **Monitoring Stack**
- Prometheus metrics
- Grafana dashboards
- Loki log aggregation
- Promtail log shipping
- Health check endpoints

#### 116. **Internationalization (i18n)**
- Multiple language support
- Translation system
- Language switching
- Locale-based formatting
- Timezone handling

#### 117. **Progressive Web App (PWA)**
- Install as mobile app
- Offline support
- App manifest
- Service worker
- Mobile optimization

#### 118. **Responsive Design**
- Mobile-friendly interface
- Tablet optimization
- Desktop experience
- Touch-friendly controls
- Adaptive layouts

#### 119. **Real-time Features**
- WebSocket support
- Live timer updates
- Real-time notifications
- Cross-device sync
- Collaborative features

#### 120. **Performance**
- Database query optimization
- Caching strategies
- Lazy loading
- Pagination
- Efficient data loading

---

## Feature Summary by Category

### Time Tracking (13 features)
Timer management, manual entry, bulk entry, templates, calendar view, focus sessions, recurring blocks, idle detection, rounding, duplication, real-time updates

### Project Management (9 features)
Project CRUD, budgeting, costs, extra goods, favorites, export, dashboard, status management

### Task Management (11 features)
Task CRUD, Kanban board, comments, priorities, assignment, filtering, export, activity tracking, bulk operations

### Client Management (6 features)
Client CRUD, notes, billing rates, prepaid consumption, export

### Invoicing (13 features)
Invoice creation, templates, PDF export, status management, tax calculation, multi-currency, recurring invoices, email, numbering, export

### Financial Management (14 features)
Expense tracking, categories, approval workflow, reimbursement, billable expenses, payment tracking, methods, gateway integration, statistics, mileage, per diem

### Reporting & Analytics (16 features)
Time reports, project reports, user reports, invoice reports, expense reports, saved filters, dashboards, hours analytics, revenue analytics, project analytics, task analytics, overtime, weekly trends, budget alerts, forecasting, weekly goals

### User Management & Security (6 features)
User accounts, profiles, RBAC, authentication, API tokens, preferences

### Productivity (7 features)
Command palette, keyboard shortcuts, quick search, activity feed, email notifications, toast notifications, weekly summaries

### Administration (10 features)
Admin dashboard, system settings, user management, backup/restore, logo/branding, PDF layout, email configuration, telemetry, audit logs, OIDC/SSO

### Integration & API (6 features)
REST API, API endpoints, authentication, documentation, import, export

### Technical (9 features)
Docker, database support, HTTPS, monitoring, i18n, PWA, responsive design, real-time, performance

---

## Total Feature Count

**120+ Features** across 12 major categories

---

## Getting Started with Features

### For New Users
1. Start with **Time Tracking** - Learn to track your time
2. Create **Projects** - Organize your work
3. Set up **Clients** - Manage your relationships
4. Generate **Invoices** - Bill for your time
5. Explore **Reports** - Understand your productivity

### For Teams
1. Set up **User Management** - Add team members
2. Configure **Permissions** - Control access
3. Use **Task Management** - Assign and track work
4. Monitor **Analytics** - Track team performance
5. Set **Budget Alerts** - Manage project budgets

### For Administrators
1. Configure **System Settings** - Customize the application
2. Set up **Email** - Enable notifications
3. Configure **Backups** - Protect your data
4. Set up **HTTPS** - Secure your installation
5. Enable **Monitoring** - Track system health

---

## Related Documentation

- [Getting Started Guide](GETTING_STARTED.md)
- [Installation Guide](DOCKER_COMPOSE_SETUP.md)
- [API Documentation](REST_API.md)
- [Task Management](TASK_MANAGEMENT_README.md)
- [Invoice System](INVOICE_FEATURE_README.md)
- [Client Management](CLIENT_MANAGEMENT_README.md)
- [Expense Tracking](EXPENSE_TRACKING.md)
- [Payment Tracking](PAYMENT_TRACKING.md)
- [Budget Alerts](BUDGET_ALERTS_AND_FORECASTING.md)
- [Weekly Goals](WEEKLY_TIME_GOALS.md)
- [Advanced Permissions](ADVANCED_PERMISSIONS.md)

---

**Note:** This document is maintained to reflect all current features. For the most up-to-date feature list, refer to the main [README.md](../README.md) and individual feature documentation files.

