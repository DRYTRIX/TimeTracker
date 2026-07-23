import { test, expect } from '@playwright/test';
import { collectPageProblems, login } from './helpers.mjs';

/**
 * Page-weight budget and bundle integrity.
 *
 * base.html used to load 32 separate JS files totalling ~550 KB uncompressed. They are
 * now minified and concatenated into ordered bundles. This locks in the improvement so
 * a future change cannot quietly reintroduce the old cost, and confirms the bundles
 * actually execute (several source files declare globals that later files consume, so
 * a bad grouping fails at runtime, not at build time).
 */

/** Generous enough to avoid flakiness, tight enough to catch a regression. */
const MAX_JS_BYTES = 420_000;
const MAX_JS_REQUESTS = 16;

test('dashboard stays within its JavaScript budget', async ({ page }) => {
  test.skip(!(await login(page)), 'E2E_USERNAME not configured');

  let bytes = 0;
  let requests = 0;

  page.on('response', async (response) => {
    const url = response.url();
    if (!/\.js(\?|$)/.test(url)) return;
    requests += 1;
    try {
      bytes += (await response.body()).length;
    } catch {
      /* body already discarded; ignore */
    }
  });

  await page.goto('/', { waitUntil: 'networkidle' });

  expect(requests, `too many JS requests (${requests})`).toBeLessThanOrEqual(MAX_JS_REQUESTS);
  expect(bytes, `JS payload grew to ${bytes} bytes`).toBeLessThanOrEqual(MAX_JS_BYTES);
});

test('bundles execute and expose their globals', async ({ page }) => {
  test.skip(!(await login(page)), 'E2E_USERNAME not configured');

  const problems = collectPageProblems(page);
  await page.goto('/', { waitUntil: 'networkidle' });

  // One representative global per bundle group, to catch a mis-ordered concatenation.
  const globals = await page.evaluate(() => ({
    toast: typeof window.showToast,
    typing: typeof window.TimeTracker?.isTyping,
    shortcuts: typeof window.shortcutManager,
  }));

  expect(globals.toast, 'toast-notifications.js (core-a1) did not run').toBe('function');
  expect(globals.typing, 'typing-utils.js (core-d) did not run').toBe('function');
  expect(globals.shortcuts, 'keyboard-shortcuts-advanced.js (core-e) did not run').toBe('object');
  expect(problems.errors, 'JS errors on dashboard').toEqual([]);
});

test('assets are served with content-hashed, cacheable URLs', async ({ page }) => {
  test.skip(!(await login(page)), 'E2E_USERNAME not configured');

  await page.goto('/', { waitUntil: 'networkidle' });

  const bundles = await page.evaluate(() =>
    Array.from(document.querySelectorAll('script[src]'))
      .map((s) => s.getAttribute('src'))
      .filter((src) => src.includes('/static/dist/'))
  );

  expect(bundles.length, 'no hashed bundles on the page').toBeGreaterThan(0);
  for (const src of bundles) {
    expect(src, `${src} is not content-hashed`).toMatch(/\.[0-9a-f]{12}\.min\.js$/);
  }
});
