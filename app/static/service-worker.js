/**
 * Service Worker for TimeTracker PWA
 * Provides offline support and background sync
 */

const CACHE_VERSION = 'v1.0.1';
const CACHE_NAME = `timetracker-${CACHE_VERSION}`;

// Resources to cache immediately
const PRECACHE_URLS = [
    '/',
    '/static/dist/output.css',
    '/static/enhanced-ui.css',
    '/static/enhanced-ui.js',
    '/static/charts.js',
    '/static/interactions.js',
    '/static/images/drytrix-logo.svg',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css'
];

// Resources to cache on first use
const RUNTIME_CACHE_URLS = [
    '/main/dashboard',
    '/projects/',
    '/tasks/',
    '/timer/manual_entry'
];

// Install event - precache critical resources
self.addEventListener('install', event => {
    console.log('[ServiceWorker] Installing...');
    
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('[ServiceWorker] Precaching app shell');
                return cache.addAll(PRECACHE_URLS);
            })
            .then(() => self.skipWaiting())
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    console.log('[ServiceWorker] Activating...');
    
    event.waitUntil(
        caches.keys()
            .then(cacheNames => {
                return Promise.all(
                    cacheNames.map(cacheName => {
                        if (cacheName !== CACHE_NAME) {
                            console.log('[ServiceWorker] Deleting old cache:', cacheName);
                            return caches.delete(cacheName);
                        }
                    })
                );
            })
            .then(() => self.clients.claim())
    );
});

// Fetch event - serve from cache when offline
self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);
    
    // Skip cross-origin requests
    if (url.origin !== location.origin) {
        return;
    }
    
    // Skip caching for uploads directory (user-uploaded content that changes)
    if (url.pathname.startsWith('/uploads/')) {
        event.respondWith(fetch(request)); // Always fetch fresh
        return;
    }
    
    // API requests - network first, cache fallback
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(networkFirst(request));
        return;
    }
    
    // Static assets - cache first, network fallback
    if (request.destination === 'style' || 
        request.destination === 'script' || 
        request.destination === 'image' ||
        request.destination === 'font') {
        event.respondWith(cacheFirst(request));
        return;
    }
    
    // HTML pages - network first, cache fallback
    if (request.mode === 'navigate' || request.destination === 'document') {
        event.respondWith(networkFirst(request));
        return;
    }
    
    // Default: network first
    event.respondWith(networkFirst(request));
});

// Cache first strategy
async function cacheFirst(request) {
    const cache = await caches.open(CACHE_NAME);
    const cached = await cache.match(request);
    
    if (cached) {
        // Return cached and update in background
        updateCache(request);
        return cached;
    }
    
    try {
        const response = await fetch(request);
        if (response.ok) {
            cache.put(request, response.clone());
        }
        return response;
    } catch (error) {
        console.error('[ServiceWorker] Fetch failed:', error);
        return new Response('Offline', { status: 503, statusText: 'Service Unavailable' });
    }
}

// Network first strategy
async function networkFirst(request) {
    const cache = await caches.open(CACHE_NAME);
    
    try {
        const response = await fetch(request);
        
        if (response.ok) {
            // Cache successful responses
            cache.put(request, response.clone());
        }
        
        return response;
    } catch (error) {
        console.log('[ServiceWorker] Network failed, trying cache');
        const cached = await cache.match(request);
        
        if (cached) {
            return cached;
        }
        
        // Return offline page for navigation requests
        if (request.mode === 'navigate') {
            return createOfflinePage();
        }
        
        return new Response('Offline', { 
            status: 503, 
            statusText: 'Service Unavailable',
            headers: new Headers({ 'Content-Type': 'text/plain' })
        });
    }
}

// Update cache in background
async function updateCache(request) {
    const cache = await caches.open(CACHE_NAME);
    
    try {
        const response = await fetch(request);
        if (response.ok) {
            await cache.put(request, response);
        }
    } catch (error) {
        // Silently fail - we're updating in background
    }
}

