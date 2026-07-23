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
      problems.errors.push(text);
    }
  });

  page.on('pageerror', (err) => problems.errors.push(String(err)));

  page.on('requestfailed', (req) => {
    // about:/data: and intentionally aborted requests are not interesting.
    if (/^https?:/.test(req.url())) {
      problems.failedRequests.push(`${req.url()} (${req.failure()?.errorText})`);
    }
  });

  return problems;
}

/** Log in through the real form. Returns false when no credentials are configured. */
export async function login(page) {
  if (!USERNAME) return false;

  await page.goto('/login');
  await page.fill('input[name="username"]', USERNAME);
  const passwordField = page.locator('input[name="password"]');
  if (await passwordField.count()) {
    await passwordField.fill(PASSWORD);
  }
  await Promise.all([
    page.waitForLoadState('networkidle'),
    page.click('button[type="submit"], input[type="submit"]'),
  ]);

  await expect(page).not.toHaveURL(/\/login/);
  return true;
}
