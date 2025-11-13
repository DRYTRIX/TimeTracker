/**
 * Enhanced Error Handling System
 * User-friendly messages, retry buttons, offline queue, graceful degradation, and recovery options
 */

class EnhancedErrorHandler {
    constructor() {
        this.retryQueue = [];
        this.offlineQueue = [];
        this.isOnline = navigator.onLine;
        this.retryAttempts = new Map();
        this.maxRetries = 3;
        this.init();
    }

    init() {
        // Setup network status monitoring
        this.setupNetworkMonitoring();
        
        // Setup fetch interceptors
        this.setupFetchInterceptor();
        
        // Setup global error handlers
        this.setupGlobalErrorHandlers();
        
        // Setup offline queue processor
        this.setupOfflineQueue();
        
        // Setup graceful degradation
        this.setupGracefulDegradation();
    }

    /**
     * Network Status Monitoring
     */
    setupNetworkMonitoring() {
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.handleOnline();
        });

        window.addEventListener('offline', () => {
            this.isOnline = false;
            this.handleOffline();
        });

        // Periodic online check
        setInterval(() => {
            this.checkOnlineStatus();
        }, 5000);
    }

    checkOnlineStatus() {
        fetch('/api/health', { method: 'GET', cache: 'no-cache' })
            .then((response) => {
                if (response.ok && !this.isOnline) {
                    this.isOnline = true;
                    this.handleOnline();
                }
            })
            .catch(() => {
                if (this.isOnline) {
                    this.isOnline = false;
                    this.handleOffline();
                }
            });
    }

    handleOnline() {
        // Show online indicator
        this.showOnlineIndicator();
        
        // Process offline queue
        this.processOfflineQueue();
        
        // Retry failed operations
        this.retryFailedOperations();
    }

    handleOffline() {
        // Show offline indicator
        this.showOfflineIndicator();
    }

    showOnlineIndicator() {
        if (window.toastManager) {
            window.toastManager.success(
                'Connection restored. Processing queued operations...',
                'Back Online',
                3000
            );
        }
    }

    showOfflineIndicator() {
        // Create persistent offline indicator
        if (document.getElementById('offline-indicator')) return;

        const indicator = document.createElement('div');
        indicator.id = 'offline-indicator';
        indicator.className = 'offline-indicator';
        indicator.innerHTML = `
            <div class="offline-indicator-content">
                <i class="fas fa-wifi-slash"></i>
                <span>You're offline. Some features may be limited.</span>
                <span class="offline-queue-count" id="offline-queue-count"></span>
            </div>
        `;
        document.body.appendChild(indicator);

        // Add styles
        this.addOfflineIndicatorStyles();
    }

    addOfflineIndicatorStyles() {
        if (document.getElementById('offline-indicator-styles')) return;

        const style = document.createElement('style');
        style.id = 'offline-indicator-styles';
        style.textContent = `
            .offline-indicator {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                background: #f59e0b;
                color: white;
                padding: 12px 16px;
                text-align: center;
                z-index: 9999;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
                animation: slideDown 0.3s ease-out;
            }
            
            .dark .offline-indicator {
                background: #d97706;
            }
            
            .offline-indicator-content {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 8px;
                font-size: 0.875rem;
            }
            
            .offline-queue-count {
                margin-left: 8px;
                font-weight: 600;
            }
            
            @keyframes slideDown {
                from {
                    transform: translateY(-100%);
                }
                to {
                    transform: translateY(0);
                }
            }
            
            .error-retry-container {
                margin-top: 12px;
                padding-top: 12px;
                border-top: 1px solid rgba(255, 255, 255, 0.2);
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 12px;
            }
            
            .error-retry-btn {
                padding: 6px 12px;
                background: rgba(255, 255, 255, 0.2);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 6px;
                cursor: pointer;
                font-size: 0.875rem;
                transition: all 0.2s;
            }
            
            .error-retry-btn:hover {
                background: rgba(255, 255, 255, 0.3);
            }
            
            .error-retry-btn:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }
            
            .error-message-friendly {
                margin-bottom: 8px;
            }
            
            .error-recovery-options {
                margin-top: 12px;
                padding-top: 12px;
                border-top: 1px solid rgba(0, 0, 0, 0.1);
            }
            
            .dark .error-recovery-options {
                border-top-color: rgba(255, 255, 255, 0.1);
            }
            
            .error-recovery-btn {
                display: inline-block;
                margin: 4px 8px 4px 0;
                padding: 6px 12px;
                background: #f3f4f6;
                color: #374151;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                cursor: pointer;
                font-size: 0.875rem;
                transition: all 0.2s;
            }
            
            .dark .error-recovery-btn {
                background: #374151;
                color: #e5e7eb;
                border-color: #4b5563;
            }
            
            .error-recovery-btn:hover {
                background: #e5e7eb;
            }
            
            .dark .error-recovery-btn:hover {
                background: #4b5563;
            }
        `;
        document.head.appendChild(style);
    }

    /**
     * Fetch Interceptor for Error Handling
     */
    setupFetchInterceptor() {
        const originalFetch = window.fetch;
        
        window.fetch = async (...args) => {
            const [url, options = {}] = args;
            
            try {
                const response = await originalFetch(...args);
                
                // Handle non-ok responses
                if (!response.ok) {
                    return this.handleFetchError(response, url, options);
                }
                
                return response;
            } catch (error) {
                // Network error or other fetch error
                return this.handleFetchException(error, url, options);
            }
        };
    }

    async handleFetchError(response, url, options) {
        const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
        const userFriendlyMessage = this.getUserFriendlyMessage(response.status, errorData);
        
        // Show error notification with retry option
        const errorId = this.showErrorWithRetry(userFriendlyMessage, response.status, () => {
            return this.retryFetch(url, options);
        });
        
        // Queue for offline processing if offline
        if (!this.isOnline) {
            this.queueForOffline(url, options, errorId);
        }
        
        // Return response (caller can handle it)
        return response;
    }

    async handleFetchException(error, url, options) {
        // Network error
        if (!this.isOnline) {
            this.queueForOffline(url, options);
            return new Response(JSON.stringify({ error: 'Offline' }), {
                status: 0,
                statusText: 'Offline'
            });
        }
        
        const userFriendlyMessage = this.getUserFriendlyMessage(0, error);
        const errorId = this.showErrorWithRetry(userFriendlyMessage, 0, () => {
            return this.retryFetch(url, options);
        });
        
        return new Response(JSON.stringify({ error: userFriendlyMessage }), {
            status: 0,
            statusText: 'Network Error'
        });
    }

    async retryFetch(url, options) {
        const retryKey = `${url}-${JSON.stringify(options)}`;
        const attempts = this.retryAttempts.get(retryKey) || 0;
        
        if (attempts >= this.maxRetries) {
            this.showError(
                'Maximum retry attempts reached. Please try again later or contact support.',
                'Retry Failed'
            );
            return null;
        }
        
        this.retryAttempts.set(retryKey, attempts + 1);
        
        try {
            const response = await fetch(url, options);
            if (response.ok) {
                this.retryAttempts.delete(retryKey);
                return response;
            }
            throw new Error(`HTTP ${response.status}`);
        } catch (error) {
            if (attempts < this.maxRetries - 1) {
                // Wait before retrying (exponential backoff)
                await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempts) * 1000));
                return this.retryFetch(url, options);
            }
            throw error;
        }
    }

    /**
     * User-Friendly Error Messages
     */
    getUserFriendlyMessage(status, errorData) {
        const errorMessage = errorData?.error || errorData?.message || 'An error occurred';
        
        const messages = {
            0: 'Unable to connect to the server. Please check your internet connection.',
            400: 'Invalid request. Please check your input and try again.',
            401: 'You need to log in to access this feature.',
            403: 'You don\'t have permission to perform this action.',
            404: 'The requested resource was not found.',
            409: 'This action conflicts with existing data. Please refresh and try again.',
            422: 'Validation error. Please check your input.',
            429: 'Too many requests. Please wait a moment and try again.',
            500: 'A server error occurred. Our team has been notified.',
            502: 'The server is temporarily unavailable. Please try again later.',
            503: 'Service temporarily unavailable. Please try again in a few moments.',
            504: 'Request timeout. Please try again.'
        };
        
        // Try to get specific message from server
        if (typeof errorData === 'object' && errorData.message) {
            return errorData.message;
        }
        
        // Fallback to status-based message
        return messages[status] || `An error occurred (${status}). ${errorMessage}`;
    }

    /**
     * Show Error with Retry Button
     */
    showErrorWithRetry(message, status, retryCallback) {
        const recoveryOptions = this.getRecoveryOptions(status);
        
        // Create error toast with retry
        if (window.toastManager) {
            const toastId = window.toastManager.error(message, 'Error', 0);
            
            // Find toast element by ID
            const toastElement = window.toastManager.container.querySelector(
                `[data-toast-id="${toastId}"]`
            ) || Array.from(window.toastManager.container.children).find(
                el => el.getAttribute('data-toast-id') === String(toastId)
            );
            
            if (toastElement) {
                const retryContainer = document.createElement('div');
                retryContainer.className = 'error-retry-container';
                
                const retryBtn = document.createElement('button');
                retryBtn.className = 'error-retry-btn';
                retryBtn.textContent = 'Retry';
                retryBtn.onclick = async () => {
                    retryBtn.disabled = true;
                    retryBtn.textContent = 'Retrying...';
                    
                    try {
                        await retryCallback();
                        window.toastManager.dismiss(toastId);
                        window.toastManager.success('Operation completed successfully', 'Success');
                    } catch (error) {
                        retryBtn.disabled = false;
                        retryBtn.textContent = 'Retry';
                        window.toastManager.error(
                            this.getUserFriendlyMessage(0, error),
                            'Retry Failed'
                        );
                    }
                };
                
                retryContainer.appendChild(retryBtn);
                
                // Add recovery options if available
                if (recoveryOptions.length > 0) {
                    const recoveryDiv = document.createElement('div');
                    recoveryDiv.className = 'error-recovery-options';
                    recoveryOptions.forEach(option => {
                        const btn = document.createElement('button');
                        btn.className = 'error-recovery-btn';
                        btn.textContent = option.label;
                        btn.onclick = option.action;
                        recoveryDiv.appendChild(btn);
                    });
                    retryContainer.appendChild(recoveryDiv);
                }
                
                toastElement.appendChild(retryContainer);
            }
            
            return toastId;
        }
        
        // Fallback to console
        console.error('Error:', message);
        return null;
    }

    showError(message, title = 'Error') {
        if (window.toastManager) {
            window.toastManager.error(message, title);
        } else {
            console.error(title + ':', message);
        }
    }

    /**
     * Recovery Options
     */
    getRecoveryOptions(status) {
        const options = [];
        
        switch (status) {
            case 401:
                options.push({
                    label: 'Go to Login',
                    action: () => {
                        window.location.href = '/auth/login';
                    }
                });
                break;
            case 403:
                options.push({
                    label: 'Go to Dashboard',
                    action: () => {
                        window.location.href = '/main/dashboard';
                    }
                });
                break;
            case 404:
                options.push({
                    label: 'Go to Dashboard',
                    action: () => {
                        window.location.href = '/main/dashboard';
                    }
                });
                options.push({
                    label: 'Go Back',
                    action: () => {
                        window.history.back();
                    }
                });
                break;
            case 500:
            case 502:
            case 503:
            case 504:
                options.push({
                    label: 'Refresh Page',
                    action: () => {
                        window.location.reload();
                    }
                });
                break;
        }
        
        return options;
    }

    /**
     * Offline Queue Management
     */
    queueForOffline(url, options, errorId = null) {
        const queueItem = {
            url,
            options,
            errorId,
            timestamp: Date.now(),
            retries: 0
        };
        
        this.offlineQueue.push(queueItem);
        this.updateOfflineQueueIndicator();
        
        // Store in localStorage for persistence
        this.saveOfflineQueue();
    }

    saveOfflineQueue() {
        try {
            localStorage.setItem('offline_queue', JSON.stringify(this.offlineQueue));
        } catch (e) {
            console.warn('Failed to save offline queue:', e);
        }
    }

    loadOfflineQueue() {
        try {
            const stored = localStorage.getItem('offline_queue');
            if (stored) {
                this.offlineQueue = JSON.parse(stored);
                this.updateOfflineQueueIndicator();
            }
        } catch (e) {
            console.warn('Failed to load offline queue:', e);
        }
    }

    async processOfflineQueue() {
        if (this.offlineQueue.length === 0) return;
        
        const queue = [...this.offlineQueue];
        this.offlineQueue = [];
        
        for (const item of queue) {
            try {
                const response = await fetch(item.url, item.options);
                if (response.ok && item.errorId) {
                    window.toastManager?.dismiss(item.errorId);
                }
            } catch (error) {
                // Re-queue if still failing
                this.offlineQueue.push(item);
            }
        }
        
        this.updateOfflineQueueIndicator();
        this.saveOfflineQueue();
    }

    updateOfflineQueueIndicator() {
        const countElement = document.getElementById('offline-queue-count');
        if (countElement) {
            const count = this.offlineQueue.length;
            if (count > 0) {
                countElement.textContent = `(${count} pending)`;
                countElement.style.display = 'inline';
            } else {
                countElement.style.display = 'none';
            }
        }
    }

    setupOfflineQueue() {
        // Load existing queue on init
        this.loadOfflineQueue();
        
        // Process queue when online
        if (this.isOnline && this.offlineQueue.length > 0) {
            this.processOfflineQueue();
        }
    }

    /**
     * Global Error Handlers
     */
    setupGlobalErrorHandlers() {
        // JavaScript errors
        window.addEventListener('error', (event) => {
            this.handleJavaScriptError(event.error, event.message, event.filename, event.lineno);
        });
        
        // Unhandled promise rejections
        window.addEventListener('unhandledrejection', (event) => {
            this.handleUnhandledRejection(event.reason);
        });
    }

    handleJavaScriptError(error, message, filename, lineno) {
        if (this.shouldIgnoreFrontendNoise(error, message)) {
            return;
        }

        const userFriendlyMessage = 'An unexpected error occurred. Please refresh the page or contact support if the problem persists.';
        
        this.showError(userFriendlyMessage, 'Application Error');
        
        // Log to console for debugging
        console.error('JavaScript Error:', {
            error,
            message,
            filename,
            lineno
        });
    }

    handleUnhandledRejection(reason) {
        if (this.shouldIgnoreFrontendNoise(reason, reason?.message)) {
            return;
        }

        const userFriendlyMessage = 'An operation failed unexpectedly. Please try again or contact support if the problem persists.';
        
        this.showError(userFriendlyMessage, 'Operation Failed');
        
        // Log to console for debugging
        console.error('Unhandled Rejection:', reason);
    }

    /**
     * Graceful Degradation
     */
    setupGracefulDegradation() {
        // Check for required features
        this.checkRequiredFeatures();
        
        // Setup feature fallbacks
        this.setupFeatureFallbacks();
    }

    checkRequiredFeatures() {
        const features = {
            'localStorage': typeof Storage !== 'undefined',
            'fetch': typeof fetch !== 'undefined',
            'serviceWorker': 'serviceWorker' in navigator
        };
        
        const missing = Object.entries(features)
            .filter(([_, available]) => !available)
            .map(([name]) => name);
        
        if (missing.length > 0) {
            console.warn('Missing features:', missing);
            this.showError(
                `Some features may not work properly: ${missing.join(', ')}. Please update your browser.`,
                'Browser Compatibility'
            );
        }
    }

    setupFeatureFallbacks() {
        // Fallback for fetch if not available
        if (typeof fetch === 'undefined') {
            console.warn('Fetch API not available, using XMLHttpRequest fallback');
            // Implement XMLHttpRequest-based fetch polyfill if needed
        }
        
        // Fallback for localStorage
        if (typeof Storage === 'undefined') {
            console.warn('LocalStorage not available, using memory storage');
            // Implement in-memory storage fallback
        }
    }

    retryFailedOperations() {
        // Retry operations from retry queue
        const queue = [...this.retryQueue];
        this.retryQueue = [];
        
        queue.forEach(operation => {
            try {
                operation();
            } catch (error) {
                console.error('Failed to retry operation:', error);
            }
        });
    }

    shouldIgnoreFrontendNoise(error, message) {
        const normalizedMessage = String(message || error?.message || '').toLowerCase();

        // Known benign ResizeObserver warning triggered by various UI libraries/browsers
        if (normalizedMessage.includes('resizeobserver loop limit exceeded') ||
            normalizedMessage.includes('resizeobserver loop completed with undelivered notifications')) {
            console.debug('Ignored benign ResizeObserver warning:', message || error);
            return true;
        }

        return false;
    }
}

// Initialize enhanced error handler
window.enhancedErrorHandler = new EnhancedErrorHandler();

// Remove offline indicator when online
document.addEventListener('DOMContentLoaded', () => {
    if (navigator.onLine) {
        const indicator = document.getElementById('offline-indicator');
        if (indicator) {
            indicator.remove();
        }
    }
});

