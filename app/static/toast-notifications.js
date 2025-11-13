/**
 * Modern Toast Notification System
 * Professional notification manager with animations and auto-dismiss
 */

class ToastNotificationManager {
    constructor() {
        this.container = null;
        this.toasts = new Map();
        this.maxToasts = 5;
        this.defaultDuration = 5000;
        this.init();
    }

    init() {
        // Create container if it doesn't exist
        if (!document.getElementById('toast-notification-container')) {
            this.container = document.createElement('div');
            this.container.id = 'toast-notification-container';
            this.container.setAttribute('role', 'region');
            this.container.setAttribute('aria-label', 'Notifications');
            document.body.appendChild(this.container);
        } else {
            this.container = document.getElementById('toast-notification-container');
        }
    }

    /**
     * Show a toast notification
     * @param {Object} options - Toast options
     * @param {string} options.message - Message text (required)
     * @param {string} options.title - Toast title (optional)
     * @param {string} options.type - Type: success, error, warning, info (default: info)
     * @param {number} options.duration - Duration in ms (default: 5000, 0 = no auto-dismiss)
     * @param {boolean} options.dismissible - Show close button (default: true)
     */
    show(options) {
        if (!options || !options.message) {
            console.warn('Toast notification requires a message');
            return null;
        }

        const config = {
            message: options.message,
            title: options.title || this.getDefaultTitle(options.type),
            type: options.type || 'info',
            duration: options.duration !== undefined ? options.duration : this.defaultDuration,
            dismissible: options.dismissible !== false
        };

        const toastId = Date.now() + Math.random();
        const toast = this.createToast(config, toastId);
        
        this.toasts.set(toastId, {
            element: toast,
            config: config,
            timeoutId: null
        });

        // Add to container
        this.container.appendChild(toast);

        // Trigger animation
        requestAnimationFrame(() => {
            toast.style.opacity = '1';
            toast.style.transform = 'translateX(0) scale(1)';
        });

        // Auto-dismiss
        if (config.duration > 0) {
            const timeoutId = setTimeout(() => {
                this.dismiss(toastId);
            }, config.duration);
            this.toasts.get(toastId).timeoutId = timeoutId;
        }

        // Cleanup old toasts if too many
        this.enforceLimit();

        return toastId;
    }

