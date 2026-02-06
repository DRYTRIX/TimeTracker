/**
 * PWA Enhancements - Offline support and push notifications
 */

class PWAEnhancements {
    constructor() {
        this.serviceWorkerRegistration = null;
        this.pushSubscription = null;
        this.isOnline = navigator.onLine;
        this.init();
    }

    async init() {
        // Register service worker
        if ('serviceWorker' in navigator) {
            await this.registerServiceWorker();
        }

        // Setup offline detection
        this.setupOfflineDetection();

        // Setup install prompt
        this.setupInstallPrompt();

        // Setup push notifications
        if ('PushManager' in window) {
            await this.setupPushNotifications();
        }

        // Setup IndexedDB for offline storage
        await this.setupIndexedDB();
    }

    async registerServiceWorker() {
        try {
            const registration = await navigator.serviceWorker.register('/static/service-worker.js');
            this.serviceWorkerRegistration = registration;
            
            // Listen for updates
            registration.addEventListener('updatefound', () => {
                const newWorker = registration.installing;
                newWorker.addEventListener('statechange', () => {
                    if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                        // New service worker available
                        this.showUpdateNotification();
                    }
                });
            });

            // Check for updates periodically
            setInterval(() => {
                registration.update();
            }, 60000); // Check every minute

        } catch (error) {
            console.error('Service Worker registration failed:', error);
        }
    }

    setupOfflineDetection() {
        // Listen for online/offline events
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.onOnline();
        });

        window.addEventListener('offline', () => {
            this.isOnline = false;
            this.onOffline();
        });

        // Show initial status
        if (!this.isOnline) {
            this.onOffline();
        }
    }

    onOnline() {
        // Hide offline indicator
        this.hideOfflineIndicator();
        
        // Show online notification
        this.showNotification('You\'re back online!', 'Your data will sync automatically.');
        
        // Trigger background sync
        if (this.serviceWorkerRegistration && 'sync' in self.registration) {
            this.serviceWorkerRegistration.sync.register('sync-time-entries');
        }

        // Sync pending data
        this.syncPendingData();
    }

    onOffline() {
        // Show offline indicator
        this.showOfflineIndicator();
        
        // Store current page state
        this.storePageState();
    }

    showOfflineIndicator() {
        let indicator = document.getElementById('offline-indicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'offline-indicator';
            indicator.className = 'fixed top-0 left-0 right-0 bg-yellow-500 text-white text-center py-2 z-50';
            indicator.innerHTML = '<i class="fas fa-wifi-slash mr-2"></i>You are offline. Some features may be limited.';
            document.body.insertBefore(indicator, document.body.firstChild);
        }
        indicator.style.display = 'block';
    }

    hideOfflineIndicator() {
        const indicator = document.getElementById('offline-indicator');
        if (indicator) {
            indicator.style.display = 'none';
        }
    }

    setupInstallPrompt() {
        let deferredPrompt;
        
        window.addEventListener('beforeinstallprompt', (e) => {
            // Prevent the mini-infobar from appearing
            e.preventDefault();
            deferredPrompt = e;
            
            // Show custom install button
            this.showInstallButton(deferredPrompt);
        });

        // Listen for app installed
        window.addEventListener('appinstalled', () => {
            this.hideInstallButton();
            deferredPrompt = null;
        });
    }

    showInstallButton(deferredPrompt) {
        // Check if button already exists
        if (document.getElementById('pwa-install-button')) {
            return;
        }

        const button = document.createElement('button');
        button.id = 'pwa-install-button';
        button.className = 'fixed bottom-4 right-4 bg-primary text-white px-4 py-2 rounded-lg shadow-lg hover:bg-primary/90 z-50';
        button.innerHTML = '<i class="fas fa-download mr-2"></i>Install App';
        
        button.addEventListener('click', async () => {
            deferredPrompt.prompt();
            const { outcome } = await deferredPrompt.userChoice;
            this.hideInstallButton();
            deferredPrompt = null;
        });

        document.body.appendChild(button);
    }

    hideInstallButton() {
        const button = document.getElementById('pwa-install-button');
        if (button) {
            button.remove();
        }
    }

    async setupPushNotifications() {
        try {
            // Only check permission status, don't request automatically
            // Permission should only be requested from user interactions (button clicks)
            if ('Notification' in window && Notification.permission === 'granted') {
                // Subscribe to push notifications if permission already granted
                if (this.serviceWorkerRegistration && this.serviceWorkerRegistration.pushManager) {
                    const vapidKey = this.getVapidPublicKey();
                    
                    // Only subscribe if VAPID key is available and valid
                    if (!vapidKey || vapidKey.trim() === '') {
                        return;
                    }
                    
                    try {
                        const applicationServerKey = this.urlBase64ToUint8Array(vapidKey);
                        const subscription = await this.serviceWorkerRegistration.pushManager.subscribe({
                            userVisibleOnly: true,
                            applicationServerKey: applicationServerKey
                        });

                        this.pushSubscription = subscription;
                        
                        // Send subscription to server
                        await this.sendSubscriptionToServer(subscription);
                    } catch (keyError) {
                        // If key conversion fails, log but don't throw
                        console.warn('Push notifications: Invalid VAPID key format, skipping subscription:', keyError);
                    }
                }
            }
        } catch (error) {
            // Only log as warning if it's a key-related error, otherwise error
            if (error.name === 'InvalidAccessError' && error.message.includes('applicationServerKey')) {
                console.warn('Push notifications: VAPID key configuration issue, skipping subscription');
            } else {
                console.error('Push notification setup failed:', error);
            }
        }
    }

    /**
     * Request notification permission (should be called from user interaction)
     */
    async requestNotificationPermission() {
        if ('Notification' in window && Notification.permission === 'default') {
            try {
                const permission = await Notification.requestPermission();
                
                if (permission === 'granted') {
                    // Subscribe to push notifications
                    if (this.serviceWorkerRegistration && this.serviceWorkerRegistration.pushManager) {
                        const vapidKey = this.getVapidPublicKey();
                        
                        // Only subscribe if VAPID key is available and valid
                        if (!vapidKey || vapidKey.trim() === '') {
                            console.warn('Push notifications: VAPID public key not configured, cannot subscribe');
                            return permission;
                        }
                        
                        try {
                            const applicationServerKey = this.urlBase64ToUint8Array(vapidKey);
                            const subscription = await this.serviceWorkerRegistration.pushManager.subscribe({
                                userVisibleOnly: true,
                                applicationServerKey: applicationServerKey
                            });

                            this.pushSubscription = subscription;
                            
                            // Send subscription to server
                            await this.sendSubscriptionToServer(subscription);
                        } catch (keyError) {
                            console.warn('Push notifications: Invalid VAPID key format:', keyError);
                        }
                    }
                }
                return permission;
            } catch (error) {
                console.error('Error requesting notification permission:', error);
                return 'denied';
            }
        }
        return Notification.permission;
    }

    urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding)
            .replace(/\-/g, '+')
            .replace(/_/g, '/');

        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);

        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    }

    getVapidPublicKey() {
        // This should come from server config
        return document.querySelector('meta[name="vapid-public-key"]')?.content || '';
    }

    async sendSubscriptionToServer(subscription) {
        try {
            const response = await fetch('/api/push/subscribe', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(subscription)
            });

            if (!response.ok) {
                throw new Error('Failed to send subscription to server');
            }
        } catch (error) {
            console.error('Failed to send subscription:', error);
        }
    }

    async setupIndexedDB() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open('TimeTrackerPWA', 2);

            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve(request.result);

            request.onupgradeneeded = (event) => {
                const db = event.target.result;

                // Time entries store
                if (!db.objectStoreNames.contains('timeEntries')) {
                    const store = db.createObjectStore('timeEntries', { keyPath: 'id', autoIncrement: true });
                    store.createIndex('timestamp', 'timestamp', { unique: false });
                    store.createIndex('synced', 'synced', { unique: false });
                }

                // Projects store
                if (!db.objectStoreNames.contains('projects')) {
                    db.createObjectStore('projects', { keyPath: 'id' });
                }

                // Tasks store
                if (!db.objectStoreNames.contains('tasks')) {
                    db.createObjectStore('tasks', { keyPath: 'id' });
                }

                // Pending actions store
                if (!db.objectStoreNames.contains('pendingActions')) {
                    const store = db.createObjectStore('pendingActions', { keyPath: 'id', autoIncrement: true });
                    store.createIndex('type', 'type', { unique: false });
                    store.createIndex('timestamp', 'timestamp', { unique: false });
                }
            };
        });
    }

    async storeTimeEntryOffline(entryData) {
        const db = await this.getDB();
        const transaction = db.transaction(['timeEntries'], 'readwrite');
        const store = transaction.objectStore('timeEntries');

        const entry = {
            ...entryData,
            timestamp: Date.now(),
            synced: false
        };

        return store.add(entry);
    }

    async getDB() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open('TimeTrackerPWA', 2);
            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve(request.result);
        });
    }

    async syncPendingData() {
        const db = await this.getDB();
        const transaction = db.transaction(['timeEntries'], 'readonly');
        const store = transaction.objectStore('timeEntries');
        const index = store.index('synced');
        const request = index.getAll(false);

        request.onsuccess = async () => {
            const entries = request.result;
            for (const entry of entries) {
                try {
                    await this.syncTimeEntry(entry);
                } catch (error) {
                    console.error('Failed to sync entry:', error);
                }
            }
        };
    }

    async syncTimeEntry(entry) {
        const response = await fetch('/api/time-entries', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(entry)
        });

        if (response.ok) {
            // Mark as synced
            const db = await this.getDB();
            const transaction = db.transaction(['timeEntries'], 'readwrite');
            const store = transaction.objectStore('timeEntries');
            entry.synced = true;
            await store.put(entry);
        }
    }

    storePageState() {
        // Store current page state for offline access
        const state = {
            url: window.location.href,
            title: document.title,
            timestamp: Date.now()
        };

        localStorage.setItem('lastPageState', JSON.stringify(state));
    }

    showUpdateNotification() {
        // Show notification that update is available
        const notification = document.createElement('div');
        notification.className = 'fixed bottom-4 left-4 bg-blue-600 text-white px-4 py-3 rounded-lg shadow-lg z-50 max-w-sm';
        notification.innerHTML = `
            <div class="flex items-center justify-between">
                <div>
                    <p class="font-semibold">Update Available</p>
                    <p class="text-sm">A new version is available. Refresh to update.</p>
                </div>
                <button onclick="window.location.reload()" class="ml-4 bg-white text-blue-600 px-3 py-1 rounded hover:bg-gray-100">
                    Update
                </button>
            </div>
        `;
        document.body.appendChild(notification);

        // Auto-remove after 10 seconds
        setTimeout(() => {
            notification.remove();
        }, 10000);
    }

    showNotification(title, body) {
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification(title, {
                body: body,
                icon: '/static/images/timetracker-logo.svg',
                badge: '/static/images/timetracker-logo.svg'
            });
        }
    }
}

// Initialize on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.pwaEnhancements = new PWAEnhancements();
    });
} else {
    window.pwaEnhancements = new PWAEnhancements();
}

