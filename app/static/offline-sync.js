/**
 * Offline Sync Manager for TimeTracker
 * Handles offline data storage, sync queue, and conflict resolution
 */

class OfflineSyncManager {
    constructor() {
        this.dbName = 'TimeTrackerDB';
        this.dbVersion = 2;
        this.db = null;
        this.syncInProgress = false;
        this.pendingSyncCount = 0;
        this.init();
    }

    async init() {
        try {
            this.db = await this.openDB();
            this.setupOnlineListener();
            this.setupServiceWorkerSync();
            await this.checkPendingSync();
            this.updateUI();
        } catch (error) {
            console.error('[OfflineSync] Initialization failed:', error);
        }
    }

    openDB() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.dbName, this.dbVersion);

            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve(request.result);

            request.onupgradeneeded = (event) => {
                const db = event.target.result;

                // Time entries store
                if (!db.objectStoreNames.contains('timeEntries')) {
                    const store = db.createObjectStore('timeEntries', {
                        keyPath: 'localId',
                        autoIncrement: true
                    });
                    store.createIndex('serverId', 'serverId', { unique: false });
                    store.createIndex('timestamp', 'timestamp', { unique: false });
                    store.createIndex('synced', 'synced', { unique: false });
                }

                // Tasks store
                if (!db.objectStoreNames.contains('tasks')) {
                    const store = db.createObjectStore('tasks', {
                        keyPath: 'localId',
                        autoIncrement: true
                    });
                    store.createIndex('serverId', 'serverId', { unique: false });
                    store.createIndex('synced', 'synced', { unique: false });
                }

                // Projects store
                if (!db.objectStoreNames.contains('projects')) {
                    const store = db.createObjectStore('projects', {
                        keyPath: 'localId',
                        autoIncrement: true
                    });
                    store.createIndex('serverId', 'serverId', { unique: false });
                    store.createIndex('synced', 'synced', { unique: false });
                }

                // Sync queue store
                if (!db.objectStoreNames.contains('syncQueue')) {
                    const store = db.createObjectStore('syncQueue', {
                        keyPath: 'id',
                        autoIncrement: true
                    });
                    store.createIndex('type', 'type', { unique: false });
                    store.createIndex('timestamp', 'timestamp', { unique: false });
                    store.createIndex('processed', 'processed', { unique: false });
                }
            };
        });
    }

    setupOnlineListener() {
        window.addEventListener('online', () => {
            console.log('[OfflineSync] Back online, starting sync...');
            this.syncAll();
        });

        window.addEventListener('offline', () => {
            console.log('[OfflineSync] Gone offline');
            this.updateUI();
        });
    }

    setupServiceWorkerSync() {
        if ('serviceWorker' in navigator && 'sync' in self.ServiceWorkerRegistration.prototype) {
            navigator.serviceWorker.ready.then(registration => {
                // Register background sync
                registration.sync.register('sync-time-entries').catch(err => {
                    console.log('[OfflineSync] Background sync not supported:', err);
                });
            });
        }
    }

    async checkPendingSync() {
        if (!this.db) return;

        try {
            const count = await this.getPendingSyncCount();
            this.pendingSyncCount = count;
            this.updateUI();

            if (count > 0 && navigator.onLine) {
                // Auto-sync if online
                this.syncAll();
            }
        } catch (error) {
            console.error('[OfflineSync] Error checking pending sync:', error);
        }
    }

    async getPendingSyncCount() {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['syncQueue'], 'readonly');
            const store = transaction.objectStore('syncQueue');
            const index = store.index('processed');
            const request = index.count(IDBKeyRange.only(false));

            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve(request.result || 0);
        });
    }

    // Time Entry Operations
    async saveTimeEntryOffline(entryData) {
        if (!this.db) {
            throw new Error('Database not initialized');
        }

        const entry = {
            ...entryData,
            localId: `local_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            serverId: null,
            synced: false,
            timestamp: new Date().toISOString(),
            conflict: false
        };

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['timeEntries', 'syncQueue'], 'readwrite');
            const entriesStore = transaction.objectStore('timeEntries');
            const queueStore = transaction.objectStore('syncQueue');

            const addRequest = entriesStore.add(entry);

            addRequest.onsuccess = () => {
                // Add to sync queue
                const queueItem = {
                    type: 'time_entry',
                    action: 'create',
                    localId: entry.localId,
                    data: entryData,
                    timestamp: new Date().toISOString(),
                    processed: false,
                    retries: 0
                };

                queueStore.add(queueItem).onsuccess = () => {
                    this.pendingSyncCount++;
                    this.updateUI();
                    resolve(entry);
                };
            };

            addRequest.onerror = () => reject(addRequest.error);
        });
    }

    async getOfflineTimeEntries() {
        if (!this.db) return [];

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['timeEntries'], 'readonly');
            const store = transaction.objectStore('timeEntries');
            const request = store.getAll();

            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve(request.result || []);
        });
    }

    // Sync Operations
    async syncAll() {
        if (!navigator.onLine || this.syncInProgress) {
            return;
        }

        this.syncInProgress = true;
        this.updateUI();

        try {
            await this.syncTimeEntries();
            await this.syncTasks();
            await this.syncProjects();
            await this.processSyncQueue();

            await this.checkPendingSync();
            console.log('[OfflineSync] Sync complete');
        } catch (error) {
            console.error('[OfflineSync] Sync error:', error);
        } finally {
            this.syncInProgress = false;
            this.updateUI();
        }
    }

    async syncTimeEntries() {
        if (!this.db) return;

        const unsyncedEntries = await this.getUnsyncedEntries('timeEntries');

        for (const entry of unsyncedEntries) {
            try {
                const response = await fetch('/api/v1/time-entries', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        project_id: entry.project_id,
                        task_id: entry.task_id,
                        start_time: entry.start_time,
                        end_time: entry.end_time,
                        notes: entry.notes,
                        tags: entry.tags,
                        billable: entry.billable
                    })
                });

                if (response.ok) {
                    const result = await response.json();
                    await this.markAsSynced('timeEntries', entry.localId, result.id);
                    this.pendingSyncCount--;
                } else {
                    console.error('[OfflineSync] Failed to sync entry:', response.statusText);
                }
            } catch (error) {
                console.error('[OfflineSync] Error syncing entry:', error);
            }
        }

        this.updateUI();
    }

    async syncTasks() {
        // Similar implementation for tasks
        // TODO: Implement task sync
    }

    async syncProjects() {
        // Similar implementation for projects
        // TODO: Implement project sync
    }

    async getUnsyncedEntries(storeName) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([storeName], 'readonly');
            const store = transaction.objectStore(storeName);
            const index = store.index('synced');
            const request = index.getAll(IDBKeyRange.only(false));

            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve(request.result || []);
        });
    }

    async markAsSynced(storeName, localId, serverId) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([storeName, 'syncQueue'], 'readwrite');
            const store = transaction.objectStore(storeName);
            const queueStore = transaction.objectStore('syncQueue');

            const getRequest = store.get(localId);
            getRequest.onsuccess = () => {
                const entry = getRequest.result;
                if (entry) {
                    entry.serverId = serverId;
                    entry.synced = true;
                    entry.syncedAt = new Date().toISOString();

                    const putRequest = store.put(entry);
                    putRequest.onsuccess = () => {
                        // Mark queue item as processed
                        const index = queueStore.index('type');
                        const queueRequest = index.openCursor(IDBKeyRange.only('time_entry'));
                        queueRequest.onsuccess = (event) => {
                            const cursor = event.target.result;
                            if (cursor) {
                                if (cursor.value.localId === localId) {
                                    cursor.value.processed = true;
                                    cursor.update(cursor.value);
                                }
                                cursor.continue();
                            }
                        };
                        resolve();
                    };
                    putRequest.onerror = () => reject(putRequest.error);
                } else {
                    resolve();
                }
            };
            getRequest.onerror = () => reject(getRequest.error);
        });
    }

    async processSyncQueue() {
        if (!this.db) return;

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['syncQueue'], 'readwrite');
            const store = transaction.objectStore('syncQueue');
            const index = store.index('processed');
            const request = index.openCursor(IDBKeyRange.only(false));

            request.onerror = () => reject(request.error);
            request.onsuccess = async (event) => {
                const cursor = event.target.result;
                if (cursor) {
                    const item = cursor.value;
                    // Process queue item based on type
                    // This will be handled by specific sync methods
                    cursor.continue();
                } else {
                    resolve();
                }
            };
        });
    }

    updateUI() {
        const isOnline = navigator.onLine;
        const hasPending = this.pendingSyncCount > 0;
        const isSyncing = this.syncInProgress;

        // Update offline indicator
        const indicator = document.getElementById('offline-indicator');
        if (indicator) {
            if (!isOnline) {
                indicator.classList.remove('hidden');
                indicator.textContent = 'You are offline. Changes will sync when you reconnect.';
            } else if (hasPending && !isSyncing) {
                indicator.classList.remove('hidden');
                indicator.textContent = `${this.pendingSyncCount} item(s) pending sync.`;
            } else if (isSyncing) {
                indicator.classList.remove('hidden');
                indicator.textContent = 'Syncing...';
            } else {
                indicator.classList.add('hidden');
            }
        }

        // Dispatch event for other components
        window.dispatchEvent(new CustomEvent('offlineSyncStatus', {
            detail: {
                online: isOnline,
                pendingCount: this.pendingSyncCount,
                syncing: isSyncing
            }
        }));
    }

    // Public API
    async createTimeEntryOffline(data) {
        if (navigator.onLine) {
            // Try online first
            try {
                const response = await fetch('/api/v1/time-entries', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                if (response.ok) {
                    return await response.json();
                }
            } catch (error) {
                console.log('[OfflineSync] Online create failed, saving offline:', error);
            }
        }

        // Save offline
        return await this.saveTimeEntryOffline(data);
    }

    async getPendingCount() {
        return this.pendingSyncCount;
    }

    async forceSync() {
        await this.syncAll();
    }
}

// Initialize singleton
window.offlineSyncManager = new OfflineSyncManager();