    createToast(config, toastId) {
        const toast = document.createElement('div');
        toast.className = `toast-notification toast-${config.type}`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', config.type === 'error' ? 'assertive' : 'polite');
        toast.setAttribute('aria-atomic', 'true');
        if (toastId) {
            toast.setAttribute('data-toast-id', String(toastId));
        }

        // Icon
        const icon = this.getIcon(config.type);
        const iconElement = document.createElement('div');
        iconElement.className = 'toast-icon';
        iconElement.innerHTML = `<i class="${icon}"></i>`;

        // Content
        const content = document.createElement('div');
        content.className = 'toast-content';
        
        if (config.title) {
            const title = document.createElement('div');
            title.className = 'toast-title';
            title.textContent = config.title;
            content.appendChild(title);
        }

        const message = document.createElement('div');
        message.className = 'toast-message';
        message.textContent = config.message;
        content.appendChild(message);

        // Close button
        let closeBtn = null;
        if (config.dismissible) {
            closeBtn = document.createElement('button');
            closeBtn.className = 'toast-close';
            closeBtn.setAttribute('type', 'button');
            closeBtn.setAttribute('aria-label', 'Close notification');
            closeBtn.innerHTML = '<i class="fas fa-xmark"></i>';
        }

        // Progress bar
        let progressBar = null;
        if (config.duration > 0) {
            const progress = document.createElement('div');
            progress.className = 'toast-progress';
            progressBar = document.createElement('div');
            progressBar.className = 'toast-progress-bar';
            progressBar.style.animationDuration = `${config.duration}ms`;
            progress.appendChild(progressBar);
            toast.appendChild(progress);
        }

        // Assemble
        toast.appendChild(iconElement);
        toast.appendChild(content);
        if (closeBtn) toast.appendChild(closeBtn);

        // Event listeners
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                const toastId = this.findToastId(toast);
                if (toastId) this.dismiss(toastId);
            });
        }

        // Pause on hover
        if (config.duration > 0) {
            let pausedTime = 0;
            let remainingTime = config.duration;
            let pauseStart = 0;

            toast.addEventListener('mouseenter', () => {
                pauseStart = Date.now();
                if (progressBar) {
                    progressBar.style.animationPlayState = 'paused';
                }
            });

            toast.addEventListener('mouseleave', () => {
                if (pauseStart > 0) {
                    pausedTime += Date.now() - pauseStart;
                    pauseStart = 0;
                    if (progressBar) {
                        progressBar.style.animationPlayState = 'running';
                    }
                }
            });
        }

        return toast;
    }

    dismiss(toastId) {
        const toastData = this.toasts.get(toastId);
        if (!toastData) return;

        const { element, timeoutId } = toastData;

        // Clear timeout
        if (timeoutId) {
            clearTimeout(timeoutId);
        }

        // Animate out
        element.classList.add('hiding');

        setTimeout(() => {
            if (element.parentNode) {
                element.parentNode.removeChild(element);
            }
            this.toasts.delete(toastId);
        }, 300);
    }

    dismissAll() {
        this.toasts.forEach((_, toastId) => {
            this.dismiss(toastId);
        });
    }

    findToastId(element) {
        for (const [id, data] of this.toasts.entries()) {
            if (data.element === element) {
                return id;
            }
        }
        return null;
    }

    enforceLimit() {
        if (this.toasts.size > this.maxToasts) {
            const oldestId = this.toasts.keys().next().value;
            this.dismiss(oldestId);
        }
    }

    getIcon(type) {
        const icons = {
            success: 'fas fa-check-circle',
            error: 'fas fa-exclamation-circle',
            warning: 'fas fa-exclamation-triangle',
            info: 'fas fa-info-circle'
        };
        return icons[type] || icons.info;
    }

    getDefaultTitle(type) {
        // Try to get translated titles from window.i18n if available
        // These are injected by the backend in base template
        if (window.i18n && window.i18n.toast) {
            const titles = window.i18n.toast;
            return titles[type] || titles.info || 'Information';
        }
        
        // Fallback to English if translations not loaded
        const titles = {
            success: 'Success',
            error: 'Error',
            warning: 'Warning',
            info: 'Information'
        };
        return titles[type] || titles.info;
    }

    // Convenience methods
    success(message, title, duration) {
        return this.show({ message, title, type: 'success', duration });
    }

    error(message, title, duration) {
        return this.show({ message, title, type: 'error', duration });
    }

    warning(message, title, duration) {
        return this.show({ message, title, type: 'warning', duration });
    }

    info(message, title, duration) {
        return this.show({ message, title, type: 'info', duration });
    }
}

// Initialize global instance
window.toastManager = new ToastNotificationManager();

// Backwards compatibility with existing showToast function
window.showToast = function(message, type = 'info') {
    window.toastManager.show({
        message: message,
        type: type === 'danger' ? 'error' : type,
        duration: 5000
    });
};

// Also create a more descriptive global function
window.showNotification = function(message, options = {}) {
    return window.toastManager.show({
        message: message,
        ...options
    });
};

// Convert flash messages to toasts on page load
document.addEventListener('DOMContentLoaded', function() {
    // ONLY convert flash messages from the special container, not all alerts
    const flashContainer = document.getElementById('flash-messages-container');
    if (!flashContainer) return;
    
    const alerts = flashContainer.querySelectorAll('.alert');
    
    alerts.forEach(alert => {
        // Get message from data attribute or text content
        const message = alert.getAttribute('data-toast-message') || alert.textContent.trim();
        if (!message) return;

        // Get type from data attribute or class
        let type = alert.getAttribute('data-toast-type') || 'info';
        if (alert.classList.contains('alert-success')) type = 'success';
        else if (alert.classList.contains('alert-danger')) type = 'error';
        else if (alert.classList.contains('alert-warning')) type = 'warning';
        else if (alert.classList.contains('alert-info')) type = 'info';

        // Show as toast
        window.toastManager.show({
            message: message,
            type: type,
            duration: 6000
        });

        // Mark as converted (no need to hide, container is already hidden)
        alert.classList.add('toast-converted');
    });
});

console.log('Toast Notification System initialized');

