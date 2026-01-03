/**
 * Smart Notifications System
 * Intelligent notification management with scheduling, grouping, and priority
 */

class SmartNotificationManager {
    constructor() {
        this.notifications = [];
        this.preferences = this.loadPreferences();
        this.queue = [];
        this.permissionGranted = false;
        this.init();
    }

    init() {
        this.checkPermissionStatus();
        this.startBackgroundTasks();
        this.setupServiceWorkerMessaging();
        this.checkIdleTime();
        this.checkDeadlines();
        this.checkDailySummary();
    }

    /**
     * Check current notification permission status (without requesting)
     */
    checkPermissionStatus() {
        if ('Notification' in window) {
            this.permissionGranted = Notification.permission === 'granted';
        }
    }

    /**
     * Request notification permission (should be called from user interaction)
     */
    async requestPermission() {
        if ('Notification' in window && Notification.permission === 'default') {
            try {
                const permission = await Notification.requestPermission();
                this.permissionGranted = permission === 'granted';
                
                if (this.permissionGranted) {
                    console.log('Notification permission granted');
                    this.showNotification({
                        title: 'Notifications Enabled',
                        body: 'You will now receive notifications for important events',
                        icon: '/static/images/timetracker-logo.svg',
                        type: 'success'
                    });
                }
                return this.permissionGranted;
            } catch (error) {
                console.error('Error requesting notification permission:', error);
                return false;
            }
        }
        return this.permissionGranted;
    }

    /**
     * Show notification
     */
    show(options) {
        const {
            title,
            message,
            type = 'info',
            priority = 'normal',
            persistent = false,
            actions = [],
            group = null,
            sound = true,
            vibrate = true,
            requireInteraction = false
        } = options;

        // Check if notifications are enabled for this type
        if (!this.isEnabled(type)) {
            return null;
        }

        // Check priority and rate limiting
        if (!this.shouldShow(type, priority)) {
            this.queue.push(options);
            return null;
        }

        const notification = {
            id: this.generateId(),
            title,
            message,
            type,
            priority,
            persistent,
            actions,
            group,
            timestamp: Date.now(),
            read: false
        };

        this.notifications.push(notification);
        this.saveNotifications();

        // Show toast
        if (window.toastManager) {
            // toastManager.show expects an options object (not positional args)
            window.toastManager.show({
                message: message,
                title: title,
                type: type,
                duration: persistent ? 0 : 5000
            });
        }

        // Show browser notification if permitted
        if (this.permissionGranted && priority !== 'low') {
            this.showBrowserNotification(notification);
        }

        // Play sound
        if (sound && this.preferences.sound) {
            this.playSound(type);
        }

        // Vibrate
        if (vibrate && this.preferences.vibrate && 'vibrate' in navigator) {
            navigator.vibrate([200, 100, 200]);
        }

        // Emit event
        this.emit('notification', notification);

        return notification;
    }

    /**
     * Show browser notification
     */
    showBrowserNotification(notification) {
        if (!this.permissionGranted) return;

        const options = {
            body: notification.message,
            icon: '/static/images/timetracker-logo.svg',
            badge: '/static/images/timetracker-logo.svg',
            tag: notification.group || notification.id,
            requireInteraction: notification.priority === 'high',
            silent: !this.preferences.sound
        };

        if (notification.actions.length > 0) {
            options.actions = notification.actions.map(action => ({
                action: action.id,
                title: action.label
            }));
        }

        const n = new Notification(notification.title, options);

        n.onclick = () => {
            window.focus();
            if (notification.url) {
                window.location.href = notification.url;
            }
            n.close();
        };

        // Auto-close after 10 seconds
        setTimeout(() => n.close(), 10000);
    }

    /**
     * Scheduled notifications
     */
    schedule(options, delay) {
        setTimeout(() => {
            this.show(options);
        }, delay);
    }

    /**
     * Recurring notifications
     */
    recurring(options, interval) {
        const recur = () => {
            this.show(options);
            setTimeout(recur, interval);
        };
        
        setTimeout(recur, interval);
    }

    /**
     * Smart notifications based on user activity
     */

