/**
 * Dashboard Widgets System
 * Customizable, draggable dashboard widgets
 */

class DashboardWidgetManager {
    constructor() {
        this.widgets = [];
        this.layout = this.loadLayout();
        this.availableWidgets = this.defineAvailableWidgets();
        this.editMode = false;
        this.init();
    }

    init() {
        this.createContainer();
        this.renderWidgets();
        this.createCustomizeButton();
    }

    defineAvailableWidgets() {
        return {
            'quick-stats': {
                id: 'quick-stats',
                name: 'Quick Stats',
                description: 'Overview of today\'s time tracking',
                size: 'medium',
                render: () => this.renderQuickStats()
            },
            'active-timer': {
                id: 'active-timer',
                name: 'Active Timer',
                description: 'Currently running timer',
                size: 'small',
                render: () => this.renderActiveTimer()
            },
            'recent-projects': {
                id: 'recent-projects',
                name: 'Recent Projects',
                description: 'Recently worked on projects',
                size: 'medium',
                render: () => this.renderRecentProjects()
            },
            'upcoming-deadlines': {
                id: 'upcoming-deadlines',
                name: 'Upcoming Deadlines',
                description: 'Tasks due soon',
                size: 'medium',
                render: () => this.renderUpcomingDeadlines()
            },
            'time-chart': {
                id: 'time-chart',
                name: 'Time Tracking Chart',
                description: '7-day time tracking visualization',
                size: 'large',
                render: () => this.renderTimeChart()
            },
            'productivity-score': {
                id: 'productivity-score',
                name: 'Productivity Score',
                description: 'Your productivity metrics',
                size: 'small',
                render: () => this.renderProductivityScore()
            },
            'activity-feed': {
                id: 'activity-feed',
                name: 'Activity Feed',
                description: 'Recent activity across projects',
                size: 'medium',
                render: () => this.renderActivityFeed()
            },
            'quick-actions': {
                id: 'quick-actions',
                name: 'Quick Actions',
                description: 'Common actions at your fingertips',
                size: 'small',
                render: () => this.renderQuickActions()
            }
        };
    }

    createContainer() {
        const dashboard = document.querySelector('[data-dashboard]');
        if (dashboard) {
            dashboard.classList.add('dashboard-widgets-container');
            dashboard.innerHTML = '<div class="widgets-grid"></div>';
        }
    }

    createCustomizeButton() {
        const button = document.createElement('button');
        button.className = 'fixed bottom-24 left-6 z-40 px-4 py-2 bg-card-light dark:bg-card-dark border-2 border-primary text-primary rounded-lg shadow-lg hover:shadow-xl hover:bg-primary hover:text-white transition-all';
        button.innerHTML = '<i class="fas fa-cog mr-2"></i>Customize Dashboard';
        button.onclick = () => this.toggleEditMode();
        document.body.appendChild(button);
    }

    renderWidgets() {
        const container = document.querySelector('.widgets-grid');
        if (!container) return;

        container.innerHTML = '';
        container.className = 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 p-6';

        // Get active widgets from layout or use defaults
        const activeWidgets = this.layout.length > 0 ? this.layout : [
            'quick-stats',
            'active-timer',
            'time-chart',
            'upcoming-deadlines',
            'recent-projects',
            'activity-feed'
        ];

        activeWidgets.forEach(widgetId => {
            const widget = this.availableWidgets[widgetId];
            if (widget) {
                const el = this.createWidgetElement(widget);
                container.appendChild(el);
            }
        });
    }

    createWidgetElement(widget) {
        const el = document.createElement('div');
        el.className = `widget-card ${this.getSizeClass(widget.size)} bg-card-light dark:bg-card-dark rounded-lg shadow-sm hover:shadow-md transition-shadow p-6 relative`;
        el.dataset.widgetId = widget.id;
        
        if (this.editMode) {
            el.classList.add('edit-mode');
            el.draggable = true;
        }

        el.innerHTML = `
            ${this.editMode ? '<div class="widget-drag-handle absolute top-2 right-2 cursor-move"><i class="fas fa-grip-vertical text-gray-400"></i></div>' : ''}
            <div class="widget-content">
                ${widget.render()}
            </div>
        `;

        if (this.editMode) {
            this.makeDraggable(el);
        }

        return el;
    }

