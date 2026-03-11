/**
 * Modern Toast Notification System
 * Professional notification manager with animations and auto-dismiss
 */

class ToastNotificationManager {
    constructor() {
        this.container = null;
        this.toasts = new Map();
        this.maxToasts = 4;
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
            Object.assign(this.container.style, {
                position: 'fixed',
                top: '5rem',
                right: '1rem',
                left: 'auto',
                bottom: 'auto',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'flex-end',
                gap: '0.75rem',
                zIndex: '9999',
                pointerEvents: 'none',
                width: 'auto',
                maxWidth: 'calc(100vw - 1rem)'
            });
            document.body.appendChild(this.container);
        } else {
            this.container = document.getElementById('toast-notification-container');
        }

        this.applyResponsiveContainerStyles();
        window.addEventListener('resize', () => this.applyResponsiveContainerStyles());
    }

    applyResponsiveContainerStyles() {
        if (!this.container) return;
        if (window.innerWidth <= 640) {
            Object.assign(this.container.style, {
                top: '0.75rem',
                right: '0.75rem',
                left: 'auto',
                maxWidth: 'calc(100vw - 1.5rem)',
                alignItems: 'flex-end'
            });
        } else {
            Object.assign(this.container.style, {
                top: '5rem',
                right: '1rem',
                left: 'auto',
                maxWidth: 'calc(100vw - 1rem)',
                alignItems: 'flex-end'
            });
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
     * @param {string} options.actionLink - Optional URL for action link
     * @param {string} options.actionLabel - Label for action link (e.g. "View time entries")
     */
    show(options) {
        if (!options || !options.message) {
            console.warn('Toast notification requires a message');
            return null;
        }

        // Ensure message is always a string
        let message = options.message;
        // Prefer common object shapes before stringifying
        if (message && typeof message === 'object') {
            if (typeof message.message === 'string') {
                message = message.message;
            } else if (typeof message.error === 'string') {
                message = message.error;
            }
        }
        if (typeof message !== 'string') {
            try {
                message = JSON.stringify(message);
            } catch (e) {
                message = String(message);
            }
        }

        const config = {
            message: message,
            title: Object.prototype.hasOwnProperty.call(options, 'title')
                ? options.title
                : this.getDefaultTitle(options.type),
            type: options.type || 'info',
            duration: options.duration !== undefined ? options.duration : this.defaultDuration,
            dismissible: options.dismissible !== false,
            actionLink: options.actionLink || '',
            actionLabel: options.actionLabel || ''
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
        const isDark = document.documentElement.classList.contains('dark');
        const accentMap = {
            success: '#10B981',
            error: '#EF4444',
            warning: '#F59E0B',
            info: '#3B82F6'
        };
        const accent = accentMap[config.type] || accentMap.info;
        const toast = document.createElement('div');
        toast.className = `toast-notification toast-${config.type}`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', config.type === 'error' ? 'assertive' : 'polite');
        toast.setAttribute('aria-atomic', 'true');
        if (toastId) {
            toast.setAttribute('data-toast-id', String(toastId));
        }
        Object.assign(toast.style, {
            display: 'block',
            width: 'min(20rem, calc(100vw - 1.5rem))',
            maxWidth: 'calc(100vw - 1.5rem)',
            marginLeft: 'auto',
            background: isDark ? '#2D3748' : '#FFFFFF',
            color: isDark ? '#E2E8F0' : '#2D3748',
            border: `1px solid ${isDark ? '#4A5568' : '#E2E8F0'}`,
            borderLeft: `4px solid ${accent}`,
            borderRadius: '0.875rem',
            padding: '0.875rem 0.95rem',
            boxShadow: '0 14px 32px rgba(15,23,42,0.16), 0 4px 10px rgba(15,23,42,0.08)',
            opacity: '0',
            transform: 'translateY(-8px) scale(0.98)',
            transition: 'opacity 180ms ease, transform 180ms ease',
            pointerEvents: 'auto',
            overflow: 'hidden'
        });

        // Icon
        const icon = this.getIcon(config.type);
        const iconElement = document.createElement('div');
        iconElement.className = 'tt-toast-icon';
        iconElement.innerHTML = `<i class="${icon}"></i>`;
        Object.assign(iconElement.style, {
            lineHeight: '1',
            fontSize: '0.95rem',
            width: '1.9rem',
            height: '1.9rem',
            borderRadius: '9999px',
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: '0',
            background: isDark ? 'rgba(148,163,184,0.18)' : 'rgba(148,163,184,0.12)',
            marginTop: '0.05rem',
            color: accent
        });

        // Content
        const content = document.createElement('div');
        content.className = 'tt-toast-content';
        Object.assign(content.style, {
            minWidth: '0',
            paddingRight: '0'
        });
        
        if (config.title) {
            const title = document.createElement('div');
            title.className = 'tt-toast-title';
            title.textContent = config.title;
            Object.assign(title.style, {
                fontWeight: '700',
                marginBottom: '0.2rem',
                lineHeight: '1.2',
                fontSize: '0.95rem'
            });
            content.appendChild(title);
        }

        const message = document.createElement('div');
        message.className = 'tt-toast-message';
        message.textContent = config.message;
        Object.assign(message.style, {
            fontSize: '0.915rem',
            lineHeight: '1.4',
            color: 'inherit',
            opacity: '0.9',
            overflowWrap: 'anywhere'
        });
        content.appendChild(message);

        if (config.actionLink && config.actionLabel) {
            const actionLink = document.createElement('a');
            actionLink.href = config.actionLink;
            actionLink.textContent = config.actionLabel;
            actionLink.className = 'tt-toast-action';
            Object.assign(actionLink.style, {
                display: 'inline-block',
                marginTop: '0.35rem',
                fontSize: '0.875rem',
                fontWeight: '600',
                color: 'inherit',
                opacity: '0.95',
                textDecoration: 'underline'
            });
            content.appendChild(actionLink);
        }

        // Close button
        let closeBtn = null;
        if (config.dismissible) {
            closeBtn = document.createElement('button');
            closeBtn.className = 'tt-toast-close';
            closeBtn.setAttribute('type', 'button');
            closeBtn.setAttribute('aria-label', 'Close notification');
            closeBtn.innerHTML = '<i class="fas fa-xmark"></i>';
            Object.assign(closeBtn.style, {
                position: 'static',
                marginLeft: '0',
                background: 'transparent',
                border: '0',
                color: 'inherit',
                opacity: '0.72',
                cursor: 'pointer',
                width: '1.9rem',
                height: '1.9rem',
                borderRadius: '0.5rem',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: '0'
            });
        }

        const body = document.createElement('div');
        body.className = 'tt-toast-body';
        Object.assign(body.style, {
            display: 'grid',
            gridTemplateColumns: '1.9rem minmax(0, 1fr) 1.9rem',
            alignItems: 'flex-start',
            gap: '0.75rem'
        });
        body.appendChild(iconElement);
        body.appendChild(content);
        if (closeBtn) body.appendChild(closeBtn);

        // Progress bar
        let progressBar = null;
        if (config.duration > 0) {
            const progress = document.createElement('div');
            progress.className = 'tt-toast-progress';
            progressBar = document.createElement('div');
            progressBar.className = 'tt-toast-progress-bar';
            progressBar.style.animationDuration = `${config.duration}ms`;
            Object.assign(progress.style, {
                position: 'relative',
                height: '3px',
                overflow: 'hidden',
                borderRadius: '9999px',
                marginTop: '0.7rem',
                background: isDark ? 'rgba(148,163,184,0.24)' : 'rgba(148,163,184,0.18)'
            });
            Object.assign(progressBar.style, {
                position: 'absolute',
                left: '0',
                top: '0',
                height: '100%',
                width: '100%',
                background: accent,
                animationName: 'toast-progress-shrink',
                animationTimingFunction: 'linear',
                animationFillMode: 'forwards'
            });
            progress.appendChild(progressBar);
            toast.appendChild(progress);
        }

        // Assemble
        toast.prepend(body);

        // Event listeners
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                const toastId = this.findToastId(toast);
                if (toastId) this.dismiss(toastId);
            });
            closeBtn.addEventListener('mouseenter', () => {
                closeBtn.style.opacity = '1';
                closeBtn.style.background = isDark ? 'rgba(148,163,184,0.18)' : 'rgba(148,163,184,0.12)';
            });
            closeBtn.addEventListener('mouseleave', () => {
                closeBtn.style.opacity = '0.72';
                closeBtn.style.background = 'transparent';
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
        let message = alert.getAttribute('data-toast-message') || alert.textContent.trim();
        if (!message) return;
        
        // Ensure message is a string (handle objects that might have been passed)
        if (typeof message !== 'string') {
            try {
                message = JSON.stringify(message);
            } catch (e) {
                message = String(message);
            }
        }

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
            duration: 6000,
            title: null
        });

        // Mark as converted (no need to hide, container is already hidden)
        alert.classList.add('toast-converted');
    });
});