    // Check idle time and remind to log time
    checkIdleTime() {
        try {
            let idleTime = 0;
            let lastActivity = Date.now();
            let notificationSent = false;

            const resetTimer = () => {
                lastActivity = Date.now();
                idleTime = 0;
                notificationSent = false; // Reset notification flag on activity
            };

            // Use passive event listeners for better performance
            const resetTimerPassive = () => resetTimer();
            
            document.addEventListener('mousemove', resetTimerPassive, { passive: true });
            document.addEventListener('keydown', resetTimerPassive, { passive: true });
            document.addEventListener('click', resetTimerPassive, { passive: true });
            document.addEventListener('scroll', resetTimerPassive, { passive: true });

            setInterval(() => {
                try {
                    idleTime = Date.now() - lastActivity;
                    
                    // If idle for 30 minutes and haven't sent notification yet
                    if (idleTime > 30 * 60 * 1000 && !notificationSent) {
                        this.show({
                            title: 'Still working?',
                            message: 'You\'ve been idle for 30 minutes. Don\'t forget to log your time!',
                            type: 'info',
                            priority: 'normal',
                            actions: [
                                { id: 'log-time', label: 'Log Time' },
                                { id: 'dismiss', label: 'Dismiss' }
                            ]
                        });
                        
                        notificationSent = true; // Mark as sent to avoid spam
                    }
                } catch (error) {
                    console.error('[SmartNotifications] Error in idle time check:', error);
                }
            }, 5 * 60 * 1000); // Check every 5 minutes
        } catch (error) {
            console.error('[SmartNotifications] Error initializing idle time check:', error);
        }
    }

    // Check upcoming deadlines
    checkDeadlines() {
        try {
            let lastCheckTime = 0;
            const checkInterval = 60 * 60 * 1000; // 1 hour
            const notifiedDeadlines = new Set(); // Track notified deadlines to avoid duplicates
            
            const checkDeadlinesNow = async () => {
                try {
                    // Skip if checked recently (within last 50 minutes)
                    const now = Date.now();
                    if (now - lastCheckTime < checkInterval - 10 * 60 * 1000) {
                        return;
                    }
                    lastCheckTime = now;
                    
                    // Check if fetch is available
                    if (typeof fetch === 'undefined') {
                        console.warn('[SmartNotifications] Fetch not available for deadline check');
                        return;
                    }
                    
                    const response = await fetch('/api/deadlines/upcoming', {
                        method: 'GET',
                        headers: {
                            'Content-Type': 'application/json'
                        }
                    });
                    
                    // Check if response is OK before reading body
                    if (!response.ok) {
                        // Log status but don't throw error
                        if (response.status !== 404) {
                            console.warn('[SmartNotifications] Deadline check failed:', response.status, response.statusText);
                        }
                        return;
                    }
                    
                    const deadlines = await response.json();
                    
                    // Validate response is an array
                    if (!Array.isArray(deadlines)) {
                        console.warn('[SmartNotifications] Invalid deadlines response format');
                        return;
                    }
                    
                    deadlines.forEach(deadline => {
                        try {
                            // Validate deadline structure
                            if (!deadline || !deadline.due_date || !deadline.task_id) {
                                return;
                            }
                            
                            const deadlineKey = `deadline_${deadline.task_id}`;
                            
                            // Skip if already notified
                            if (notifiedDeadlines.has(deadlineKey)) {
                                return;
                            }
                            
                            const dueDate = new Date(deadline.due_date);
                            if (isNaN(dueDate.getTime())) {
                                console.warn('[SmartNotifications] Invalid due date:', deadline.due_date);
                                return;
                            }
                            
                            const timeUntil = dueDate.getTime() - Date.now();
                            const hoursUntil = timeUntil / (1000 * 60 * 60);
                            
                            // Notify if deadline is within 24 hours
                            if (hoursUntil <= 24 && hoursUntil > 0) {
                                this.show({
                                    title: 'Deadline Approaching',
                                    message: `${deadline.task_name || 'Task'} is due in ${Math.round(hoursUntil)} hours`,
                                    type: 'warning',
                                    priority: 'high',
                                    url: `/tasks/${deadline.task_id}`,
                                    group: 'deadlines'
                                });
                                
                                notifiedDeadlines.add(deadlineKey);
                                
                                // Remove from set after 25 hours to allow re-notification if deadline changes
                                setTimeout(() => {
                                    notifiedDeadlines.delete(deadlineKey);
                                }, 25 * 60 * 60 * 1000);
                            }
                        } catch (deadlineError) {
                            console.error('[SmartNotifications] Error processing deadline:', deadlineError);
                        }
                    });
                } catch (error) {
                    // Only log if it's not a network/abort error (which are expected in some cases)
                    if (error.name !== 'AbortError' && error.name !== 'TypeError') {
                        console.error('[SmartNotifications] Error checking deadlines:', error);
                    }
                }
            };
            
            // Initial check after 1 minute (to avoid immediate check on page load)
            setTimeout(checkDeadlinesNow, 60 * 1000);
            
            // Then check every hour
            setInterval(checkDeadlinesNow, checkInterval);
        } catch (error) {
            console.error('[SmartNotifications] Error initializing deadline check:', error);
        }
    }

