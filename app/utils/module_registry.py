"""
Module Registry System

Centralized registry for managing module metadata, dependencies, and visibility.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum


class ModuleCategory(Enum):
    """Module categories for organization"""
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
    """Definition of a module with its metadata and configuration"""
    id: str
    name: str
    description: str
    category: ModuleCategory
    blueprint_name: str
    default_enabled: bool = True
    requires_admin: bool = False
    dependencies: List[str] = field(default_factory=list)  # Module IDs this depends on
    routes: List[str] = field(default_factory=list)  # Route endpoints
    icon: Optional[str] = None  # FontAwesome icon class
    order: int = 0  # Display order in navigation
    
    def __post_init__(self):
        """Validate and normalize module definition"""
        if self.dependencies is None:
            self.dependencies = []
        if self.routes is None:
            self.routes = []


class ModuleRegistry:
    """Centralized registry for all application modules"""
    
    _modules: Dict[str, ModuleDefinition] = {}
    _initialized: bool = False
    
    @classmethod
    def register(cls, module: ModuleDefinition):
        """Register a module definition"""
        cls._modules[module.id] = module
    
    @classmethod
    def get(cls, module_id: str) -> Optional[ModuleDefinition]:
        """Get a module definition by ID"""
        return cls._modules.get(module_id)
    
    @classmethod
    def get_all(cls) -> Dict[str, ModuleDefinition]:
        """Get all registered modules"""
        return cls._modules.copy()
    
    @classmethod
    def get_by_category(cls, category: ModuleCategory) -> List[ModuleDefinition]:
        """Get all modules in a specific category, sorted by order"""
        modules = [m for m in cls._modules.values() if m.category == category]
        return sorted(modules, key=lambda m: m.order)
    
    @classmethod
    def is_enabled(cls, module_id: str, settings=None, user=None) -> bool:
        """
        Check if a module is enabled for a user.
        
        Args:
            module_id: The module ID to check
            settings: Settings instance (deprecated, kept for backwards compatibility)
            user: User instance (optional, will use current_user if not provided)
        
        Returns:
            True if module is enabled, False otherwise
        """
        module = cls.get(module_id)
        if not module:
            return False
        
        # Core modules are always enabled
        if module.category == ModuleCategory.CORE:
            return True
        
        # Admin-only modules require admin access
        if module.requires_admin:
            if user is None:
                from flask_login import current_user
                user = current_user
            if not user or not getattr(user, 'is_authenticated', False):
                return False
            if not getattr(user, 'is_admin', False):
                return False
        
        # Check dependencies recursively
        for dep_id in module.dependencies:
            if not cls.is_enabled(dep_id, settings, user):
                return False

        # Admin-disabled modules (settings.disabled_module_ids)
        if settings:
            disabled = getattr(settings, "disabled_module_ids", None) or []
            if isinstance(disabled, list) and module_id in disabled:
                return False

        return True
    
    @classmethod
    def get_enabled_modules(cls, settings=None, user=None) -> List[ModuleDefinition]:
        """Get all enabled modules for a user"""
        enabled = []
        for module in cls._modules.values():
            if cls.is_enabled(module.id, settings, user):
                enabled.append(module)
        return sorted(enabled, key=lambda m: (m.category.value, m.order))
    
    @classmethod
    def initialize_defaults(cls):
        """Initialize the registry with all default module definitions"""
        if cls._initialized:
            return
        
        # Core modules (always enabled)
        cls.register(ModuleDefinition(
            id="auth",
            name="Authentication",
            description="User authentication and profile management",
            category=ModuleCategory.CORE,
            blueprint_name="auth",
            default_enabled=True,
            icon="fa-user-circle",
            order=0
        ))
        
        cls.register(ModuleDefinition(
            id="main",
            name="Dashboard",
            description="Main dashboard",
            category=ModuleCategory.CORE,
            blueprint_name="main",
            default_enabled=True,
            icon="fa-tachometer-alt",
            order=1
        ))
        
        cls.register(ModuleDefinition(
            id="projects",
            name="Projects",
            description="Project management",
            category=ModuleCategory.CORE,
            blueprint_name="projects",
            default_enabled=True,
            icon="fa-folder",
            order=2
        ))
        
        cls.register(ModuleDefinition(
            id="timer",
            name="Time Tracking",
            description="Time entry and timer management",
            category=ModuleCategory.CORE,
            blueprint_name="timer",
            default_enabled=True,
            icon="fa-clock",
            order=3
        ))
        
        cls.register(ModuleDefinition(
            id="tasks",
            name="Tasks",
            description="Task management",
            category=ModuleCategory.CORE,
            blueprint_name="tasks",
            default_enabled=True,
            dependencies=["projects"],
            icon="fa-tasks",
            order=4
        ))
        
        cls.register(ModuleDefinition(
            id="clients",
            name="Clients",
            description="Client management",
            category=ModuleCategory.CORE,
            blueprint_name="clients",
            default_enabled=True,
            icon="fa-users",
            order=5
        ))
        
        # Time Tracking Features
        cls.register(ModuleDefinition(
            id="calendar",
            name="Calendar",
            description="Calendar view and integrations",
            category=ModuleCategory.TIME_TRACKING,
            blueprint_name="calendar",
            default_enabled=True,
            icon="fa-calendar-alt",
            order=10
        ))
        
        cls.register(ModuleDefinition(
            id="project_templates",
            name="Project Templates",
            description="Project template system",
            category=ModuleCategory.PROJECT_MANAGEMENT,
            blueprint_name="project_templates",
            default_enabled=True,
            dependencies=["projects"],
            icon="fa-layer-group",
            order=11
        ))
        
        cls.register(ModuleDefinition(
            id="gantt",
            name="Gantt Chart",
            description="Gantt chart visualization",
            category=ModuleCategory.PROJECT_MANAGEMENT,
            blueprint_name="gantt",
            default_enabled=True,
            dependencies=["tasks"],
            icon="fa-project-diagram",
            order=12
        ))
        
        cls.register(ModuleDefinition(
            id="kanban",
            name="Kanban Board",
            description="Kanban task board",
            category=ModuleCategory.PROJECT_MANAGEMENT,
            blueprint_name="kanban",
            default_enabled=True,
            dependencies=["tasks"],
            icon="fa-columns",
            order=13
        ))
        
        cls.register(ModuleDefinition(
            id="weekly_goals",
            name="Weekly Goals",
            description="Weekly time goals tracking",
            category=ModuleCategory.TIME_TRACKING,
            blueprint_name="weekly_goals",
            default_enabled=True,
            icon="fa-bullseye",
            order=14
        ))
        
        cls.register(ModuleDefinition(
            id="issues",
            name="Issues",
            description="Issue and bug tracking",
            category=ModuleCategory.PROJECT_MANAGEMENT,
            blueprint_name="issues",
            default_enabled=True,
            icon="fa-bug",
            order=15
        ))
        
        cls.register(ModuleDefinition(
            id="time_entry_templates",
            name="Time Entry Templates",
            description="Reusable time entry templates",
            category=ModuleCategory.TIME_TRACKING,
            blueprint_name="time_entry_templates",
            default_enabled=True,
            icon="fa-clipboard-list",
            order=16
        ))
        
        # CRM Features
        cls.register(ModuleDefinition(
            id="quotes",
            name="Quotes",
            description="Quote management",
            category=ModuleCategory.CRM,
            blueprint_name="quotes",
            default_enabled=True,
            dependencies=["clients"],
            icon="fa-file-contract",
            order=20
        ))
        
        cls.register(ModuleDefinition(
            id="contacts",
            name="Contacts",
            description="Contact management",
            category=ModuleCategory.CRM,
            blueprint_name="contacts",
            default_enabled=True,
            dependencies=["clients"],
            icon="fa-address-book",
            order=21
        ))
        
        cls.register(ModuleDefinition(
            id="deals",
            name="Deals",
            description="Deal pipeline management",
            category=ModuleCategory.CRM,
            blueprint_name="deals",
            default_enabled=True,
            dependencies=["clients"],
            icon="fa-handshake",
            order=22
        ))
        
        cls.register(ModuleDefinition(
            id="leads",
            name="Leads",
            description="Lead management",
            category=ModuleCategory.CRM,
            blueprint_name="leads",
            default_enabled=True,
            dependencies=["clients"],
            icon="fa-user-tag",
            order=23
        ))
        
        # Finance & Expenses
        cls.register(ModuleDefinition(
            id="reports",
            name="Reports",
            description="Standard reports",
            category=ModuleCategory.FINANCE,
            blueprint_name="reports",
            default_enabled=True,
            icon="fa-chart-bar",
            order=30
        ))
        
        cls.register(ModuleDefinition(
            id="custom_reports",
            name="Report Builder",
            description="Custom report builder",
            category=ModuleCategory.FINANCE,
            blueprint_name="custom_reports",
            default_enabled=True,
            icon="fa-magic",
            order=31
        ))
        
        cls.register(ModuleDefinition(
            id="scheduled_reports",
            name="Scheduled Reports",
            description="Automated report scheduling",
            category=ModuleCategory.FINANCE,
            blueprint_name="scheduled_reports",
            default_enabled=True,
            icon="fa-clock",
            order=32
        ))
        
        cls.register(ModuleDefinition(
            id="invoices",
            name="Invoices",
            description="Invoice management",
            category=ModuleCategory.FINANCE,
            blueprint_name="invoices",
            default_enabled=True,
            dependencies=["projects"],
            icon="fa-file-invoice",
            order=33
        ))
        
        cls.register(ModuleDefinition(
            id="invoice_approvals",
            name="Invoice Approvals",
            description="Invoice approval workflow",
            category=ModuleCategory.FINANCE,
            blueprint_name="invoice_approvals",
            default_enabled=True,
            dependencies=["invoices"],
            icon="fa-check-circle",
            order=34
        ))
        
        cls.register(ModuleDefinition(
            id="recurring_invoices",
            name="Recurring Invoices",
            description="Recurring invoice management",
            category=ModuleCategory.FINANCE,
            blueprint_name="recurring_invoices",
            default_enabled=True,
            dependencies=["invoices"],
            icon="fa-sync-alt",
            order=35
        ))
        
        cls.register(ModuleDefinition(
            id="payments",
            name="Payments",
            description="Payment tracking",
            category=ModuleCategory.FINANCE,
            blueprint_name="payments",
            default_enabled=True,
            dependencies=["invoices"],
            icon="fa-credit-card",
            order=36
        ))
        
        cls.register(ModuleDefinition(
            id="payment_gateways",
            name="Payment Gateways",
            description="Payment gateway integration",
            category=ModuleCategory.FINANCE,
            blueprint_name="payment_gateways",
            default_enabled=True,
            dependencies=["payments"],
            icon="fa-credit-card",
            order=37
        ))
        
        cls.register(ModuleDefinition(
            id="expenses",
            name="Expenses",
            description="Expense tracking",
            category=ModuleCategory.FINANCE,
            blueprint_name="expenses",
            default_enabled=True,
            dependencies=["projects"],
            icon="fa-receipt",
            order=38
        ))
        
        cls.register(ModuleDefinition(
            id="mileage",
            name="Mileage",
            description="Mileage tracking",
            category=ModuleCategory.FINANCE,
            blueprint_name="mileage",
            default_enabled=True,
            icon="fa-car",
            order=39
        ))
        
        cls.register(ModuleDefinition(
            id="per_diem",
            name="Per Diem",
            description="Per diem expense tracking",
            category=ModuleCategory.FINANCE,
            blueprint_name="per_diem",
            default_enabled=True,
            icon="fa-utensils",
            order=40
        ))
        
        cls.register(ModuleDefinition(
            id="budget_alerts",
            name="Budget Alerts",
            description="Project budget monitoring",
            category=ModuleCategory.FINANCE,
            blueprint_name="budget_alerts",
            default_enabled=True,
            dependencies=["projects"],
            icon="fa-exclamation-triangle",
            order=41
        ))
        
        # Inventory
        cls.register(ModuleDefinition(
            id="inventory",
            name="Inventory",
            description="Inventory management",
            category=ModuleCategory.INVENTORY,
            blueprint_name="inventory",
            default_enabled=True,
            icon="fa-boxes",
            order=50
        ))
        
        # Analytics
        cls.register(ModuleDefinition(
            id="analytics",
            name="Analytics",
            description="Analytics dashboard",
            category=ModuleCategory.ANALYTICS,
            blueprint_name="analytics",
            default_enabled=True,
            icon="fa-chart-line",
            order=60
        ))
        
        # Tools & Data
        cls.register(ModuleDefinition(
            id="integrations",
            name="Integrations",
            description="External integrations",
            category=ModuleCategory.TOOLS,
            blueprint_name="integrations",
            default_enabled=True,
            icon="fa-plug",
            order=70
        ))
        
        cls.register(ModuleDefinition(
            id="import_export",
            name="Import/Export",
            description="Data import and export",
            category=ModuleCategory.TOOLS,
            blueprint_name="import_export",
            default_enabled=True,
            icon="fa-exchange-alt",
            order=71
        ))
        
        cls.register(ModuleDefinition(
            id="saved_filters",
            name="Saved Filters",
            description="Saved filter management",
            category=ModuleCategory.TOOLS,
            blueprint_name="saved_filters",
            default_enabled=True,
            icon="fa-filter",
            order=72
        ))
        
        # Advanced Features
        cls.register(ModuleDefinition(
            id="workflows",
            name="Workflows",
            description="Automation workflows",
            category=ModuleCategory.ADVANCED,
            blueprint_name="workflows",
            default_enabled=True,
            icon="fa-sitemap",
            order=80
        ))
        
        cls.register(ModuleDefinition(
            id="time_approvals",
            name="Time Approvals",
            description="Time entry approval workflow",
            category=ModuleCategory.ADVANCED,
            blueprint_name="time_approvals",
            default_enabled=True,
            dependencies=["timer"],
            icon="fa-check-double",
            order=81
        ))
        
        cls.register(ModuleDefinition(
            id="activity_feed",
            name="Activity Feed",
            description="Activity stream",
            category=ModuleCategory.ADVANCED,
            blueprint_name="activity_feed",
            default_enabled=True,
            icon="fa-stream",
            order=82
        ))
        
        cls.register(ModuleDefinition(
            id="recurring_tasks",
            name="Recurring Tasks",
            description="Automated recurring tasks",
            category=ModuleCategory.ADVANCED,
            blueprint_name="recurring_tasks",
            default_enabled=True,
            dependencies=["tasks"],
            icon="fa-redo",
            order=83
        ))
        
        cls.register(ModuleDefinition(
            id="team_chat",
            name="Team Chat",
            description="Team messaging",
            category=ModuleCategory.ADVANCED,
            blueprint_name="team_chat",
            default_enabled=True,
            icon="fa-comments",
            order=84
        ))
        
        cls.register(ModuleDefinition(
            id="client_portal",
            name="Client Portal",
            description="Client-facing portal",
            category=ModuleCategory.ADVANCED,
            blueprint_name="client_portal",
            default_enabled=True,
            dependencies=["clients"],
            icon="fa-door-open",
            order=85
        ))
        
        cls.register(ModuleDefinition(
            id="kiosk",
            name="Kiosk Mode",
            description="Kiosk interface",
            category=ModuleCategory.ADVANCED,
            blueprint_name="kiosk",
            default_enabled=True,
            icon="fa-desktop",
            order=86
        ))
        
        cls._initialized = True

