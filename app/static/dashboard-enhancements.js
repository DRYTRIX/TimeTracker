/**
 * Dashboard Enhancements - Sparklines, Activity Timeline, Real-time Updates
 */

(function() {
    'use strict';

    let sparklineCharts = new Map();
    let realTimeUpdateInterval = null;
    let activityTimeline = null;
    let lastDashboardUpdateAt = 0;
    const MIN_UPDATE_INTERVAL_MS = 5000; // Throttle: no updates more than once per 5s

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    function isDashboardPage() {
        return window.location.pathname === '/dashboard' ||
            document.getElementById('todayHoursValue') != null ||
            document.querySelector('[data-sparkline]') != null;
    }

    function init() {
        initSparklines();
        initActivityTimeline();
        initRealTimeUpdates();
    }

    /**
     * Initialize sparklines for quick stats
     */
    function initSparklines() {
        const sparklineContainers = document.querySelectorAll('[data-sparkline]');
        
        sparklineContainers.forEach(container => {
            const data = JSON.parse(container.getAttribute('data-sparkline'));
            const color = container.getAttribute('data-color') || '#3b82f6';
            const id = container.id || 'sparkline-' + Math.random().toString(36).substr(2, 9);
            
            if (!container.id) {
                container.id = id;
            }

            createSparkline(id, data, color);
        });
    }

    /**
     * Create a sparkline chart
     */
    function createSparkline(containerId, data, color = '#3b82f6') {
        const container = document.getElementById(containerId);
        if (!container) return;

        const width = container.offsetWidth || 100;
        const height = container.offsetHeight || 40;
        const padding = 4;

        // Create SVG
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('class', 'sparkline-svg');
        svg.setAttribute('width', width);
        svg.setAttribute('height', height);
        svg.setAttribute('viewBox', `0 0 ${width} ${height}`);

        // Calculate scales
        const maxValue = Math.max(...data);
        const minValue = Math.min(...data);
        const range = maxValue - minValue || 1;
        const xScale = (width - 2 * padding) / (data.length - 1 || 1);
        const yScale = (height - 2 * padding) / range;

        // Create path
        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        let pathData = '';

        data.forEach((value, index) => {
            const x = padding + index * xScale;
            const y = height - padding - (value - minValue) * yScale;
            
            if (index === 0) {
                pathData += `M ${x} ${y}`;
            } else {
                pathData += ` L ${x} ${y}`;
            }
        });

        path.setAttribute('d', pathData);
        path.setAttribute('stroke', color);
        path.setAttribute('stroke-width', '2');
        path.setAttribute('fill', 'none');
        path.setAttribute('stroke-linecap', 'round');
        path.setAttribute('stroke-linejoin', 'round');

        // Add area fill
        const areaPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        const areaData = pathData + ` L ${padding + (data.length - 1) * xScale} ${height - padding} L ${padding} ${height - padding} Z`;
        areaPath.setAttribute('d', areaData);
        areaPath.setAttribute('fill', color);
        areaPath.setAttribute('opacity', '0.1');

        svg.appendChild(areaPath);
        svg.appendChild(path);

        // Add dots for data points
        data.forEach((value, index) => {
            const x = padding + index * xScale;
            const y = height - padding - (value - minValue) * yScale;
            
            const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            circle.setAttribute('cx', x);
            circle.setAttribute('cy', y);
            circle.setAttribute('r', '2');
            circle.setAttribute('fill', color);
            svg.appendChild(circle);
        });

        container.innerHTML = '';
        container.appendChild(svg);

        sparklineCharts.set(containerId, { svg, data, color });
    }

    /**
     * Initialize activity timeline
     */
    function initActivityTimeline() {
        const timelineContainer = document.getElementById('activityTimeline');
        if (!timelineContainer) return;

        activityTimeline = timelineContainer;
        loadActivityTimeline();
    }

    /**
     * Load activity timeline data
     */
    async function loadActivityTimeline() {
        try {
            const response = await fetch('/api/activity/timeline', {
                credentials: 'same-origin'
            });

            if (!response.ok) {
                throw new Error('Failed to load activity timeline');
            }

            const data = await response.json();
            renderActivityTimeline(data.activities || []);
        } catch (error) {
            console.error('Error loading activity timeline:', error);
            // Fallback to empty timeline
            renderActivityTimeline([]);
        }
    }

    /**
     * Render activity timeline
     */
    function renderActivityTimeline(activities) {
        if (!activityTimeline) return;

        if (activities.length === 0) {
            activityTimeline.innerHTML = `
                <div class="text-center py-8 text-text-muted-light dark:text-text-muted-dark">
                    <i class="fas fa-inbox text-4xl mb-4 opacity-50"></i>
                    <p>No recent activity</p>
                </div>
            `;
            return;
        }

        const timelineHTML = activities.map(activity => {
            const icon = getActivityIcon(activity.type);
            const color = getActivityColor(activity.type);
            const timeAgo = formatTimeAgo(activity.created_at);

            return `
                <div class="activity-timeline-item">
                    <div class="flex items-start gap-3">
                        <div class="flex-shrink-0 w-8 h-8 rounded-full ${color} flex items-center justify-center">
                            <i class="${icon} text-sm"></i>
                        </div>
                        <div class="flex-1">
                            <p class="text-sm text-text-light dark:text-text-dark">${activity.description || 'Activity'}</p>
                            <p class="text-xs text-text-muted-light dark:text-text-muted-dark">${timeAgo}</p>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        activityTimeline.innerHTML = `
            <div class="activity-timeline">
                ${timelineHTML}
            </div>
        `;
    }

    /**
     * Get activity icon
     */
    function getActivityIcon(type) {
        const icons = {
            'time_entry': 'fas fa-clock',
            'task_created': 'fas fa-plus-circle',
            'task_updated': 'fas fa-edit',
            'task_completed': 'fas fa-check-circle',
            'project_created': 'fas fa-folder-plus',
            'project_updated': 'fas fa-folder-open',
            'default': 'fas fa-circle'
        };
        return icons[type] || icons.default;
    }

    /**
     * Get activity color
     */
    function getActivityColor(type) {
        const colors = {
            'time_entry': 'bg-blue-100 dark:bg-blue-900/30 text-blue-600',
            'task_created': 'bg-green-100 dark:bg-green-900/30 text-green-600',
            'task_updated': 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-600',
            'task_completed': 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600',
            'project_created': 'bg-purple-100 dark:bg-purple-900/30 text-purple-600',
            'project_updated': 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600',
            'default': 'bg-gray-100 dark:bg-gray-700 text-gray-600'
        };
        return colors[type] || colors.default;
    }

    /**
     * Format time ago
     */
    function formatTimeAgo(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) {
            return 'Just now';
        } else if (diffMins < 60) {
            return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
        } else if (diffHours < 24) {
            return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
        } else if (diffDays < 7) {
            return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
        } else {
            return window.formatUserDate ? window.formatUserDate(date) : date.toLocaleDateString();
        }
    }

    /**
     * Initialize real-time updates (only on dashboard page; avoids repeated API calls on other pages)
     */
    function initRealTimeUpdates() {
        if (!isDashboardPage()) return;

        // Avoid stacking intervals if init runs more than once
        if (realTimeUpdateInterval) {
            clearInterval(realTimeUpdateInterval);
            realTimeUpdateInterval = null;
        }

        // Add real-time indicator
        const dashboard = document.querySelector('[data-dashboard]');
        if (dashboard) {
            const indicator = document.createElement('div');
            indicator.className = 'real-time-indicator';
            indicator.innerHTML = '<span>Live</span>';
            dashboard.insertBefore(indicator, dashboard.firstChild);
        }

        // Start real-time update interval
        realTimeUpdateInterval = setInterval(() => {
            updateDashboardData();
        }, 30000); // Update every 30 seconds

        // Update immediately (throttled inside updateDashboardData)
        updateDashboardData();
    }

    /**
     * Update dashboard data (throttled to prevent runaway callers from causing requests every few ms)
     */
    async function updateDashboardData() {
        if (!isDashboardPage()) return;
        const now = Date.now();
        if (now - lastDashboardUpdateAt < MIN_UPDATE_INTERVAL_MS) return;
        lastDashboardUpdateAt = now;

        try {
            // Update stats
            await updateStats();

            // Update activity timeline
            if (activityTimeline) {
                await loadActivityTimeline();
            }

            // Update sparklines
            await updateSparklines();
        } catch (error) {
            console.error('Error updating dashboard:', error);
        }
    }

    /**
     * Update stats
     */
    async function updateStats() {
        try {
            const response = await fetch('/api/dashboard/stats', {
                credentials: 'same-origin'
            });

            if (!response.ok) {
                throw new Error('Failed to load stats');
            }

            const data = await response.json();

            // Update stat cards
            if (data.today_hours !== undefined) {
                updateStatCard('todayHoursValue', data.today_hours);
            }
            if (data.week_hours !== undefined) {
                updateStatCard('weekHoursValue', data.week_hours);
            }
            if (data.month_hours !== undefined) {
                updateStatCard('monthHoursValue', data.month_hours);
            }

            // Update overtime lines (today and week)
            const todayOvertimeEl = document.getElementById('todayOvertimeLine');
            if (todayOvertimeEl && data.standard_hours_per_day !== undefined) {
                if (data.today_overtime_hours > 0) {
                    todayOvertimeEl.style.display = '';
                    todayOvertimeEl.innerHTML = '<span class="font-medium">+ ' + Number(data.today_overtime_hours).toFixed(2) + 'h overtime</span>';
                } else {
                    todayOvertimeEl.innerHTML = '<span class="text-blue-600/70 dark:text-blue-400/70">' + Number(data.today_hours).toFixed(2) + 'h / ' + Number(data.standard_hours_per_day).toFixed(1) + 'h</span>';
                    todayOvertimeEl.style.display = data.today_hours > 0 ? '' : 'none';
                }
            }
            const weekOvertimeEl = document.getElementById('weekOvertimeLine');
            if (weekOvertimeEl && data.week_overtime_hours !== undefined) {
                if (data.week_overtime_hours > 0) {
                    weekOvertimeEl.style.display = '';
                    weekOvertimeEl.innerHTML = '<span class="font-medium">+ ' + Number(data.week_overtime_hours).toFixed(2) + 'h overtime</span>';
                } else {
                    weekOvertimeEl.style.display = 'none';
                }
            }
        } catch (error) {
            console.error('Error updating stats:', error);
        }
    }

    /**
     * Update stat card
     */
    function updateStatCard(id, value) {
        const valueEl = document.getElementById(id);
        if (valueEl) {
            // Animate value change
            const oldValue = parseFloat(valueEl.textContent) || 0;
            animateValue(valueEl, oldValue, value, 1000);
        }
    }

    /**
     * Animate value change
     */
    function animateValue(element, start, end, duration) {
        const range = end - start;
        const increment = range / (duration / 16);
        let current = start;

        const timer = setInterval(() => {
            current += increment;
            if ((increment > 0 && current >= end) || (increment < 0 && current <= end)) {
                element.textContent = end.toFixed(2);
                clearInterval(timer);
            } else {
                element.textContent = current.toFixed(2);
            }
        }, 16);
    }

    /**
     * Update sparklines with real data from API
     */
    async function updateSparklines() {
        try {
            const response = await fetch('/api/dashboard/sparklines', {
                credentials: 'same-origin'
            });

            if (!response.ok) {
                throw new Error('Failed to load sparklines');
            }

            const json = await response.json();
            const data = json.success ? json : { today: json.today, week: json.week, month: json.month };
            const keys = ['today', 'week', 'month'];

            keys.forEach(key => {
                const container = document.querySelector(`[data-sparkline-id="${key}"]`);
                const series = data[key];
                if (container && Array.isArray(series) && series.length > 0) {
                    const color = container.getAttribute('data-color') || '#3b82f6';
                    createSparkline(container.id || `sparkline-${key}`, series, color);
                }
            });
        } catch (error) {
            console.error('Error updating sparklines:', error);
        }
    }

    /**
     * Cleanup on page unload
     */
    window.addEventListener('beforeunload', () => {
        if (realTimeUpdateInterval) {
            clearInterval(realTimeUpdateInterval);
        }
    });

    // Export functions for global use
    window.DashboardEnhancements = {
        createSparkline,
        loadActivityTimeline,
        updateDashboardData
    };

})();

