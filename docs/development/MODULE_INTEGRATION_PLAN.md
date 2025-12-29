# Module Integration & Visibility Control Plan

**Date:** 2025-01-27  
**Status:** Planning Phase

## Executive Summary

This document outlines a comprehensive plan to improve module integration in TimeTracker and implement a centralized system for enabling/disabling modules and menu items from admin settings. The goal is to create a more maintainable, flexible architecture that allows administrators to customize the application based on their needs.

---

## Current State Analysis

### Module Inventory

TimeTracker currently has **50+ modules/features** organized into the following categories:

#### Core Modules (Always Enabled)
- **Authentication** (`auth`) - Login, logout, profile
- **Dashboard** (`main`) - Main dashboard
- **Projects** (`projects`) - Project management
- **Time Tracking** (`timer`) - Time entry, timers
- **Tasks** (`tasks`) - Task management
- **Clients** (`clients`) - Client management

#### Optional Modules (Can Be Disabled)
1. **Calendar** (`calendar`) - Calendar view, integrations
2. **Project Templates** (`project_templates`) - Template system
3. **Gantt Chart** (`gantt`) - Gantt visualization
4. **Kanban Board** (`kanban`) - Kanban task board
5. **Weekly Goals** (`weekly_goals`) - Goal tracking
6. **Issues** (`issues`) - Issue/bug tracking
7. **CRM Features:**
   - **Quotes** (`quotes`) - Quote management
   - **Contacts** (`contacts`) - Contact management
   - **Deals** (`deals`) - Deal pipeline
   - **Leads** (`leads`) - Lead management
8. **Finance & Expenses:**
   - **Reports** (`reports`) - Standard reports
   - **Report Builder** (`custom_reports`) - Custom report builder
   - **Scheduled Reports** (`scheduled_reports`) - Automated reports
   - **Invoices** (`invoices`) - Invoice management
   - **Invoice Approvals** (`invoice_approvals`) - Approval workflow
   - **Recurring Invoices** (`recurring_invoices`) - Recurring billing
   - **Payments** (`payments`) - Payment tracking
   - **Payment Gateways** (`payment_gateways`) - Gateway integration
   - **Expenses** (`expenses`) - Expense tracking
   - **Mileage** (`mileage`) - Mileage tracking
   - **Per Diem** (`per_diem`) - Per diem expenses
   - **Budget Alerts** (`budget_alerts`) - Budget monitoring
9. **Inventory** (`inventory`) - Inventory management
10. **Analytics** (`analytics`) - Analytics dashboard
11. **Tools & Data:**
    - **Integrations** (`integrations`) - External integrations
    - **Import/Export** (`import_export`) - Data import/export
    - **Saved Filters** (`saved_filters`) - Filter management
12. **Admin Features:**
    - **User Management** (`admin`) - User administration
    - **Permissions** (`permissions`) - RBAC system
    - **Settings** (`settings`) - System settings
    - **Audit Logs** (`audit_logs`) - Activity logging
    - **Webhooks** (`webhooks`) - Webhook management
    - **Custom Fields** (`custom_field_definitions`) - Field definitions
    - **Link Templates** (`link_templates`) - Link templates
    - **Time Entry Templates** (`time_entry_templates`) - Time templates
13. **Advanced Features:**
    - **Workflows** (`workflows`) - Automation workflows
    - **Time Approvals** (`time_approvals`) - Time approval workflow
    - **Activity Feed** (`activity_feed`) - Activity stream
    - **Recurring Tasks** (`recurring_tasks`) - Automated tasks
    - **Team Chat** (`team_chat`) - Team messaging
    - **Client Portal** (`client_portal`) - Client-facing portal
    - **Kiosk Mode** (`kiosk`) - Kiosk interface

### Current Architecture Issues

1. **No Centralized Module Registry**
   - Blueprints registered directly in `app/__init__.py`
   - No single source of truth for module metadata
   - Hard to track module dependencies

2. **Inconsistent Visibility Control**
   - Some modules have `ui_allow_*` flags in Settings
   - Some modules have `ui_show_*` flags in User
   - Many modules have no flags at all
   - No route-level protection

3. **Complex Navigation Logic**
   - Navigation menu has hardcoded endpoint checks
   - Conditional rendering scattered throughout templates
   - Difficult to add/remove menu items