    // Daily summary
    checkDailySummary() {
        try {
            let lastSummarySent = null;
            const targetHour = 18; // 6 PM
            
            const sendSummary = () => {
                try {
                    const now = new Date();
                    const hour = now.getHours();
                    const date = now.toDateString();
                    
                    // Send at 6 PM, but only once per day
                    if (hour === targetHour && lastSummarySent !== date) {
                        this.sendDailySummary();
                        lastSummarySent = date;
                    }
                } catch (error) {
                    console.error('[SmartNotifications] Error in daily summary check:', error);
                }
            };

            // Check every hour
            setInterval(sendSummary, 60 * 60 * 1000);
            
            // Also check immediately if it's already 6 PM
            const now = new Date();
            if (now.getHours() === targetHour) {
                sendSummary();
            }
        } catch (error) {
            console.error('[SmartNotifications] Error initializing daily summary check:', error);
        }
    }

    async sendDailySummary() {
        if (!this.preferences.dailySummary) return;

        try {
            // Check if fetch is available
            if (typeof fetch === 'undefined') {
                console.warn('[SmartNotifications] Fetch not available for daily summary');
                return;
            }
            
            const response = await fetch('/api/summary/today', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            // Check if response is OK before reading body
            if (!response.ok) {
                // Log status but don't throw error (404 is expected if endpoint doesn't exist)
                if (response.status !== 404) {
                    console.warn('[SmartNotifications] Daily summary check failed:', response.status, response.statusText);
                }
                return;
            }
            
            const summary = await response.json();

            // Safely extract values with defaults
            const hours = (summary && typeof summary.hours === 'number')
                ? summary.hours
                : (summary && summary.hours ? Number(summary.hours) : 0);
            const projects = (summary && typeof summary.projects === 'number')
                ? summary.projects
                : (summary && summary.projects ? Number(summary.projects) : 0);

            // Build a safe, human-friendly message
            const hoursText = isNaN(hours) || hours < 0 ? '0' : hours.toFixed(1);
            const projectsText = isNaN(projects) || projects < 0 ? '0' : String(projects);
            const message = `Today you logged ${hoursText}h across ${projectsText} project${projects !== 1 ? 's' : ''}. Great work!`;

            // Auto-dismiss after 8s; no permanent sticky summary to avoid lingering toasts
            if (window.toastManager && typeof window.toastManager.show === 'function') {
                window.toastManager.show({
                    message: message,
                    title: 'Daily Summary',
                    type: 'success',
                    duration: 8000
                });
            } else {
                this.show({
                    title: 'Daily Summary',
                    message,
                    type: 'success',
                    priority: 'normal',
                    persistent: false
                });
            }
        } catch (error) {
            // Only log if it's not a network/abort error (which are expected in some cases)
            if (error.name !== 'AbortError' && error.name !== 'TypeError') {
                console.error('[SmartNotifications] Error fetching daily summary:', error);
            }
        }
    }

    // Budget alerts
    budgetAlert(project, percentage) {
        let type = 'info';
        let priority = 'normal';
        
        if (percentage >= 90) {
            type = 'error';
            priority = 'high';
        } else if (percentage >= 75) {
            type = 'warning';
            priority = 'normal';
        }

        this.show({
            title: 'Budget Alert',
            message: `${project.name} has used ${percentage}% of its budget`,
            type,
            priority,
            url: `/projects/${project.id}`,
            group: 'budget-alerts'
        });
    }

    // Achievement notifications
    achievement(achievement) {
        this.show({
            title: '🎉 Achievement Unlocked!',
            message: achievement.title,
            type: 'success',
            priority: 'normal',
            persistent: true,
            sound: true,
            vibrate: true
        });
    }

    // Team activity
    teamActivity(activity) {
        this.show({
            title: 'Team Update',
            message: activity.message,
            type: 'info',
            priority: 'low',
            group: 'team-activity'
        });
    }

    /**
     * Notification management
     */

    getAll() {
        return this.notifications;
    }

    getUnread() {
        return this.notifications.filter(n => !n.read);
    }

    markAsRead(id) {
        const notification = this.notifications.find(n => n.id === id);
        if (notification) {
            notification.read = true;
            this.saveNotifications();
            this.emit('read', notification);
        }
    }

    markAllAsRead() {
        this.notifications.forEach(n => n.read = true);
        this.saveNotifications();
        this.emit('allRead');
    }

    delete(id) {
        this.notifications = this.notifications.filter(n => n.id !== id);
        this.saveNotifications();
        this.emit('deleted', id);
    }

    deleteAll() {
        this.notifications = [];
        this.saveNotifications();
        this.emit('allDeleted');
    }

    /**
     * Preferences
     */

    isEnabled(type) {
        return this.preferences[type] !== false;
    }

    shouldShow(type, priority) {
        // Rate limiting logic
        const recent = this.notifications.filter(n => 
            n.type === type && 
            Date.now() - n.timestamp < 60000 // Last minute
        );

        // Don't show more than 3 of the same type per minute
        return recent.length < 3;
    }

    updatePreferences(prefs) {
        this.preferences = { ...this.preferences, ...prefs };
        localStorage.setItem('notification_preferences', JSON.stringify(this.preferences));
    }

    loadPreferences() {
        try {
            const saved = localStorage.getItem('notification_preferences');
            return saved ? JSON.parse(saved) : {
                enabled: true,
                sound: true,
                vibrate: true,
                dailySummary: true,
                deadlines: true,
                budgetAlerts: true,
                teamActivity: true,
                achievements: true,
                info: true,
                success: true,
                warning: true,
                error: true
            };
        } catch {
            return { enabled: true };
        }
    }

    /**
     * Storage
     */

    saveNotifications() {
        // Only keep last 50 notifications
        const toSave = this.notifications.slice(-50);
        localStorage.setItem('notifications', JSON.stringify(toSave));
    }

    loadNotifications() {
        try {
            const saved = localStorage.getItem('notifications');
            return saved ? JSON.parse(saved) : [];
        } catch {
            return [];
        }
    }

    /**
     * Utilities
     */

    generateId() {
        return `notif_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    playSound(type) {
        const soundMap = {
            success: 'notification-success.mp3',
            error: 'notification-error.mp3',
            warning: 'notification-warning.mp3',
            info: 'notification-info.mp3'
        };

        const audio = new Audio(`/static/sounds/${soundMap[type] || soundMap.info}`);
        audio.volume = 0.5;
        audio.play().catch(() => {}); // Silently fail if sounds don't exist
    }

    emit(event, data) {
        window.dispatchEvent(new CustomEvent(`notification:${event}`, { detail: data }));
    }

    /**
     * Service Worker integration
     */

    setupServiceWorkerMessaging() {
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.addEventListener('message', (event) => {
                if (event.data.type === 'NOTIFICATION') {
                    this.show(event.data.payload);
                }
            });
        }
    }

    startBackgroundTasks() {
        try {
            // Background sync for notifications
            if ('serviceWorker' in navigator) {
                navigator.serviceWorker.ready.then(registration => {
                    try {
                        if (registration && 'sync' in registration && registration.sync) {
                            registration.sync.register('sync-notifications').catch((error) => {
                                // Sync not supported or failed, ignore silently
                                console.debug('[SmartNotifications] Background sync not available:', error);
                            });
                        }
                    } catch (error) {
                        console.debug('[SmartNotifications] Error registering background sync:', error);
                    }
                }).catch((error) => {
                    // Service worker not ready, ignore silently
                    console.debug('[SmartNotifications] Service worker not ready:', error);
                });
            }
        } catch (error) {
            console.error('[SmartNotifications] Error starting background tasks:', error);
        }
    }
}

// Create notification center UI
class NotificationCenter {
    constructor(manager) {
        this.manager = manager;
        this.createUI();
        this.attachListeners();
    }

    createUI() {
        const button = document.createElement('button');
        button.id = 'notificationCenterBtn';
        button.className = 'relative p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors';
        button.innerHTML = `
            <i class="fas fa-bell text-lg"></i>
            <span id="notificationBadge" class="hidden absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">0</span>
        `;

        // Insert into header
        const header = document.querySelector('header .flex.items-center.space-x-4');
        if (header) {
            header.insertBefore(button, header.firstChild);
        }

        this.updateBadge();
    }

    attachListeners() {
        const btn = document.getElementById('notificationCenterBtn');
        if (btn) {
            btn.addEventListener('click', () => this.toggle());
        }

        // Listen for new notifications
        window.addEventListener('notification:notification', () => this.updateBadge());
        window.addEventListener('notification:read', () => this.updateBadge());
        window.addEventListener('notification:allRead', () => this.updateBadge());
    }

    updateBadge() {
        const badge = document.getElementById('notificationBadge');
        const unread = this.manager.getUnread().length;
        
        if (badge) {
            badge.textContent = unread;
            badge.classList.toggle('hidden', unread === 0);
        }
    }

    toggle() {
        // Show notification panel
        const panel = this.createPanel();
        document.body.appendChild(panel);
    }

    createPanel() {
        const panel = document.createElement('div');
        panel.className = 'fixed inset-0 z-50 overflow-hidden';
        
        const permissionBanner = !this.manager.permissionGranted && 'Notification' in window && Notification.permission === 'default' ? `
            <div class="p-4 bg-yellow-50 dark:bg-yellow-900/20 border-b border-yellow-200 dark:border-yellow-800">
                <div class="flex items-center justify-between">
                    <div class="flex items-center gap-3">
                        <i class="fas fa-bell text-yellow-600 dark:text-yellow-400"></i>
                        <div>
                            <p class="text-sm font-medium text-gray-900 dark:text-gray-100">Enable Notifications</p>
                            <p class="text-xs text-gray-600 dark:text-gray-400">Get notified about important events</p>
                        </div>
                    </div>
                    <button 
                        onclick="smartNotifications.requestPermission().then(() => { this.closest('.fixed').remove(); smartNotifications.notificationCenter.toggle(); })" 
                        class="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark transition-colors text-sm font-medium"
                    >
                        Enable
                    </button>
                </div>
            </div>
        ` : '';
        
        panel.innerHTML = `
            <div class="absolute inset-0 bg-black/50" onclick="this.parentElement.remove()"></div>
            <div class="absolute right-0 top-0 h-full w-full max-w-md bg-card-light dark:bg-card-dark shadow-xl transform transition-transform">
                <div class="p-6 border-b border-border-light dark:border-border-dark flex justify-between items-center">
                    <h2 class="text-xl font-bold">Notifications</h2>
                    <div class="flex gap-2">
                        <button onclick="smartNotifications.markAllAsRead(); this.closest('.fixed').remove();" class="text-sm text-primary hover:underline">
                            Mark all read
                        </button>
                        <button onclick="this.closest('.fixed').remove()" class="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                </div>
                ${permissionBanner}
                <div class="overflow-y-auto h-[calc(100%-80px)]">
                    ${this.renderNotifications()}
                </div>
            </div>
        `;
        
        return panel;
    }

    renderNotifications() {
        const notifications = this.manager.getAll().reverse();
        
        if (notifications.length === 0) {
            return `
                <div class="p-12 text-center text-gray-500">
                    <i class="fas fa-bell-slash text-4xl mb-4"></i>
                    <p>No notifications</p>
                </div>
            `;
        }

        return notifications.map(n => `
            <div class="p-4 border-b border-border-light dark:border-border-dark ${n.read ? 'opacity-60' : 'bg-blue-50 dark:bg-blue-900/20'} hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer">
                <div class="flex items-start gap-3">
                    <div class="w-10 h-10 rounded-full bg-${this.getTypeColor(n.type)}/10 flex items-center justify-center flex-shrink-0">
                        <i class="${this.getTypeIcon(n.type)} text-${this.getTypeColor(n.type)}"></i>
                    </div>
                    <div class="flex-1">
                        <h4 class="font-medium text-sm">${n.title}</h4>
                        <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">${n.message}</p>
                        <span class="text-xs text-gray-500 mt-2 block">${this.formatTime(n.timestamp)}</span>
                    </div>
                    ${!n.read ? '<div class="w-2 h-2 bg-blue-500 rounded-full"></div>' : ''}
                </div>
            </div>
        `).join('');
    }

    getTypeColor(type) {
        const colors = {
            success: 'green-500',
            error: 'red-500',
            warning: 'amber-500',
            info: 'blue-500'
        };
        return colors[type] || colors.info;
    }

    getTypeIcon(type) {
        const icons = {
            success: 'fas fa-check-circle',
            error: 'fas fa-exclamation-circle',
            warning: 'fas fa-exclamation-triangle',
            info: 'fas fa-info-circle'
        };
        return icons[type] || icons.info;
    }

    formatTime(timestamp) {
        const diff = Date.now() - timestamp;
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);
        
        if (days > 0) return `${days}d ago`;
        if (hours > 0) return `${hours}h ago`;
        if (minutes > 0) return `${minutes}m ago`;
        return 'Just now';
    }
}

// Initialize
window.smartNotifications = new SmartNotificationManager();
window.notificationCenter = new NotificationCenter(window.smartNotifications);

console.log('Smart notifications initialized');

