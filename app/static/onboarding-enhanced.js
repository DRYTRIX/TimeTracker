/**
 * Enhanced Onboarding System for TimeTracker
 * Interactive tours, tooltips, contextual help, and feature discovery
 */

class EnhancedOnboardingManager {
    constructor() {
        this.currentStep = 0;
        this.steps = [];
        this.overlay = null;
        this.tooltip = null;
        this.highlight = null;
        this.storageKey = 'onboarding_completed';
        this.tooltipsEnabled = true;
        this.featureDiscoveryEnabled = true;
        this.init();
    }

    init() {
        // Initialize tooltip system
        this.initTooltips();
        
        // Initialize contextual help buttons
        this.initContextualHelp();
        
        // Initialize feature discovery
        if (this.featureDiscoveryEnabled) {
            this.initFeatureDiscovery();
        }
        
        // Check for first-time user
        this.checkFirstTimeUser();
    }

    /**
     * Tooltip System for Complex Features
     */
    initTooltips() {
        // Create tooltip container
        this.tooltipContainer = document.createElement('div');
        this.tooltipContainer.id = 'tooltip-container';
        this.tooltipContainer.className = 'tooltip-container';
        document.body.appendChild(this.tooltipContainer);

        // Add tooltip styles
        this.addTooltipStyles();

        // Attach tooltips to elements with data-tooltip attribute
        document.addEventListener('DOMContentLoaded', () => {
            this.attachTooltips();
        });

        // Re-attach tooltips when new content is loaded
        const observer = new MutationObserver(() => {
            this.attachTooltips();
        });
        observer.observe(document.body, { childList: true, subtree: true });
    }

    addTooltipStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .tooltip-container {
                position: fixed;
                z-index: 10000;
                pointer-events: none;
            }
            
            .tooltip-element {
                position: relative;
                display: inline-block;
            }
            
            .tooltip-trigger {
                cursor: help;
                color: #3b82f6;
                margin-left: 4px;
                font-size: 0.875rem;
            }
            
            .dark .tooltip-trigger {
                color: #60a5fa;
            }
            
            .tooltip-popup {
                position: absolute;
                background: #1e293b;
                color: #e2e8f0;
                padding: 12px 16px;
                border-radius: 8px;
                font-size: 0.875rem;
                line-height: 1.5;
                max-width: 300px;
                box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
                z-index: 10001;
                pointer-events: none;
                opacity: 0;
                transform: translateY(-8px);
                transition: opacity 0.2s, transform 0.2s;
                bottom: calc(100% + 8px);
                left: 50%;
                transform: translateX(-50%) translateY(-8px);
            }
            
            .tooltip-popup.show {
                opacity: 1;
                transform: translateX(-50%) translateY(0);
            }
            
            .tooltip-popup::after {
                content: '';
                position: absolute;
                top: 100%;
                left: 50%;
                transform: translateX(-50%);
                border: 6px solid transparent;
                border-top-color: #1e293b;
            }
            
            .dark .tooltip-popup {
                background: #0f172a;
                color: #f1f5f9;
            }
            
            .dark .tooltip-popup::after {
                border-top-color: #0f172a;
            }
            
            .contextual-help-btn {
                position: absolute;
                top: 8px;
                right: 8px;
                width: 24px;
                height: 24px;
                border-radius: 50%;
                background: #3b82f6;
                color: white;
                border: none;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 12px;
                box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
                transition: all 0.2s;
                z-index: 10;
            }
            
            .contextual-help-btn:hover {
                background: #2563eb;
                transform: scale(1.1);
            }
            
            .feature-discovery-badge {
                position: absolute;
                top: -8px;
                right: -8px;
                width: 20px;
                height: 20px;
                border-radius: 50%;
                background: #ef4444;
                color: white;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 10px;
                font-weight: bold;
                animation: pulse 2s infinite;
                z-index: 100;
            }
            