4. **Missing Module Flags**
   - CRM features (deals, leads, contacts) have no flags
   - Many admin features have no flags
   - Advanced features have no flags

5. **No Module Dependencies**
   - No way to express that one module depends on another
   - No validation when disabling modules

---

## Proposed Solution

### Phase 1: Module Registry System

Create a centralized module registry that defines:
- Module metadata (name, description, category)
- Dependencies between modules
- Default visibility settings
- Route associations

**File:** `app/utils/module_registry.py`

```python
from dataclasses import dataclass
from typing import List, Optional, Dict
from enum import Enum

class ModuleCategory(Enum):
    CORE = "core"
    TIME_TRACKING = "time_tracking"
    PROJECT_MANAGEMENT = "project_management"
    CRM = "crm"
    FINANCE = "finance"
    INVENTORY = "inventory"
    ANALYTICS = "analytics"
    TOOLS = "tools"
    ADMIN = "admin"
    ADVANCED = "advanced"

@dataclass
class ModuleDefinition:
    id: str
    name: str
    description: str
    category: ModuleCategory
    blueprint_name: str
    default_enabled: bool = True
    requires_admin: bool = False
    dependencies: List[str] = None  # Module IDs this depends on
    settings_flag: Optional[str] = None  # Settings.ui_allow_* field name
    user_flag: Optional[str] = None  # User.ui_show_* field name
    routes: List[str] = None  # Route endpoints
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.routes is None:
            self.routes = []

class ModuleRegistry:
    _modules: Dict[str, ModuleDefinition] = {}
    
    @classmethod
    def register(cls, module: ModuleDefinition):
        cls._modules[module.id] = module
    
    @classmethod
    def get(cls, module_id: str) -> Optional[ModuleDefinition]:
        return cls._modules.get(module_id)
    
    @classmethod
    def get_all(cls) -> Dict[str, ModuleDefinition]:
        return cls._modules.copy()
    
    @classmethod
    def get_by_category(cls, category: ModuleCategory) -> List[ModuleDefinition]:
        return [m for m in cls._modules.values() if m.category == category]
    
    @classmethod
    def is_enabled(cls, module_id: str, settings, user) -> bool:
        """Check if a module is enabled for a user"""
        module = cls.get(module_id)
        if not module:
            return False
        
        # Check system-wide setting
        if module.settings_flag:
            if not getattr(settings, module.settings_flag, True):
                return False
        
        # Check user-specific setting
        if module.user_flag:
            if not getattr(user, module.user_flag, True):
                return False
        
        # Check dependencies
        for dep_id in module.dependencies:
            if not cls.is_enabled(dep_id, settings, user):
                return False
        
        return True
```

### Phase 2: Add Missing UI Flags

Add missing `ui_allow_*` flags to Settings model and `ui_show_*` flags to User model for all modules.

**Settings Model Additions:**
```python
# CRM section (missing)
ui_allow_contacts = db.Column(db.Boolean, default=True, nullable=False)
ui_allow_deals = db.Column(db.Boolean, default=True, nullable=False)
ui_allow_leads = db.Column(db.Boolean, default=True, nullable=False)

# Admin section (missing)
ui_allow_workflows = db.Column(db.Boolean, default=True, nullable=False)
ui_allow_time_approvals = db.Column(db.Boolean, default=True, nullable=False)
ui_allow_activity_feed = db.Column(db.Boolean, default=True, nullable=False)
ui_allow_recurring_tasks = db.Column(db.Boolean, default=True, nullable=False)
ui_allow_team_chat = db.Column(db.Boolean, default=True, nullable=False)
ui_allow_client_portal = db.Column(db.Boolean, default=True, nullable=False)
ui_allow_kiosk = db.Column(db.Boolean, default=True, nullable=False)
```

**User Model Additions:**
```python
# CRM section (missing)
ui_show_contacts = db.Column(db.Boolean, default=True, nullable=False)
ui_show_deals = db.Column(db.Boolean, default=True, nullable=False)
ui_show_leads = db.Column(db.Boolean, default=True, nullable=False)

# Admin section (missing)
ui_show_workflows = db.Column(db.Boolean, default=True, nullable=False)
ui_show_time_approvals = db.Column(db.Boolean, default=True, nullable=False)
ui_show_activity_feed = db.Column(db.Boolean, default=True, nullable=False)
ui_show_recurring_tasks = db.Column(db.Boolean, default=True, nullable=False)
ui_show_team_chat = db.Column(db.Boolean, default=True, nullable=False)
ui_show_client_portal = db.Column(db.Boolean, default=True, nullable=False)
ui_show_kiosk = db.Column(db.Boolean, default=True, nullable=False)
```

