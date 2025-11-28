# Getting Started with TimeTracker

A complete guide to get you up and running with TimeTracker in minutes.

---

## 📋 Table of Contents

1. [Installation](#-installation)
2. [First Login](#-first-login)
3. [Initial Setup](#-initial-setup)
4. [Core Workflows](#-core-workflows)
5. [Next Steps](#-next-steps)

---

## 🚀 Installation

### Option 1: Docker (Recommended)

The fastest way to get TimeTracker running:

```bash
# 1. Clone the repository
git clone https://github.com/drytrix/TimeTracker.git
cd TimeTracker

# 2. Set a strong SECRET_KEY (required for sessions & CSRF)
# Linux/macOS:
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
# Windows PowerShell:
$env:SECRET_KEY = python -c "import secrets; print(secrets.token_hex(32))"

# 3. (Optional) Set admin usernames
# Linux/macOS:
export ADMIN_USERNAMES=admin,manager
# Windows PowerShell:
$env:ADMIN_USERNAMES = "admin,manager"

# 4. Start TimeTracker
docker-compose up -d

# 5. Access the application
# Open your browser to: https://localhost
# (Self‑signed certificate; your browser will show a warning the first time.)

# Prefer plain HTTP on port 8080 instead?
# Use the example compose that publishes the app directly:
# docker-compose -f docker-compose.example.yml up -d
# Then open: http://localhost:8080

# Note: Login with the username you set in ADMIN_USERNAMES (default: admin) to get admin access
```

**That's it!** TimeTracker is now running with PostgreSQL.

> Important: The default `docker-compose.yml` expects `SECRET_KEY` to be set. You can also edit the file and replace `SECRET_KEY=your-secret-key-here` with a securely generated value. Never use weak or guessable keys.

### Option 2: Quick Test (SQLite)

Want to try it without setting up a database?

```bash
# Start with SQLite (no database setup needed)
docker-compose -f docker-compose.local-test.yml up --build

# Access at: http://localhost:8080
```

Perfect for testing and development!

### Option 3: Manual Installation

For advanced users who prefer manual setup:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp env.example .env
# Edit .env with your settings

# 3. Initialize database
python -c "from app import create_app; app = create_app(); app.app_context().push(); app.initialize_database()"

# 4. Run the application
python app.py
```

**📖 See [Requirements](REQUIREMENTS.md) for detailed system requirements**

---

## 🔑 First Login

1. **Open TimeTracker** in your browser: `http://localhost:8080`

2. **Enter your credentials** (depends on authentication method configured)
   - **Default (`AUTH_METHOD=local`)**: Enter username and password
   - **No authentication (`AUTH_METHOD=none`)**: Enter username only (no password)
   - **OIDC (`AUTH_METHOD=oidc`)**: Click "Sign in with SSO" button
   - **Both (`AUTH_METHOD=both`)**: Choose either SSO or local username/password

3. **Admin users are configured in the environment**
   - Set via `ADMIN_USERNAMES` environment variable (default: `admin`)
   - When you login with a username matching the list, you get admin role
   - Example: If `ADMIN_USERNAMES=admin,manager`, logging in as "admin" or "manager" gives admin access

4. **You're in!** Welcome to your dashboard

> **Note**: Authentication method is configured via the `AUTH_METHOD` environment variable:
> - `none`: Username only (for trusted internal networks)
> - `local`: Username + password (default, recommended)
> - `oidc`: Single Sign-On only
> - `both`: Both OIDC and local password authentication
> 
> See [OIDC Setup Guide](OIDC_SETUP.md#5-authentication-methods) for detailed explanations of all authentication modes.

---

## ⚙️ Initial Setup

### Step 1: Configure System Settings

> **Important**: You need admin access for this step. Login with a username from `ADMIN_USERNAMES` (default: `admin`).

1. Go to **Admin → Settings** (in the left sidebar menu, expand "Admin", then click "Settings")

The Admin Settings page has multiple sections. Configure what you need:

#### General Settings
- **Timezone**: Your local timezone (e.g., `America/New_York`, `Europe/Rome`)
- **Currency**: Your preferred currency (e.g., `USD`, `EUR`, `GBP`)

#### Timer Settings
- **Rounding (Minutes)**: Round to nearest 1/5/15 minutes
- **Idle Timeout (Minutes)**: Auto-pause after idle (default: 30)
- **Single Active Timer**: Allow only one running timer per user

#### User Management
- **Allow Self-Registration**: ☑ Enable this to let users create accounts by entering any username on the login page
- **Note**: Admin users are set via `ADMIN_USERNAMES` environment variable, not in this UI

#### Company Branding
- **Company Name**: Your company or business name
- **Company Email**: Contact email for invoices
- **Company Phone**: Contact phone number
- **Company Website**: Your website URL
- **Company Address**: Your billing address (multi-line)
- **Tax ID**: Optional tax identification number
- **Bank Information**: Optional bank account details for invoices
- **Company Logo**: Upload your logo (PNG, JPG, GIF, SVG, WEBP)

#### Invoice Defaults
- **Invoice Prefix**: Prefix for invoice numbers (e.g., `INV`)
- **Invoice Start Number**: Starting number for invoices (e.g., 1000)
- **Default Payment Terms**: Terms text (e.g., "Payment due within 30 days")
- **Default Invoice Notes**: Footer notes (e.g., "Thank you for your business!")

#### Additional Settings
- **Backup Settings**: Retention days and backup time
- **Export Settings**: CSV delimiter preference
- **Privacy & Analytics**: Allow analytics to help improve the application

2. **Click "Save Settings"** at the bottom to apply all changes

> **💡 Tip**: Don't confuse this with the **Settings** option in your account dropdown (top right) - that's for personal/user preferences. System-wide settings are in **Admin → Settings** in the left sidebar.

### Step 2: Add Your First Client

1. Navigate to **Clients → Create Client**

2. **Enter client information**:
   - **Name**: Client or company name (required)
   - **Contact Person**: Primary contact
   - **Email**: Client email address
   - **Phone**: Contact number
   - **Address**: Billing address

3. **Set billing defaults**:
   - **Default Hourly Rate**: Your rate for this client (e.g., `100.00`)
   - This will auto-populate when creating projects

4. **Click Create** to save the client

### Step 3: Create Your First Project

1. Go to **Projects → Create Project**

2. **Basic information**:
   - **Name**: Project name (required)
   - **Client**: Select from dropdown (auto-filled with client info)
   - **Description**: Brief project description

3. **Billing information**:
   - **Billable**: Toggle on if you'll invoice this project
   - **Hourly Rate**: Auto-filled from client (can override)
   - **Estimated Hours**: Optional project estimate

4. **Advanced settings** (optional):
   - **Status**: Active/Archived
   - **Start/End Dates**: Project timeline
   - **Budget Alert Threshold**: Get notified at X% budget used

5. **Click Create** to save the project

### Step 4: Create Tasks (Optional)

Break your project into manageable tasks:

1. Go to **Tasks → Create Task**

2. **Task details**:
   - **Project**: Select your project
   - **Name**: Task name (e.g., "Design homepage")
   - **Description**: What needs to be done
   - **Priority**: Low/Medium/High/Urgent

3. **Planning**:
   - **Estimated Hours**: Time estimate for this task
   - **Due Date**: When it should be completed
   - **Assign To**: Team member responsible

4. **Click Create** to save the task

---

## 🎯 Core Workflows

### Workflow 1: Track Time with Timer

**Quick time tracking for active work:**

1. **On the Dashboard**, find the timer section
2. **Select a project** (and optionally a task)
3. **Click Start** — the timer begins
4. **Work on your task** — timer continues even if you close the browser
5. **Click Stop** when finished — time entry is saved automatically

**💡 Tip**: The timer runs on the server, so it keeps going even if you:
- Close your browser
- Switch devices
- Lose internet connection temporarily

### Workflow 2: Manual Time Entry

**Add historical or bulk time entries:**

1. Go to **Timer → Log Time**

2. **Choose entry type**:
   - Single entry
   - Bulk entry (multiple entries at once)
   - Calendar view (visual entry)

3. **Fill in details**:
   - **Project**: Required
   - **Task**: Optional
   - **Start Time**: When you started
   - **End Time**: When you finished
   - **Notes**: What you worked on
   - **Tags**: Categorize your work (e.g., `design`, `meeting`, `bugfix`)

4. **Click Save** to record the entry

### Workflow 3: Generate an Invoice

**Turn tracked time into a professional invoice:**

1. Go to **Invoices → Create Invoice**

2. **Select project** and fill in client details
   - Client info auto-populated from project

3. **Set invoice details**:
   - **Issue Date**: Today (default)
   - **Due Date**: Payment deadline (e.g., 30 days)
   - **Tax Rate**: Your tax rate (e.g., `21.00` for 21%)

4. **Click "Generate from Time Entries"**:
   - Select time entries to bill
   - Choose grouping (by task or project)
   - Preview the total

5. **Review and customize**:
   - Edit descriptions
   - Add manual line items
   - Adjust quantities or rates

6. **Save and send**:
   - Status: Draft → Sent → Paid
   - Export as CSV
   - (PDF export coming soon!)

### Workflow 4: View Reports

**Analyze your time and productivity:**

1. Go to **Reports**

2. **Choose report type**:
   - **Project Report**: Time breakdown by project
   - **User Report**: Individual productivity
   - **Summary Report**: Overall statistics

3. **Set filters**:
   - **Date Range**: Today/This Week/This Month/Custom
   - **Project**: Specific project or all
   - **User**: Specific user or all
   - **Billable**: Billable only/Non-billable only/Both

4. **View insights**:
   - Total hours worked
   - Billable vs non-billable
   - Time distribution
   - Estimated costs

5. **Export data**:
   - Click **Export CSV** for spreadsheet analysis
   - Choose delimiter (comma, semicolon, tab)

---

## 🎓 Next Steps

### Learn Advanced Features

- **[Task Management](TASK_MANAGEMENT_README.md)** — Master task boards and workflows
- **[Calendar View](CALENDAR_FEATURES_README.md)** — Visual time entry and planning
- **[Command Palette](COMMAND_PALETTE_USAGE.md)** — Keyboard shortcuts for power users
- **[Bulk Operations](BULK_TIME_ENTRY_README.md)** — Batch time entry creation

### Customize Your Experience

- **Company branding**: Upload your logo and set company info in Admin → Settings
- **Configure notifications** for task due dates
- **Set up recurring time blocks** for regular tasks
- **Create saved filters** for common report views
- **Add custom tags** for better categorization

### Team Setup

If you're setting up for a team:

1. **Add team members**:
   - **Self-registration** (recommended): Enable in Admin → Settings → "Allow Self-Registration"
   - **Admin creates users**: Go to Admin → Users → Create User
   - **Admin roles**: Set via `ADMIN_USERNAMES` environment variable (comma-separated list)
   - Regular users can be assigned Manager or User roles via Admin → Users → Edit

2. **Assign projects**:
   - Projects are visible to all users
   - Use permissions to control access (coming soon)

3. **Assign tasks**:
   - Create tasks and assign to team members
   - Set priorities and due dates
   - Track progress in task board

4. **Review reports**:
   - See team productivity
   - Identify bottlenecks
   - Optimize resource allocation

### Production Deployment

Ready to deploy for real use?

1. **Use PostgreSQL** instead of SQLite:
   ```bash
   # Edit .env file
   DATABASE_URL=postgresql://user:pass@localhost:5432/timetracker
   ```

2. **Set a secure secret key and admin users**:
   ```bash
   # Generate a random key
   SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')
   
   # Set admin usernames (comma-separated)
   ADMIN_USERNAMES=admin,yourusername
   ```

3. **Configure for production**:
   ```bash
   FLASK_ENV=production
   FLASK_DEBUG=false
   SESSION_COOKIE_SECURE=true
   REMEMBER_COOKIE_SECURE=true
   ```

4. **Set up backups**:
   - Configure automatic database backups
   - Store backups off-site
   - Test restore procedures

5. **Optional: Add reverse proxy**:
   - Use Caddy or nginx for HTTPS
   - Add authentication layer if needed
   - Configure firewall rules

**📖 See [Docker Public Setup](DOCKER_PUBLIC_SETUP.md) for production deployment**

---

## 💡 Tips & Tricks

### Keyboard Shortcuts

Press `Ctrl+K` (or `Cmd+K` on Mac) to open the command palette:

- Quickly start/stop timers
- Navigate to any page
- Search projects and tasks
- Log time entries

### Mobile Access

TimeTracker is fully responsive:

- Access from any device
- Mobile-optimized interface
- Touch-friendly controls
- Works in any browser

### Time Entry Best Practices

1. **Add descriptive notes** — Future you will thank you
2. **Use consistent tags** — Makes reporting easier
3. **Track regularly** — Don't let entries pile up
4. **Review weekly** — Catch missing time or errors
5. **Categorize accurately** — Billable vs non-billable matters

### Project Management Tips

1. **Set realistic estimates** — Helps with planning
2. **Break into tasks** — Makes tracking easier
3. **Use task priorities** — Focus on what matters
4. **Review progress regularly** — Stay on track
5. **Archive completed projects** — Keep your list clean

---

## ❓ Common Questions

### How do I reset my database?

```bash
# ⚠️ This deletes all data
docker-compose down -v
docker-compose up -d
```

### How do I add more users?

- **Enable self-registration**: In Admin → Settings, enable "Allow Self-Registration" - then anyone can create an account by entering a username on the login page
- **Admin creates users**: In Admin → Users → Create User (requires admin access)
- **Users in ADMIN_USERNAMES**: Any username listed in the `ADMIN_USERNAMES` environment variable will automatically get admin role when they login

### Can I export my data?

Yes! Multiple export options:
- **CSV export** from reports
- **Database backup** via scripts
- **API access** for custom integrations (coming soon)

### How do I upgrade TimeTracker?

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose up -d --build

# Migrations run automatically
```

### Is there a mobile app?

TimeTracker is a web application that works great on mobile browsers. A Progressive Web App (PWA) version with offline support is planned.

---

## 🆘 Need Help?

- **[Documentation](README.md)** — Complete documentation index
- **[Troubleshooting](DOCKER_STARTUP_TROUBLESHOOTING.md)** — Fix common issues
- **[GitHub Issues](https://github.com/drytrix/TimeTracker/issues)** — Report bugs or request features
- **[Contributing](CONTRIBUTING.md)** — Help improve TimeTracker

---

<div align="center">

**Ready to track your time like a pro?** 🚀

[← Back to Main README](../README.md) | [View All Documentation](README.md)

</div>

