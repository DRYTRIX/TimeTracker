/* TimeTracker service worker — cache static assets; never intercept /api/* (session + token auth). */
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
    // Real network error (not a fake 503) so callers / reconnect logic can recover.
    return Response.error();
  }
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

  // Never intercept API or health probes — let the browser surface genuine network
  // failures (stale keep-alive after tab idle) instead of synthesizing 503 Offline.
  // Covers /api/*, /api/v1/*, /api/health, and /_health.
  if (path.startsWith('/api/') || path === '/_health') {
    return;
  }

  if (path.startsWith('/static/')) {
    event.respondWith(cacheFirst(request));
    return;
  }

  if (request.mode === 'navigate' || request.destination === 'document') {
    event.respondWith(networkFirstDocument(request));
    return;
  }
});