    getSizeClass(size) {
        return {
            'small': 'col-span-1',
            'medium': 'md:col-span-1',
            'large': 'md:col-span-2 lg:col-span-2'
        }[size] || 'col-span-1';
    }

    // Widget render methods
    renderQuickStats() {
        return `
            <h3 class="text-lg font-semibold mb-4">Quick Stats</h3>
            <div class="grid grid-cols-2 gap-4">
                <div class="text-center p-3 bg-blue-50 dark:bg-blue-900/20 rounded">
                    <div class="text-2xl font-bold text-blue-600">0.0h</div>
                    <div class="text-xs text-gray-600 dark:text-gray-400">Today</div>
                </div>
                <div class="text-center p-3 bg-green-50 dark:bg-green-900/20 rounded">
                    <div class="text-2xl font-bold text-green-600">0.0h</div>
                    <div class="text-xs text-gray-600 dark:text-gray-400">This Week</div>
                </div>
            </div>
        `;
    }

    renderActiveTimer() {
        return `
            <h3 class="text-lg font-semibold mb-4">Active Timer</h3>
            <div class="text-center py-8">
                <div class="text-3xl font-bold text-primary mb-2">00:00:00</div>
                <p class="text-sm text-gray-600 dark:text-gray-400 mb-4">No active timer</p>
                <button class="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90">
                    <i class="fas fa-play mr-2"></i>Start Timer
                </button>
            </div>
        `;
    }

    renderRecentProjects() {
        return `
            <h3 class="text-lg font-semibold mb-4">Recent Projects</h3>
            <div class="space-y-2">
                <div class="p-3 hover:bg-gray-50 dark:hover:bg-gray-800 rounded cursor-pointer">
                    <div class="font-medium">Project A</div>
                    <div class="text-xs text-gray-600 dark:text-gray-400">Last updated 2h ago</div>
                </div>
                <div class="p-3 hover:bg-gray-50 dark:hover:bg-gray-800 rounded cursor-pointer">
                    <div class="font-medium">Project B</div>
                    <div class="text-xs text-gray-600 dark:text-gray-400">Last updated yesterday</div>
                </div>
            </div>
        `;
    }

    renderUpcomingDeadlines() {
        return `
            <h3 class="text-lg font-semibold mb-4">Upcoming Deadlines</h3>
            <div class="space-y-3">
                <div class="flex items-center gap-3 p-3 bg-amber-50 dark:bg-amber-900/20 rounded">
                    <i class="fas fa-exclamation-triangle text-amber-600"></i>
                    <div class="flex-1">
                        <div class="font-medium">Task A</div>
                        <div class="text-xs text-gray-600 dark:text-gray-400">Due in 2 days</div>
                    </div>
                </div>
            </div>
        `;
    }

    renderTimeChart() {
        return `
            <h3 class="text-lg font-semibold mb-4">Time Tracking (7 Days)</h3>
            <canvas id="widget-time-chart" height="200"></canvas>
        `;
    }

    renderProductivityScore() {
        return `
            <h3 class="text-lg font-semibold mb-4">Productivity</h3>
            <div class="text-center">
                <div class="text-5xl font-bold text-green-600 mb-2">85</div>
                <div class="text-sm text-gray-600 dark:text-gray-400">Score</div>
                <div class="mt-4 text-xs text-green-600">
                    <i class="fas fa-arrow-up"></i> +5% from last week
                </div>
            </div>
        `;
    }

    renderActivityFeed() {
        return `
            <h3 class="text-lg font-semibold mb-4">Recent Activity</h3>
            <div class="space-y-3">
                <div class="flex items-start gap-3">
                    <div class="w-2 h-2 bg-blue-500 rounded-full mt-2"></div>
                    <div class="flex-1">
                        <p class="text-sm">Time logged on Project A</p>
                        <span class="text-xs text-gray-500">2 hours ago</span>
                    </div>
                </div>
            </div>
        `;
    }