// Create offline page response
function createOfflinePage() {
    const html = `
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Offline - TimeTracker</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    min-height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    text-align: center;
                    padding: 20px;
                }
                .container {
                    max-width: 500px;
                }
                .icon {
                    font-size: 80px;
                    margin-bottom: 20px;
                }
                h1 {
                    font-size: 32px;
                    margin: 0 0 10px 0;
                }
                p {
                    font-size: 18px;
                    opacity: 0.9;
                    margin: 0 0 30px 0;
                }
                button {
                    background: white;
                    color: #667eea;
                    border: none;
                    padding: 12px 30px;
                    border-radius: 25px;
                    font-size: 16px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: transform 0.2s;
                }
                button:hover {
                    transform: scale(1.05);
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="icon">📡</div>
                <h1>You're Offline</h1>
                <p>It looks like you've lost your internet connection. Don't worry, your data is safe!</p>
                <button onclick="window.location.reload()">Try Again</button>
            </div>
        </body>
        </html>
    `;
    
    return new Response(html, {
        headers: new Headers({
            'Content-Type': 'text/html; charset=utf-8'
        })
    });
}

// Background sync for offline actions
self.addEventListener('sync', event => {
    console.log('[ServiceWorker] Background sync:', event.tag);
    
    if (event.tag === 'sync-time-entries') {
        event.waitUntil(syncTimeEntries());
    }
});

// Sync time entries when back online
async function syncTimeEntries() {
    try {
        // Get pending entries from IndexedDB
        const db = await openDB();
        const entries = await getPendingEntries(db);
        
        if (entries.length === 0) {
            return;
        }
        
        console.log('[ServiceWorker] Syncing', entries.length, 'time entries');
        
        // Sync each entry
        for (const entry of entries) {
            try {
                const response = await fetch('/api/time-entries', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(entry.data)
                });
                
                if (response.ok) {
                    await markEntryAsSynced(db, entry.id);
                }
            } catch (error) {
                console.error('[ServiceWorker] Failed to sync entry:', error);
            }
        }
        
        // Notify all clients
        const clients = await self.clients.matchAll();
        clients.forEach(client => {
            client.postMessage({
                type: 'SYNC_COMPLETE',
                count: entries.length
            });
        });
        
    } catch (error) {
        console.error('[ServiceWorker] Background sync failed:', error);
        throw error;
    }
}

// IndexedDB helpers
function openDB() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('TimeTrackerDB', 1);
        
        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result);
        
        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            
            if (!db.objectStoreNames.contains('pendingEntries')) {
                const store = db.createObjectStore('pendingEntries', { 
                    keyPath: 'id', 
                    autoIncrement: true 
                });
                store.createIndex('timestamp', 'timestamp', { unique: false });
            }
        };
    });
}

function getPendingEntries(db) {
    return new Promise((resolve, reject) => {
        const transaction = db.transaction(['pendingEntries'], 'readonly');
        const store = transaction.objectStore('pendingEntries');
        const request = store.getAll();
        
        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result);
    });
}

function markEntryAsSynced(db, id) {
    return new Promise((resolve, reject) => {
        const transaction = db.transaction(['pendingEntries'], 'readwrite');
        const store = transaction.objectStore('pendingEntries');
        const request = store.delete(id);
        
        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve();
    });
}

// Push notifications
self.addEventListener('push', event => {
    console.log('[ServiceWorker] Push received');
    
    const data = event.data ? event.data.json() : {};
    const title = data.title || 'TimeTracker';
    const options = {
        body: data.body || 'You have a new notification',
        icon: '/static/images/drytrix-logo.svg',
        badge: '/static/images/drytrix-logo.svg',
        vibrate: [200, 100, 200],
        data: data,
        actions: data.actions || []
    };
    
    event.waitUntil(
        self.registration.showNotification(title, options)
    );
});

// Notification click
self.addEventListener('notificationclick', event => {
    console.log('[ServiceWorker] Notification clicked');
    
    event.notification.close();
    
    const urlToOpen = event.notification.data?.url || '/';
    
    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then(windowClients => {
                // Check if there's already a window open
                for (const client of windowClients) {
                    if (client.url === urlToOpen && 'focus' in client) {
                        return client.focus();
                    }
                }
                // Open new window
                if (clients.openWindow) {
                    return clients.openWindow(urlToOpen);
                }
            })
    );
});

// Message handling
self.addEventListener('message', event => {
    console.log('[ServiceWorker] Message received:', event.data);
    
    if (event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
    
    if (event.data.type === 'CACHE_URLS') {
        event.waitUntil(
            caches.open(CACHE_NAME)
                .then(cache => cache.addAll(event.data.urls))
        );
    }
    
    if (event.data.type === 'CLEAR_CACHE') {
        event.waitUntil(
            caches.keys()
                .then(cacheNames => Promise.all(
                    cacheNames.map(cacheName => caches.delete(cacheName))
                ))
        );
    }
});

console.log('[ServiceWorker] Script loaded');

