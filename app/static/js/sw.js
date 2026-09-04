/* TimeTracker service worker — cache static assets; do not touch /api/v1/* (token auth). */
const CACHE_NAME = 'timetracker-v1';

const PRECACHE_URLS = [
  '/offline',
  '/static/manifest.json',
  '/static/dist/output.css',
  '/static/enhanced-ui.css',
  '/static/enhanced-ui.js',
  '/static/charts.js',
  '/static/interactions.js',
  '/static/images/timetracker-logo.svg',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(CACHE_NAME);
      try {
        await cache.addAll(PRECACHE_URLS);
      } catch (e) {
        console.warn('[SW] precache partial failure', e);
      }
      self.skipWaiting();
    })()
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(
        keys.map((k) => {
          if (k !== CACHE_NAME) return caches.delete(k);
          return undefined;
        })
      );
      await self.clients.claim();
    })()
  );
});

function isSameOrigin(url) {
  return url.origin === self.location.origin;
}

async function cacheFirst(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);
  if (cached) return cached;
  try {
    const response = await fetch(request);
    if (response.ok && request.method === 'GET') {
      const clone = response.clone();
      try {
        await cache.put(request, clone);
      } catch (_) {}
    }
    return response;
  } catch (e) {
    return offlineJsonResponse();
  }
}

// Synthetic offline response must be JSON — callers parse .json() and a plain-text
// body would throw SyntaxError on top of the connectivity failure.
function offlineJsonResponse() {
  return new Response(JSON.stringify({ error: 'Offline' }), {
    status: 503,
    statusText: 'Service Unavailable',
    headers: { 'Content-Type': 'application/json' }
  });
}

async function networkFirstDocument(request) {
  try {
    return await fetch(request);
  } catch (_) {
    const fallback = await caches.match('/offline');
    if (fallback) return fallback;
    return new Response(
      '<!DOCTYPE html><html><head><meta charset="utf-8"><title>Offline</title></head><body><p>You are offline.</p></body></html>',
      { status: 503, headers: { 'Content-Type': 'text/html; charset=utf-8' } }
    );
  }
}

async function networkFirstApi(request) {
  try {
    return await fetch(request);
  } catch (_) {
    return offlineJsonResponse();
  }
}

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') {
    return;
  }
  let url;
  try {
    url = new URL(request.url);
  } catch (_) {
    return;
  }
  if (!isSameOrigin(url)) {
    return;
  }

  const path = url.pathname;

  // Never intercept token-auth API — browser handles the request unchanged.
  if (path.startsWith('/api/v1/')) {
    return;
  }

  // Health probes must hit the network directly (no synthetic 503 on transient fail).
  if (path === '/api/health' || path === '/_health') {
    return;
  }

  if (path.startsWith('/static/')) {
    event.respondWith(cacheFirst(request));
    return;
  }

  if (path.startsWith('/api/')) {
    event.respondWith(networkFirstApi(request));
    return;
  }

  if (request.mode === 'navigate' || request.destination === 'document') {
    event.respondWith(networkFirstDocument(request));
    return;
  }
});

// ---------------------------------------------------------------------------
// Web Push (idle "Still working?" alerts + smart reminders)
// ---------------------------------------------------------------------------
self.addEventListener('push', (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch (e) {
    data = { title: 'TimeTracker', message: event.data ? event.data.text() : '' };
  }
  const isIdle = data.kind === 'idle_timeout' || data.kind === 'idle_needs_review';
  const title = data.title || 'TimeTracker';
  const options = {
    body: data.message || '',
    tag: 'tt-' + (data.kind || 'note'),
    requireInteraction: isIdle,
    renotify: true,
    data: { url: (data.action && data.action.url) || '/', kind: data.kind || 'note' },
  };
  if (isIdle) {
    options.actions = [
      { action: 'still-working', title: 'I\'m still working' },
      { action: 'stop-timer', title: 'Stop timer' },
    ];
  }
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const info = event.notification.data || {};
  const base = info.url || '/';

  const resolveReview = (action) =>
    fetch('/api/timer/review', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ action }),
    }).catch(() => {});

  if (info.kind === 'idle_timeout' || info.kind === 'idle_needs_review') {
    if (event.action === 'still-working') {
      event.waitUntil(resolveReview('continue'));
      return;
    }
    if (event.action === 'stop-timer') {
      event.waitUntil(resolveReview('keep'));
      return;
    }
  }

  event.waitUntil(
    (async () => {
      const clientList = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
      for (const client of clientList) {
        try {
          const cUrl = new URL(client.url);
          if (cUrl.origin === self.location.origin && 'focus' in client) {
            await client.focus();
            if ('navigate' in client) {
              try { await client.navigate(base); } catch (e) {}
            }
            return;
          }
        } catch (e) {}
      }
      await self.clients.openWindow(base);
    })()
  );
});