### Phase 3: Module Checking Utilities

Create utilities for checking module availability in routes and templates.

**File:** `app/utils/module_helpers.py`

```python
from functools import wraps
from flask import abort, redirect, url_for, current_app
from flask_login import current_user
from app.models import Settings
from app.utils.module_registry import ModuleRegistry

def module_enabled(module_id: str):
    """Decorator to require a module to be enabled"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            settings = Settings.get_settings()
            if not ModuleRegistry.is_enabled(module_id, settings, current_user):
                if current_user.is_admin:
                    flash(f"Module '{module_id}' is disabled. Enable it in Settings.", "warning")
                    return redirect(url_for('admin.settings'))
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def is_module_enabled(module_id: str) -> bool:
    """Check if a module is enabled for current user"""
    if not current_user.is_authenticated:
        return False
    settings = Settings.get_settings()
    return ModuleRegistry.is_enabled(module_id, settings, current_user)

# Template helper
def init_module_helpers(app):
    @app.context_processor
    def inject_module_helpers():
        return {
            "is_module_enabled": is_module_enabled,
            "get_modules_by_category": lambda cat: ModuleRegistry.get_by_category(cat),
        }
```

### Phase 4: Route Protection

Add route decorators to protect routes based on module flags.

**Example:**
```python
@calendar_bp.route("/calendar")
@login_required
@module_enabled("calendar")
def view_calendar():
    # Route implementation
    pass
```

### Phase 5: Navigation Refactoring

Refactor navigation menu to use module registry instead of hardcoded checks.

**Benefits:**
- Centralized menu structure
- Automatic menu item visibility
- Easier to add/remove items
- Consistent behavior

**File:** `app/utils/navigation.py`

```python
from app.utils.module_registry import ModuleRegistry, ModuleCategory
from app.models import Settings
from flask_login import current_user

def build_navigation_menu(settings, user):
    """Build navigation menu structure from module registry"""
    menu = {
        "dashboard": {"enabled": True, "items": []},
        "calendar": {"enabled": False, "items": []},
        "time_tracking": {"enabled": True, "items": []},
        "crm": {"enabled": False, "items": []},
        "finance": {"enabled": False, "items": []},
        "inventory": {"enabled": False, "items": []},
        "analytics": {"enabled": False, "items": []},
        "tools": {"enabled": False, "items": []},
        "admin": {"enabled": False, "items": []},
    }
    
    # Populate menu from module registry
    for module in ModuleRegistry.get_all().values():
        if ModuleRegistry.is_enabled(module.id, settings, user):
            category_key = module.category.value
            if category_key in menu:
                menu[category_key]["enabled"] = True
                menu[category_key]["items"].append({
                    "id": module.id,
                    "name": module.name,
                    "url": url_for(f"{module.blueprint_name}.index") if hasattr(module, "index_route") else None,
                })
    
    return menu
```

### Phase 6: Admin UI for Module Management

Create admin interface to manage module visibility.

**Route:** `app/routes/admin.py`

```python
@admin_bp.route("/admin/modules", methods=["GET", "POST"])
@login_required
@admin_required
def manage_modules():
    """Manage module visibility settings"""
    settings = Settings.get_settings()
    
    if request.method == "POST":
        # Update module flags
        for module_id in ModuleRegistry.get_all().keys():
            flag_name = f"ui_allow_{module_id}"
            if hasattr(settings, flag_name):
                setattr(settings, flag_name, request.form.get(flag_name) == "on")
        
        db.session.commit()
        flash("Module settings updated successfully", "success")
        return redirect(url_for("admin.manage_modules"))
    
    # Group modules by category
    modules_by_category = {}
    for category in ModuleCategory:
        modules_by_category[category] = ModuleRegistry.get_by_category(category)
    
    return render_template("admin/modules.html", 
                         modules_by_category=modules_by_category,
                         settings=settings)
```

