/**
 * Activity Feed Component
 * Real-time activity feed with filtering and auto-refresh
 */

class ActivityFeed {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error(`Activity feed container not found: ${containerId}`);
            return;
        }

        this.options = {
            limit: options.limit || 50,
            autoRefresh: options.autoRefresh !== false,
            refreshInterval: options.refreshInterval || 30000, // 30 seconds
            filters: options.filters || {},
            ...options
        };

        this.activities = [];
        this.page = 1;
        this.hasMore = true;
        this.loading = false;
        this.refreshTimer = null;

        this.init();
    }

    init() {
        this.render();
        this.loadActivities();
        this.setupAutoRefresh();
        this.setupWebSocket();
    }

    async loadActivities(page = 1, append = false) {
        if (this.loading) return;
        this.loading = true;
        this.showLoading();

        try {
            const params = new URLSearchParams({
                page: page.toString(),
                limit: this.options.limit.toString(),
                ...this.options.filters
            });

            const response = await fetch(`/api/activity?${params}`);
            const data = await response.json();

            if (append) {
                this.activities = [...this.activities, ...data.activities];
            } else {
                this.activities = data.activities;
            }

            this.hasMore = data.pagination.has_next;
            this.page = data.pagination.page;

            this.render();
        } catch (error) {
            console.error('Error loading activities:', error);
            this.showError('Failed to load activities');
        } finally {
            this.loading = false;
            this.hideLoading();
        }
    }

    render() {
        if (!this.container) return;

        if (this.activities.length === 0 && !this.loading) {
            this.container.innerHTML = `
                <div class="text-center py-8 text-gray-500">
                    <i class="fas fa-inbox text-4xl mb-4"></i>
                    <p>No activities found</p>
                </div>
            `;
            return;
        }

        const activitiesHtml = this.activities.map(activity => this.renderActivity(activity)).join('');

        this.container.innerHTML = `
            <div class="activity-feed">
                ${activitiesHtml}
            </div>
            ${this.hasMore ? '<div class="text-center mt-4"><button class="load-more-btn bg-primary text-white px-4 py-2 rounded">Load More</button></div>' : ''}
        `;

        // Setup load more button
        const loadMoreBtn = this.container.querySelector('.load-more-btn');
        if (loadMoreBtn) {
            loadMoreBtn.addEventListener('click', () => {
                this.loadActivities(this.page + 1, true);
            });
        }
    }

    renderActivity(activity) {
        const icon = this.getActivityIcon(activity);
        const timeAgo = this.formatTimeAgo(activity.created_at);
        const userDisplay = activity.display_name || activity.username || 'Unknown';

        return `
            <div class="activity-item flex items-start gap-4 p-4 border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                <div class="activity-icon flex-shrink-0 w-10 h-10 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center">
                    <i class="${icon}"></i>
                </div>
                <div class="activity-content flex-1">
                    <div class="activity-header flex items-center gap-2 mb-1">
                        <span class="font-semibold">${userDisplay}</span>
                        <span class="text-sm text-gray-500 dark:text-gray-400">${activity.description || this.formatActivityDescription(activity)}</span>
                        <span class="text-xs text-gray-400 ml-auto">${timeAgo}</span>
                    </div>
                    ${activity.extra_data ? `<div class="activity-meta text-xs text-gray-500 mt-1">${this.formatExtraData(activity.extra_data)}</div>` : ''}
                </div>
            </div>
        `;
    }

    getActivityIcon(activity) {
        const icons = {
            'created': 'fas fa-plus-circle text-green-500',
            'updated': 'fas fa-edit text-blue-500',
            'deleted': 'fas fa-trash text-red-500',
            'started': 'fas fa-play text-green-500',
            'stopped': 'fas fa-stop text-red-500',
            'completed': 'fas fa-check-circle text-green-500',
            'assigned': 'fas fa-user-plus text-blue-500',
            'commented': 'fas fa-comment text-gray-500',
            'sent': 'fas fa-paper-plane text-blue-500',
            'paid': 'fas fa-dollar-sign text-green-500',
        };
        return icons[activity.action] || 'fas fa-circle text-gray-500';
    }

    formatActivityDescription(activity) {
        const entityType = activity.entity_type.replace('_', ' ');
        return `${activity.action} ${entityType} ${activity.entity_name || ''}`;
    }

    formatTimeAgo(timestamp) {
        if (!timestamp) return '';
        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return 'just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        return window.formatUserDate ? window.formatUserDate(date) : date.toLocaleDateString();
    }

    formatExtraData(extraData) {
        if (typeof extraData !== 'object') return '';
        return Object.entries(extraData).map(([key, value]) => `${key}: ${value}`).join(', ');
    }

    setupAutoRefresh() {
        if (!this.options.autoRefresh) return;

        this.refreshTimer = setInterval(() => {
            this.loadActivities(1, false);
        }, this.options.refreshInterval);
    }

    setupWebSocket() {
        // Listen for real-time activity updates via WebSocket
        if (typeof io !== 'undefined') {
            io.on('activity_created', (data) => {
                if (data.activity) {
                    this.activities.unshift(data.activity);
                    if (this.activities.length > this.options.limit) {
                        this.activities.pop();
                    }
                    this.render();
                }
            });
        }
    }

    showLoading() {
        const loadingEl = document.createElement('div');
        loadingEl.className = 'activity-loading text-center py-4';
        loadingEl.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
        this.container.appendChild(loadingEl);
    }

    hideLoading() {
        const loadingEl = this.container.querySelector('.activity-loading');
        if (loadingEl) {
            loadingEl.remove();
        }
    }

    showError(message) {
        const errorEl = document.createElement('div');
        errorEl.className = 'activity-error bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded';
        errorEl.textContent = message;
        this.container.appendChild(errorEl);
    }

    setFilters(filters) {
        this.options.filters = { ...this.options.filters, ...filters };
        this.page = 1;
        this.loadActivities(1, false);
    }

    destroy() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
        }
        if (typeof io !== 'undefined') {
            io.off('activity_created');
        }
    }
}

// Auto-initialize if container exists
document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('activity-feed-container');
    if (container) {
        window.activityFeed = new ActivityFeed('activity-feed-container', {
            autoRefresh: true,
            refreshInterval: 30000
        });
    }
});

