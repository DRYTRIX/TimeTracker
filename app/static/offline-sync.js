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
            try {
                const transaction = this.db.transaction(['syncQueue'], 'readonly');
                const store = transaction.objectStore('syncQueue');
                
                // Check if the index exists
                if (!store.indexNames.contains('processed')) {
                    // If index doesn't exist, count manually
                    const request = store.openCursor();
                    let count = 0;
                    request.onsuccess = (event) => {
                        const cursor = event.target.result;
                        if (cursor) {
                            if (cursor.value.processed === false || !cursor.value.processed) {
                                count++;
                            }
                            cursor.continue();
                        } else {
                            resolve(count);
                        }
                    };
                    request.onerror = () => reject(request.error);
                    return;
                }
                
                const index = store.index('processed');
                // IndexedDB doesn't support boolean values in IDBKeyRange, so we use a cursor approach
                // Iterate through all items and filter for processed === false
                const request = index.openCursor();
                let count = 0;
                
                request.onsuccess = (event) => {
                    const cursor = event.target.result;
                    if (cursor) {
                        // Check if the value is false (unprocessed)
                        if (cursor.value.processed === false || cursor.value.processed === 0 || !cursor.value.processed) {
                            count++;
                        }
                        cursor.continue();
                    } else {
                        resolve(count);
                    }
                };
                
                request.onerror = () => {
                    // Fallback: count manually if index query fails
                    const fallbackRequest = store.openCursor();
                    let fallbackCount = 0;
                    fallbackRequest.onsuccess = (event) => {
                        const cursor = event.target.result;
                        if (cursor) {
                            if (cursor.value.processed === false || !cursor.value.processed) {
                                fallbackCount++;
                            }
                            cursor.continue();
                        } else {
                            resolve(fallbackCount);
                        }
                    };
                    fallbackRequest.onerror = () => reject(fallbackRequest.error);
                };
            } catch (error) {
                // If there's any error, return 0 instead of rejecting
                console.warn('[OfflineSync] Error counting pending sync, returning 0:', error);
                resolve(0);
            }
        });
    }

    // Helper function to format dates to ISO 8601
    formatDateToISO(dateValue) {
        if (!dateValue) return null;
        
        // If it's already a string in ISO format, return as is
        if (typeof dateValue === 'string') {
            // Check if it's already in ISO format
            if (dateValue.match(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/)) {
                return dateValue;
            }
            // Try to parse and reformat
            try {
                const date = new Date(dateValue);
                if (!isNaN(date.getTime())) {
                    return date.toISOString();
                }
            } catch (e) {
                console.error('[OfflineSync] Error parsing date string:', dateValue, e);
            }
            return dateValue;
        }
        
        // If it's a Date object, convert to ISO string
        if (dateValue instanceof Date) {
            if (isNaN(dateValue.getTime())) {
                console.error('[OfflineSync] Invalid Date object:', dateValue);
                return null;
            }
            return dateValue.toISOString();
        }
        
        // Fallback: try to create a Date object
        try {
            const date = new Date(dateValue);
            if (!isNaN(date.getTime())) {
                return date.toISOString();
            }
        } catch (e) {
            console.error('[OfflineSync] Error formatting date:', dateValue, e);
        }
        
        return null;
    }

    // Time Entry Operations
    async saveTimeEntryOffline(entryData) {
        if (!this.db) {
            throw new Error('Database not initialized');
        }

        // Normalize dates to ISO format for consistent storage
        const normalizedData = {
            ...entryData,
            start_time: this.formatDateToISO(entryData.start_time),
            end_time: entryData.end_time ? this.formatDateToISO(entryData.end_time) : null
        };

        const entry = {
            ...normalizedData,
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
                    data: normalizedData,
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
                // Format dates to ISO 8601
                const startTimeISO = this.formatDateToISO(entry.start_time);
                const endTimeISO = this.formatDateToISO(entry.end_time);
                
                if (!startTimeISO) {
                    console.error('[OfflineSync] Invalid start_time format:', entry.start_time);
                    continue;
                }

                const response = await fetch('/api/v1/time-entries', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        project_id: entry.project_id,
                        task_id: entry.task_id,
                        start_time: startTimeISO,
                        end_time: endTimeISO,
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
                    const errorText = await response.text();
                    console.error('[OfflineSync] Failed to sync entry:', response.status, response.statusText, errorText);
                }
            } catch (error) {
                console.error('[OfflineSync] Error syncing entry:', error);
            }
        }

        this.updateUI();
    }

    async syncTasks() {
        if (!this.db) return;

        const unsyncedTasks = await this.getUnsyncedEntries('tasks');

        for (const task of unsyncedTasks) {
            try {
                const taskData = {
                    name: task.name,
                    project_id: task.project_id,
                    description: task.description,
                    status: task.status,
                    priority: task.priority,
                    assigned_to: task.assigned_to,
                    due_date: task.due_date ? this.formatDateToISO(task.due_date) : null,
                    estimated_hours: task.estimated_hours,
                    notes: task.notes
                };

                let response;
                if (task.serverId) {
                    // Update existing task
                    response = await fetch(`/api/v1/tasks/${task.serverId}`, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(taskData)
                    });
                } else {
                    // Create new task
                    response = await fetch('/api/v1/tasks', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(taskData)
                    });
                }

                if (response.ok) {
                    const result = await response.json();
                    const taskId = result.task?.id || result.id;
                    if (taskId) {
                        await this.markAsSynced('tasks', task.localId, taskId);
                        this.pendingSyncCount--;
                    }
                } else {
                    const errorText = await response.text();
                    console.error('[OfflineSync] Failed to sync task:', response.status, response.statusText, errorText);
                }
            } catch (error) {
                console.error('[OfflineSync] Error syncing task:', error);
            }
        }

        this.updateUI();
    }

    async syncProjects() {
        if (!this.db) return;

        const unsyncedProjects = await this.getUnsyncedEntries('projects');

        for (const project of unsyncedProjects) {
            try {
                const projectData = {
                    name: project.name,
                    description: project.description,
                    client_id: project.client_id,
                    status: project.status || 'active',
                    billable: project.billable !== false,
                    hourly_rate: project.hourly_rate,
                    code: project.code,
                    budget_amount: project.budget_amount,
                    budget_threshold_percent: project.budget_threshold_percent,
                    billing_ref: project.billing_ref
                };

                let response;
                if (project.serverId) {
                    // Update existing project
                    response = await fetch(`/api/v1/projects/${project.serverId}`, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(projectData)
                    });
                } else {
                    // Create new project
                    response = await fetch('/api/v1/projects', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(projectData)
                    });
                }

                if (response.ok) {
                    const result = await response.json();
                    const projectId = result.project?.id || result.id;
                    if (projectId) {
                        await this.markAsSynced('projects', project.localId, projectId);
                        this.pendingSyncCount--;
                    }
                } else {
                    const errorText = await response.text();
                    console.error('[OfflineSync] Failed to sync project:', response.status, response.statusText, errorText);
                }
            } catch (error) {
                console.error('[OfflineSync] Error syncing project:', error);
            }
        }

        this.updateUI();
    }

    async getUnsyncedEntries(storeName) {
        return new Promise((resolve, reject) => {
            try {
                const transaction = this.db.transaction([storeName], 'readonly');
                const store = transaction.objectStore(storeName);
                
                // Check if the index exists
                if (!store.indexNames.contains('synced')) {
                    // If index doesn't exist, filter manually
                    const request = store.getAll();
                    request.onsuccess = () => {
                        const all = request.result || [];
                        const unsynced = all.filter(entry => entry.synced === false || !entry.synced);
                        resolve(unsynced);
                    };
                    request.onerror = () => reject(request.error);
                    return;
                }
                
                const index = store.index('synced');
                // IndexedDB doesn't support boolean values in IDBKeyRange, so we use a cursor approach
                // Iterate through all items and filter for synced === false
                const request = index.openCursor();
                const results = [];
                
                request.onsuccess = (event) => {
                    const cursor = event.target.result;
                    if (cursor) {
                        // Check if the value is false (unsynced)
                        if (cursor.value.synced === false || cursor.value.synced === 0 || !cursor.value.synced) {
                            results.push(cursor.value);
                        }
                        cursor.continue();
                    } else {
                        resolve(results);
                    }
                };
                
                request.onerror = () => {
                    // Fallback: filter manually if index query fails
                    const fallbackRequest = store.getAll();
                    fallbackRequest.onsuccess = () => {
                        const all = fallbackRequest.result || [];
                        const unsynced = all.filter(entry => entry.synced === false || !entry.synced);
                        resolve(unsynced);
                    };
                    fallbackRequest.onerror = () => reject(fallbackRequest.error);
                };
            } catch (error) {
                console.warn('[OfflineSync] Error getting unsynced entries, returning empty array:', error);
                resolve([]);
            }
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
                        // Determine queue type based on store name
                        let queueType = 'time_entry';
                        if (storeName === 'tasks') {
                            queueType = 'task';
                        } else if (storeName === 'projects') {
                            queueType = 'project';
                        }
                        
                        const queueRequest = index.openCursor(IDBKeyRange.only(queueType));
                        queueRequest.onsuccess = (event) => {
                            const cursor = event.target.result;
                            if (cursor) {
                                if (cursor.value.localId === localId) {
                                    cursor.value.processed = true;
                                    cursor.update(cursor.value);
                                }
                                cursor.continue();
                            } else {
                                resolve();
                            }
                        };
                        queueRequest.onerror = () => resolve(); // Resolve even if queue update fails
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
            try {
                const transaction = this.db.transaction(['syncQueue'], 'readwrite');
                const store = transaction.objectStore('syncQueue');
                
                // Check if the index exists
                if (!store.indexNames.contains('processed')) {
                    // If index doesn't exist, iterate manually
                    const request = store.openCursor();
                    request.onsuccess = async (event) => {
                        const cursor = event.target.result;
                        if (cursor) {
                            const item = cursor.value;
                            // Process queue item based on type
                            // This will be handled by specific sync methods
                            if (item.processed === false || !item.processed) {
                                // Process unprocessed items
                            }
                            cursor.continue();
                        } else {
                            resolve();
                        }
                    };
                    request.onerror = () => reject(request.error);
                    return;
                }
                
                const index = store.index('processed');
                // IndexedDB doesn't support boolean values in IDBKeyRange, so we use a cursor approach
                const request = index.openCursor();

                request.onerror = () => {
                    // Fallback: iterate manually if index query fails
                    const fallbackRequest = store.openCursor();
                    fallbackRequest.onsuccess = async (event) => {
                        const cursor = event.target.result;
                        if (cursor) {
                            const item = cursor.value;
                            if (item.processed === false || !item.processed) {
                                // Process queue item based on type
                                // This will be handled by specific sync methods
                            }
                            cursor.continue();
                        } else {
                            resolve();
                        }
                    };
                    fallbackRequest.onerror = () => reject(fallbackRequest.error);
                };
                
                request.onsuccess = async (event) => {
                    const cursor = event.target.result;
                    if (cursor) {
                        const item = cursor.value;
                        // Check if the item is unprocessed
                        if (item.processed === false || item.processed === 0 || !item.processed) {
                            // Process queue item based on type
                            // This will be handled by specific sync methods
                        }
                        cursor.continue();
                    } else {
                        resolve();
                    }
                };
            } catch (error) {
                console.warn('[OfflineSync] Error processing sync queue:', error);
                resolve(); // Resolve instead of reject to prevent blocking
            }
        });
    }

    updateUI() {
        const isOnline = navigator.onLine;
        const hasPending = this.pendingSyncCount > 0;
        const isSyncing = this.syncInProgress;

        // Update offline indicator
        const indicator = document.getElementById('offline-indicator');
        const indicatorText = document.getElementById('offline-indicator-text');
        const indicatorIcon = document.getElementById('offline-indicator-icon');
        const syncButton = document.getElementById('offline-sync-button');
        
        if (indicator) {
            if (!isOnline) {
                indicator.classList.remove('hidden');
                indicator.className = indicator.className.replace(/bg-\w+-\d+ dark:bg-\w+-\d+/, 'bg-yellow-500 dark:bg-yellow-600');
                if (indicatorText) indicatorText.textContent = 'You are offline. Changes will sync when you reconnect.';
                if (indicatorIcon) indicatorIcon.className = 'fas fa-wifi-slash';
                if (syncButton) syncButton.style.display = 'none';
            } else if (hasPending && !isSyncing) {
                indicator.classList.remove('hidden');
                indicator.className = indicator.className.replace(/bg-\w+-\d+ dark:bg-\w+-\d+/, 'bg-blue-500 dark:bg-blue-600');
                if (indicatorText) indicatorText.textContent = `${this.pendingSyncCount} item(s) pending sync.`;
                if (indicatorIcon) indicatorIcon.className = 'fas fa-clock';
                if (syncButton) syncButton.style.display = 'inline-block';
            } else if (isSyncing) {
                indicator.classList.remove('hidden');
                indicator.className = indicator.className.replace(/bg-\w+-\d+ dark:bg-\w+-\d+/, 'bg-blue-500 dark:bg-blue-600');
                if (indicatorText) indicatorText.textContent = 'Syncing...';
                if (indicatorIcon) indicatorIcon.className = 'fas fa-sync-alt fa-spin';
                if (syncButton) syncButton.style.display = 'none';
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

    // Task Operations
    async saveTaskOffline(taskData) {
        if (!this.db) {
            throw new Error('Database not initialized');
        }

        const normalizedData = {
            ...taskData,
            due_date: taskData.due_date ? this.formatDateToISO(taskData.due_date) : null
        };

        const task = {
            ...normalizedData,
            localId: `local_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            serverId: null,
            synced: false,
            timestamp: new Date().toISOString(),
            conflict: false
        };

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['tasks', 'syncQueue'], 'readwrite');
            const tasksStore = transaction.objectStore('tasks');
            const queueStore = transaction.objectStore('syncQueue');

            const addRequest = tasksStore.add(task);

            addRequest.onsuccess = () => {
                const queueItem = {
                    type: 'task',
                    action: task.serverId ? 'update' : 'create',
                    localId: task.localId,
                    data: normalizedData,
                    timestamp: new Date().toISOString(),
                    processed: false,
                    retries: 0
                };

                queueStore.add(queueItem).onsuccess = () => {
                    this.pendingSyncCount++;
                    this.updateUI();
                    resolve(task);
                };
            };

            addRequest.onerror = () => reject(addRequest.error);
        });
    }

    async getOfflineTasks() {
        if (!this.db) return [];

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['tasks'], 'readonly');
            const store = transaction.objectStore('tasks');
            const request = store.getAll();

            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve(request.result || []);
        });
    }

    // Project Operations
    async saveProjectOffline(projectData) {
        if (!this.db) {
            throw new Error('Database not initialized');
        }

        const project = {
            ...projectData,
            localId: `local_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            serverId: null,
            synced: false,
            timestamp: new Date().toISOString(),
            conflict: false
        };

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['projects', 'syncQueue'], 'readwrite');
            const projectsStore = transaction.objectStore('projects');
            const queueStore = transaction.objectStore('syncQueue');

            const addRequest = projectsStore.add(project);

            addRequest.onsuccess = () => {
                const queueItem = {
                    type: 'project',
                    action: project.serverId ? 'update' : 'create',
                    localId: project.localId,
                    data: projectData,
                    timestamp: new Date().toISOString(),
                    processed: false,
                    retries: 0
                };

                queueStore.add(queueItem).onsuccess = () => {
                    this.pendingSyncCount++;
                    this.updateUI();
                    resolve(project);
                };
            };

            addRequest.onerror = () => reject(addRequest.error);
        });
    }

    async getOfflineProjects() {
        if (!this.db) return [];

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['projects'], 'readonly');
            const store = transaction.objectStore('projects');
            const request = store.getAll();

            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve(request.result || []);
        });
    }

    // Public API
    async createTimeEntryOffline(data) {
        // Normalize dates to ISO format
        const normalizedData = {
            ...data,
            start_time: this.formatDateToISO(data.start_time),
            end_time: data.end_time ? this.formatDateToISO(data.end_time) : null
        };

        if (navigator.onLine) {
            // Try online first
            try {
                const response = await fetch('/api/v1/time-entries', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(normalizedData)
                });

                if (response.ok) {
                    return await response.json();
                } else {
                    const errorText = await response.text();
                    console.error('[OfflineSync] Online create failed:', response.status, response.statusText, errorText);
                }
            } catch (error) {
                console.log('[OfflineSync] Online create failed, saving offline:', error);
            }
        }

        // Save offline
        return await this.saveTimeEntryOffline(normalizedData);
    }

    async createTaskOffline(data) {
        if (navigator.onLine) {
            // Try online first
            try {
                const response = await fetch('/api/v1/tasks', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                if (response.ok) {
                    return await response.json();
                } else {
                    const errorText = await response.text();
                    console.error('[OfflineSync] Online task create failed:', response.status, response.statusText, errorText);
                }
            } catch (error) {
                console.log('[OfflineSync] Online task create failed, saving offline:', error);
            }
        }

        // Save offline
        return await this.saveTaskOffline(data);
    }

    async createProjectOffline(data) {
        if (navigator.onLine) {
            // Try online first
            try {
                const response = await fetch('/api/v1/projects', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                if (response.ok) {
                    return await response.json();
                } else {
                    const errorText = await response.text();
                    console.error('[OfflineSync] Online project create failed:', response.status, response.statusText, errorText);
                }
            } catch (error) {
                console.log('[OfflineSync] Online project create failed, saving offline:', error);
            }
        }

        // Save offline
        return await this.saveProjectOffline(data);
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