**Template:** `app/templates/admin/modules.html`

- Checkboxes for each module
- Category grouping
- Dependency warnings
- Save button

### Phase 7: Database Migration

Create Alembic migration to add missing columns.

**File:** `migrations/versions/XXXX_add_module_visibility_flags.py`

```python
def upgrade():
    # Add Settings columns
    op.add_column('settings', sa.Column('ui_allow_contacts', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('settings', sa.Column('ui_allow_deals', sa.Boolean(), nullable=False, server_default='true'))
    # ... etc
    
    # Add User columns
    op.add_column('users', sa.Column('ui_show_contacts', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('users', sa.Column('ui_show_deals', sa.Boolean(), nullable=False, server_default='true'))
    # ... etc
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1)
- [ ] Create module registry system
- [ ] Define all module definitions
- [ ] Create module checking utilities
- [ ] Add route decorators

### Phase 2: Database & Models (Week 1-2)
- [ ] Create Alembic migration for missing flags
- [ ] Update Settings model
- [ ] Update User model
- [ ] Test migration

### Phase 3: Route Protection (Week 2)
- [ ] Add `@module_enabled` decorator to all optional routes
- [ ] Test route protection
- [ ] Handle edge cases

### Phase 4: Navigation Refactoring (Week 2-3)
- [ ] Create navigation builder utility
- [ ] Refactor base.html to use module registry
- [ ] Test navigation visibility

### Phase 5: Admin UI (Week 3)
- [ ] Create admin module management page
- [ ] Add dependency validation
- [ ] Test admin interface

### Phase 6: Testing & Documentation (Week 3-4)
- [ ] Write unit tests
- [ ] Write integration tests
- [ ] Update documentation
- [ ] Create migration guide

---

## Module Dependencies

### Critical Dependencies
- **Invoices** → **Projects** (required)
- **Payments** → **Invoices** (required)
- **Expenses** → **Projects** (optional, but recommended)
- **Tasks** → **Projects** (optional, but recommended)
- **Time Entries** → **Projects** (required)

### Feature Dependencies
- **Invoice Approvals** → **Invoices**
- **Recurring Invoices** → **Invoices**
- **Payment Gateways** → **Payments**
- **Budget Alerts** → **Projects**
- **Kanban Board** → **Tasks**
- **Gantt Chart** → **Tasks**
- **Deals** → **Clients**
- **Leads** → **Clients**
- **Contacts** → **Clients**

---

## Benefits

1. **Centralized Management**
   - Single source of truth for module metadata
   - Easy to add/remove modules
   - Clear dependency tracking

2. **Better User Experience**
   - Admins can customize application
   - Users see only relevant features
   - Cleaner navigation

3. **Maintainability**
   - Less code duplication
   - Easier to test
   - Clearer architecture

4. **Flexibility**
   - Easy to add new modules
   - Easy to change module behavior
   - Support for module plugins (future)

---

## Risks & Mitigation

### Risk 1: Breaking Existing Functionality
**Mitigation:** 
- Comprehensive testing
- Gradual rollout
- Feature flags for new system

### Risk 2: Performance Impact
**Mitigation:**
- Cache module registry
- Optimize database queries
- Lazy loading where possible

### Risk 3: Migration Complexity
**Mitigation:**
- Thorough migration testing
- Rollback plan
- Data validation

---

## Success Criteria

1. ✅ All modules have visibility flags
2. ✅ Admin can disable any module from settings
3. ✅ Routes are protected by module flags
4. ✅ Navigation automatically reflects module state
5. ✅ Module dependencies are enforced
6. ✅ All tests pass
7. ✅ Documentation is updated

---

## Future Enhancements

1. **Module Plugins**
   - Support for third-party modules
   - Module marketplace

2. **Module Permissions**
   - Fine-grained permissions per module
   - Role-based module access

3. **Module Analytics**
   - Track module usage
   - Identify unused modules

4. **Module Templates**
   - Pre-configured module sets
   - Industry-specific configurations

---

## References

- Current Settings Model: `app/models/settings.py`
- Current User Model: `app/models/user.py`
- Navigation Template: `app/templates/base.html`
- Blueprint Registration: `app/__init__.py`

---

**Next Steps:**
1. Review and approve this plan
2. Create module registry implementation
3. Begin Phase 1 implementation