    renderQuickActions() {
        return `
            <h3 class="text-lg font-semibold mb-4">Quick Actions</h3>
            <div class="grid grid-cols-2 gap-2">
                <button class="p-3 bg-blue-50 dark:bg-blue-900/20 rounded hover:bg-blue-100 dark:hover:bg-blue-900/30">
                    <i class="fas fa-play text-blue-600 mb-2"></i>
                    <div class="text-xs">Start Timer</div>
                </button>
                <button class="p-3 bg-green-50 dark:bg-green-900/20 rounded hover:bg-green-100 dark:hover:bg-green-900/30">
                    <i class="fas fa-plus text-green-600 mb-2"></i>
                    <div class="text-xs">New Task</div>
                </button>
            </div>
        `;
    }

    toggleEditMode() {
        this.editMode = !this.editMode;
        
        if (this.editMode) {
            this.showWidgetSelector();
        }
        
        this.renderWidgets();
    }

    showWidgetSelector() {
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 z-50 flex items-center justify-center';
        modal.innerHTML = `
            <div class="absolute inset-0 bg-black/50" onclick="this.parentElement.remove()"></div>
            <div class="relative bg-card-light dark:bg-card-dark rounded-lg shadow-xl max-w-2xl w-full mx-4 p-6">
                <h2 class="text-2xl font-bold mb-4">Customize Dashboard</h2>
                <div class="grid grid-cols-2 gap-4 mb-6">
                    ${Object.values(this.availableWidgets).map(w => `
                        <div class="p-4 border-2 border-border-light dark:border-border-dark rounded-lg hover:border-primary cursor-pointer">
                            <h4 class="font-semibold">${w.name}</h4>
                            <p class="text-sm text-gray-600 dark:text-gray-400">${w.description}</p>
                        </div>
                    `).join('')}
                </div>
                <div class="flex justify-end gap-2">
                    <button onclick="this.closest('.fixed').remove()" class="px-4 py-2 bg-gray-200 dark:bg-gray-700 rounded-lg">Cancel</button>
                    <button onclick="widgetManager.saveLayout(); this.closest('.fixed').remove()" class="px-4 py-2 bg-primary text-white rounded-lg">Save Layout</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }

    makeDraggable(element) {
        element.addEventListener('dragstart', (e) => {
            e.dataTransfer.effectAllowed = 'move';
            e.dataTransfer.setData('text/html', element.innerHTML);
            element.classList.add('dragging');
        });

        element.addEventListener('dragend', () => {
            element.classList.remove('dragging');
        });

        element.addEventListener('dragover', (e) => {
            e.preventDefault();
            const container = element.parentElement;
            const afterElement = this.getDragAfterElement(container, e.clientY);
            const dragging = container.querySelector('.dragging');
            if (afterElement == null) {
                container.appendChild(dragging);
            } else {
                container.insertBefore(dragging, afterElement);
            }
        });
    }

    getDragAfterElement(container, y) {
        const draggableElements = [...container.querySelectorAll('.widget-card:not(.dragging)')];
        
        return draggableElements.reduce((closest, child) => {
            const box = child.getBoundingClientRect();
            const offset = y - box.top - box.height / 2;
            if (offset < 0 && offset > closest.offset) {
                return { offset: offset, element: child };
            } else {
                return closest;
            }
        }, { offset: Number.NEGATIVE_INFINITY }).element;
    }

    saveLayout() {
        const widgets = Array.from(document.querySelectorAll('.widget-card')).map(el => el.dataset.widgetId);
        this.layout = widgets;
        localStorage.setItem('dashboard_layout', JSON.stringify(widgets));
        this.editMode = false;
        this.renderWidgets();
        
        if (window.toastManager) {
            window.toastManager.success('Dashboard layout saved!');
        }
    }

    loadLayout() {
        try {
            const saved = localStorage.getItem('dashboard_layout');
            return saved ? JSON.parse(saved) : [];
        } catch {
            return [];
        }
    }
}

// Initialize
window.addEventListener('DOMContentLoaded', () => {
    if (document.querySelector('[data-dashboard]')) {
        window.widgetManager = new DashboardWidgetManager();
        console.log('Dashboard widgets initialized');
    }
});

