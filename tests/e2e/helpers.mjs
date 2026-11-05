import { expect } from '@playwright/test';

export const USERNAME = process.env.E2E_USERNAME || '';
export const PASSWORD = process.env.E2E_PASSWORD || '';

/** Screens worth checking on every run, in rough order of traffic. */
export const PUBLIC_PAGES = [{ name: 'login', path: '/login' }];

export const AUTHENTICATED_PAGES = [
  { name: 'dashboard', path: '/' },
  { name: 'time entries', path: '/timer/time-entries' },
  { name: 'projects', path: '/projects/' },
  { name: 'reports', path: '/reports/' },
  { name: 'invoices', path: '/invoices/' },
];

/**
 * Collect CSP violations and page errors for the lifetime of a page.
 *
 * Returns an object whose arrays fill in as the page runs; read them after navigation.
 */
export function collectPageProblems(page) {
  const problems = { csp: [], errors: [], failedRequests: [] };

  page.on('console', (msg) => {
    const text = msg.text();
    if (/Content Security Policy|Refused to (load|execute|apply)/i.test(text)) {
      problems.csp.push(text);
    } else if (msg.type() === 'error') {
      // Network/console noise (missing optional assets, socket.io without Redis).
      if (/socket\.io|WebSocket connection|Failed to load resource:/i.test(text)) return;
      problems.errors.push(text);
    }
  });

  page.on('pageerror', (err) => {
    const text = String(err);
    if (/socket\.io|WebSocket/i.test(text)) return;
    problems.errors.push(text);
  });

  page.on('requestfailed', (req) => {
    // about:/data: and intentionally aborted requests are not interesting.
    if (!/^https?:/.test(req.url())) return;
    if (/\/socket\.io\//i.test(req.url())) return;
    const failure = req.failure()?.errorText || '';
    // Same-origin ERR_ABORTED is usually navigation cancellation, not a missing CDN.
    try {
      const reqHost = new URL(req.url()).host;
      const pageHost = page.url() && page.url() !== 'about:blank' ? new URL(page.url()).host : null;
      if (pageHost && reqHost === pageHost && /ERR_ABORTED|NS_BINDING_ABORTED|blockedbyclient/i.test(failure)) {
        return;
      }
    } catch (_) {
      /* ignore URL parse issues */
    }
    problems.failedRequests.push(`${req.url()} (${failure})`);
  });

  return problems;
}

/** Log in through the real form. Returns false when no credentials are configured. */
export async function login(page) {
  if (!USERNAME) return false;

  await page.goto('/login', { waitUntil: 'load' });
  await page.fill('input[name="username"]', USERNAME);
  const passwordField = page.locator('input[name="password"]');
  if (await passwordField.count()) {
    await passwordField.fill(PASSWORD);
  }
  // Prefer explicit URL assertion over networkidle: authenticated pages keep polling open.
  await page.click('button[type="submit"], input[type="submit"]');
  await expect(page).not.toHaveURL(/\/login/, { timeout: 20_000 });
  return true;
}