            @keyframes pulse {
                0%, 100% { transform: scale(1); }
                50% { transform: scale(1.1); }
            }
        `;
        document.head.appendChild(style);
    }

    attachTooltips() {
        // Find all elements with data-tooltip attribute
        const elements = document.querySelectorAll('[data-tooltip]');
        elements.forEach(element => {
            if (element.dataset.tooltipAttached === 'true') return;
            
            const tooltipText = element.dataset.tooltip;
            const tooltipElement = document.createElement('span');
            tooltipElement.className = 'tooltip-element';
            
            // Create trigger icon
            const trigger = document.createElement('span');
            trigger.className = 'tooltip-trigger';
            trigger.innerHTML = '<i class="fas fa-question-circle"></i>';
            trigger.setAttribute('aria-label', 'Help');
            
            // Create popup
            const popup = document.createElement('div');
            popup.className = 'tooltip-popup';
            popup.textContent = tooltipText;
            
            // Wrap element
            element.parentNode.insertBefore(tooltipElement, element);
            tooltipElement.appendChild(element);
            tooltipElement.appendChild(trigger);
            tooltipElement.appendChild(popup);
            
            // Event listeners
            trigger.addEventListener('mouseenter', () => {
                popup.classList.add('show');
            });
            
            trigger.addEventListener('mouseleave', () => {
                popup.classList.remove('show');
            });
            
            element.dataset.tooltipAttached = 'true';
        });
    }

    /**
     * Contextual Help Buttons
     */
    initContextualHelp() {
        // Add help buttons to complex features
        const helpTargets = [
            { selector: '.kanban-board', helpId: 'kanban-help' },
            { selector: '.time-entry-form', helpId: 'time-entry-help' },
            { selector: '.reports-dashboard', helpId: 'reports-help' },
            { selector: '.analytics-dashboard', helpId: 'analytics-help' },
            { selector: '.invoice-form', helpId: 'invoice-help' }
        ];

        document.addEventListener('DOMContentLoaded', () => {
            helpTargets.forEach(target => {
                const element = document.querySelector(target.selector);
                if (element) {
                    this.addHelpButton(element, target.helpId);
                }
            });
        });

        // Re-check when content changes
        const observer = new MutationObserver(() => {
            helpTargets.forEach(target => {
                const element = document.querySelector(target.selector);
                if (element && !element.querySelector('.contextual-help-btn')) {
                    this.addHelpButton(element, target.helpId);
                }
            });
        });
        observer.observe(document.body, { childList: true, subtree: true });
    }

    addHelpButton(element, helpId) {
        // Check if button already exists
        if (element.querySelector('.contextual-help-btn')) return;

        // Make parent relative if not already
        const computedStyle = window.getComputedStyle(element);
        if (computedStyle.position === 'static') {
            element.style.position = 'relative';
        }

        const helpBtn = document.createElement('button');
        helpBtn.className = 'contextual-help-btn';
        helpBtn.innerHTML = '<i class="fas fa-question"></i>';
        helpBtn.setAttribute('aria-label', 'Get help');
        helpBtn.onclick = (e) => {
            e.stopPropagation();
            this.showContextualHelp(helpId);
        };

        element.appendChild(helpBtn);
    }

    showContextualHelp(helpId) {
        const helpContent = this.getHelpContent(helpId);
        if (!helpContent) return;

        // Show help in a modal
        this.showHelpModal(helpContent.title, helpContent.content);
    }

    getHelpContent(helpId) {
        const helpContent = {
            'kanban-help': {
                title: 'Kanban Board Help',
                content: `
                    <p><strong>Drag and Drop:</strong> Move tasks between columns by dragging them.</p>
                    <p><strong>Task Details:</strong> Click on a task card to view and edit details.</p>
                    <p><strong>Quick Actions:</strong> Use the icons on task cards for quick actions like starting a timer.</p>
                    <p><strong>Filtering:</strong> Use the filter options to find specific tasks.</p>
                `
            },
            'time-entry-help': {
                title: 'Time Entry Help',
                content: `
                    <p><strong>Start Timer:</strong> Select a project and click Start to begin tracking time.</p>
                    <p><strong>Manual Entry:</strong> Fill in the form to log time manually.</p>
                    <p><strong>Bulk Entry:</strong> Use bulk entry to create multiple entries at once.</p>
                    <p><strong>Notes:</strong> Add notes to track what you worked on.</p>
                `
            },
            'reports-help': {
                title: 'Reports Help',
                content: `
                    <p><strong>Date Range:</strong> Select a date range to filter your reports.</p>
                    <p><strong>Export:</strong> Export reports to PDF or CSV for sharing.</p>
                    <p><strong>Filters:</strong> Use filters to narrow down your data.</p>
                    <p><strong>Charts:</strong> Visualize your time data with interactive charts.</p>
                `
            },
            'analytics-help': {
                title: 'Analytics Help',
                content: `
                    <p><strong>Overview:</strong> Get insights into your time tracking patterns.</p>
                    <p><strong>Trends:</strong> View trends over time to identify patterns.</p>
                    <p><strong>Project Analytics:</strong> See how time is distributed across projects.</p>
                    <p><strong>Productivity:</strong> Track your productivity metrics.</p>
                `
            },
            'invoice-help': {
                title: 'Invoice Help',
                content: `
                    <p><strong>Create Invoice:</strong> Generate invoices from time entries or create manually.</p>
                    <p><strong>Template:</strong> Customize invoice templates in settings.</p>
                    <p><strong>PDF Export:</strong> Export invoices as PDF for sending to clients.</p>
                    <p><strong>Payment Tracking:</strong> Track payments and invoice status.</p>
                `
            }
        };

        return helpContent[helpId];
    }

    showHelpModal(title, content) {
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 z-[2000] flex items-center justify-center';
        modal.innerHTML = `
            <div class="absolute inset-0 bg-black/50" onclick="this.closest('.fixed').remove()"></div>
            <div class="relative bg-card-light dark:bg-card-dark text-text-light dark:text-text-dark rounded-lg shadow-xl w-full max-w-2xl mx-4 p-6">
                <div class="flex items-center justify-between mb-4">
                    <h3 class="text-xl font-semibold">${title}</h3>
                    <button onclick="this.closest('.fixed').remove()" class="text-text-muted-light dark:text-text-muted-dark hover:text-text-light dark:hover:text-text-dark">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="prose dark:prose-invert max-w-none">
                    ${content}
                </div>
                <div class="mt-6 flex justify-end">
                    <button onclick="this.closest('.fixed').remove()" class="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90">
                        Close
                    </button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }

    /**
     * Feature Discovery for Power Features
     */
    initFeatureDiscovery() {
        // Features to discover
        const powerFeatures = [
            {
                selector: '[data-feature="keyboard-shortcuts"]',
                name: 'Keyboard Shortcuts',
                description: 'Press Ctrl+K to open the command palette with keyboard shortcuts',
                badge: true
            },
            {
                selector: '[data-feature="bulk-actions"]',
                name: 'Bulk Actions',
                description: 'Select multiple items to perform bulk operations',
                badge: true
            },
            {
                selector: '[data-feature="saved-filters"]',
                name: 'Saved Filters',
                description: 'Save frequently used filters for quick access',
                badge: true
            },
            {
                selector: '[data-feature="time-templates"]',
                name: 'Time Entry Templates',
                description: 'Create templates for recurring time entries',
                badge: true
            },
            {
                selector: '[data-feature="kanban"]',
                name: 'Kanban Board',
                description: 'Visual task management with drag-and-drop',
                badge: true
            }
        ];

        // Check if user has discovered features
        const discoveredFeatures = JSON.parse(
            localStorage.getItem('discovered_features') || '[]'
        );

        document.addEventListener('DOMContentLoaded', () => {
            powerFeatures.forEach(feature => {
                const element = document.querySelector(feature.selector);
                if (element && !discoveredFeatures.includes(feature.name)) {
                    this.addFeatureBadge(element, feature);
                }
            });
        });

        // Mark features as discovered on interaction
        powerFeatures.forEach(feature => {
            document.addEventListener('click', (e) => {
                const target = e.target.closest(feature.selector);
                if (target && !discoveredFeatures.includes(feature.name)) {
                    this.markFeatureDiscovered(feature.name);
                    this.removeFeatureBadge(target);
                }
            });
        });
    }

    addFeatureBadge(element, feature) {
        if (element.querySelector('.feature-discovery-badge')) return;

        const badge = document.createElement('div');
        badge.className = 'feature-discovery-badge';
        badge.innerHTML = '!';
        badge.title = feature.description;
        
        // Make parent relative if needed
        const computedStyle = window.getComputedStyle(element);
        if (computedStyle.position === 'static') {
            element.style.position = 'relative';
        }

        element.appendChild(badge);

        // Show tooltip on hover
        badge.addEventListener('mouseenter', () => {
            this.showFeatureTooltip(badge, feature);
        });
    }

    showFeatureTooltip(badge, feature) {
        const tooltip = document.createElement('div');
        tooltip.className = 'feature-discovery-tooltip';
        tooltip.style.cssText = `
            position: absolute;
            top: calc(100% + 8px);
            right: 0;
            background: #1e293b;
            color: #e2e8f0;
            padding: 12px 16px;
            border-radius: 8px;
            max-width: 250px;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
            z-index: 10001;
            font-size: 0.875rem;
        `;
        tooltip.innerHTML = `
            <div class="font-semibold mb-1">${feature.name}</div>
            <div>${feature.description}</div>
        `;
        
        badge.appendChild(tooltip);

        badge.addEventListener('mouseleave', () => {
            tooltip.remove();
        });
    }

    removeFeatureBadge(element) {
        const badge = element.querySelector('.feature-discovery-badge');
        if (badge) {
            badge.remove();
        }
    }

    markFeatureDiscovered(featureName) {
        const discovered = JSON.parse(
            localStorage.getItem('discovered_features') || '[]'
        );
        if (!discovered.includes(featureName)) {
            discovered.push(featureName);
            localStorage.setItem('discovered_features', JSON.stringify(discovered));
        }
    }

    /**
     * Interactive Tour (Enhanced)
     */
    checkFirstTimeUser() {
        if (this.isCompleted()) return;

        // Check if we're on a page where tour should start
        const path = window.location.pathname;
        if (path === '/' || path === '/main/dashboard' || path === '/dashboard') {
            setTimeout(() => {
                if (!this.isCompleted()) {
                    this.startTour();
                }
            }, 1500);
        }
    }

    startTour() {
        // Use the existing onboarding manager if available
        if (window.onboardingManager) {
            const enhancedSteps = this.getEnhancedTourSteps();
            window.onboardingManager.init(enhancedSteps);
        }
    }

    getEnhancedTourSteps() {
        return [
            {
                target: '#sidebar',
                title: 'Welcome to TimeTracker! 👋',
                content: 'Let\'s take a quick tour to help you get started. This is your main navigation where you can access all features. <strong>Tip:</strong> Click the arrow icon to collapse the sidebar and maximize your workspace.',
                position: 'right'
            },
            {
                target: 'a[href*="dashboard"]',
                title: 'Dashboard',
                content: 'Your command center! View today\'s hours, active timers, recent entries, top projects, and activity timeline. <strong>Pro tip:</strong> Customize widgets to see what matters most to you. All your time tracking data is visible at a glance.',
                position: 'right'
            },
            {
                target: 'a[href*="timer"]',
                title: 'Time Tracking',
                content: 'Start timers or manually log your time. <strong>Key features:</strong><br>• Timers run server-side (even if browser closes!)<br>• Press <kbd>T</kbd> to quickly toggle timer<br>• Use bulk entry for multiple days<br>• Save time entry templates for recurring work<br>• Idle detection auto-pauses after inactivity<br>• Manual entry with notes and tags',
                position: 'right'
            },
            {
                target: 'a[href*="projects"]',
                title: 'Projects',
                content: 'Organize your work with projects. <strong>What you can do:</strong><br>• Link projects to clients for billing<br>• Set hourly rates per project<br>• Track billable vs non-billable hours<br>• Monitor project budgets and costs<br>• Add project descriptions with Markdown<br>• Archive completed projects',
                position: 'right'
            },
            {
                target: 'a[href*="clients"]',
                title: 'Clients',
                content: 'Manage your clients and their information. Store contact details, billing rates, and company information. Clients are automatically linked to projects for streamlined invoicing and reporting.',
                position: 'right'
            },
            {
                target: 'a[href*="tasks"]',
                title: 'Tasks',
                content: 'Break down projects into manageable tasks. <strong>Features:</strong><br>• Track time against specific tasks<br>• Set priorities and due dates<br>• Assign tasks to team members<br>• Monitor progress with status tracking<br>• Use estimates vs actuals for planning<br>• Add comments for collaboration',
                position: 'right'
            },
            {
                target: 'a[href*="kanban"]',
                title: 'Kanban Board',
                content: 'Visual task management with drag-and-drop! Move tasks between columns (To Do, In Progress, Review, Done) to track progress. Perfect for agile workflows. <strong>Power feature:</strong> Customize columns to match your workflow.',
                position: 'right'
            },
            {
                target: 'a[href*="calendar"]',
                title: 'Calendar View',
                content: 'Visualize your time entries on a calendar. See your schedule at a glance, spot gaps, and plan your time more effectively. Drag and drop entries to reschedule them quickly.',
                position: 'right'
            },
            {
                target: 'a[href*="reports"]',
                title: 'Reports & Analytics',
                content: 'Gain insights into your time usage. <strong>Available reports:</strong><br>• Time breakdown by project, user, or date<br>• Billable vs non-billable analysis<br>• Export to PDF or CSV<br>• Custom date ranges<br>• Save filters for quick access<br>• Visual charts and graphs',
                position: 'right'
            },
            {
                target: 'a[href*="invoices"]',
                title: 'Invoicing',
                content: 'Generate professional invoices from your tracked time. <strong>Features:</strong><br>• Auto-generate from time entries<br>• Add custom line items and expenses<br>• Tax calculations<br>• PDF export with branding<br>• Track payment status<br>• Send invoices to clients',
                position: 'right'
            },
            {
                target: 'a[href*="analytics"]',
                title: 'Analytics Dashboard',
                content: 'Deep insights into your productivity and time patterns. View trends, project analytics, and performance metrics. Identify your most productive times and optimize your workflow.',
                position: 'right'
            },
            {
                target: 'a[href*="time_entry_templates"]',
                title: 'Time Entry Templates',
                content: 'Save time with templates! Create reusable time entry templates for common tasks. Perfect for recurring work, meetings, or standard activities. Just select a template and fill in the details.',
                position: 'right'
            },
            {
                target: 'a[href*="saved_filters"]',
                title: 'Saved Filters',
                content: 'Speed up your workflow! Save frequently used filters for reports, tasks, and time entries. Access your saved filters instantly instead of recreating them each time.',
                position: 'right'
            },
            {
                target: '#search',
                title: 'Global Search',
                content: 'Quickly find anything! Search across projects, tasks, clients, and time entries. <strong>Keyboard shortcut:</strong> Press <kbd>Ctrl+/</kbd> (or <kbd>Cmd+/</kbd> on Mac) to focus the search bar instantly.',
                position: 'bottom'
            },
            {
                target: 'button[onclick*="openCommandPalette"]',
                title: 'Command Palette',
                content: 'Power user feature! Press <kbd>Ctrl+K</kbd> (or <kbd>Cmd+K</kbd> on Mac) to open the command palette. Navigate to any feature, execute actions, and access shortcuts without using your mouse. <strong>Try it:</strong> Press <kbd>Ctrl+K</kbd> now!',
                position: 'bottom'
            },
            {
                target: '#theme-toggle',
                title: 'Theme Toggle',
                content: 'Switch between light and dark mode. Your preference is saved automatically. <strong>Keyboard shortcut:</strong> Press <kbd>Ctrl+Shift+L</kbd> to toggle themes quickly.',
                position: 'bottom'
            }
        ];
    }

    isCompleted() {
        return localStorage.getItem(this.storageKey) === 'true';
    }

    reset() {
        localStorage.removeItem(this.storageKey);
        localStorage.removeItem('discovered_features');
    }
}

// Initialize enhanced onboarding
window.enhancedOnboarding = new EnhancedOnboardingManager();

// Export for global access
window.restartOnboarding = function() {
    window.enhancedOnboarding.reset();
    if (window.onboardingManager) {
        window.onboardingManager.reset();
        window.onboardingManager.init(window.enhancedOnboarding.getEnhancedTourSteps());
    }
};

