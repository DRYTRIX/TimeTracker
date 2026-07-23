import { test, expect } from '@playwright/test';
import { AUTHENTICATED_PAGES, PUBLIC_PAGES, collectPageProblems, login } from './helpers.mjs';

/**
 * The strict, nonce-based Content-Security-Policy ships as Report-Only until a real
 * browser confirms it would not break anything. These tests are the gate: once they
 * pass consistently, the Report-Only policy in app/__init__.py becomes the enforced
 * one and 'unsafe-inline' is dropped from script-src.
 */
test.describe('Content Security Policy', () => {
  test('enforced policy allowlists no third-party origin', async ({ page }) => {
    const response = await page.goto('/login');
    const csp = response.headers()['content-security-policy'] || '';

    expect(csp, 'CSP header must be present').not.toBe('');
    for (const host of [
      'cdnjs.cloudflare.com',
      'cdn.jsdelivr.net',
      'uicdn.toast.com',
      'fonts.bunny.net',
      'fonts.googleapis.com',
      'code.jquery.com',
      'esm.sh',
    ]) {
      expect(csp, `CSP must not allowlist ${host}`).not.toContain(host);
    }
  });

  test('a strict nonce-based report-only policy is emitted', async ({ page }) => {
    const response = await page.goto('/login');
    const reportOnly = response.headers()['content-security-policy-report-only'] || '';

    expect(reportOnly).toContain("script-src 'self' 'nonce-");
    expect(reportOnly, 'report-only policy must not fall back to unsafe-inline').not.toContain(
      "script-src 'self' 'unsafe-inline'"
    );
  });

  for (const { name, path } of PUBLIC_PAGES) {
    test(`no CSP violations on ${name}`, async ({ page }) => {
      const problems = collectPageProblems(page);
      await page.goto(path, { waitUntil: 'networkidle' });
      expect(problems.csp, `CSP violations on ${path}`).toEqual([]);
    });
  }

  for (const { name, path } of AUTHENTICATED_PAGES) {
    test(`no CSP violations on ${name}`, async ({ page }) => {
      test.skip(!(await login(page)), 'E2E_USERNAME not configured');

      const problems = collectPageProblems(page);
      await page.goto(path, { waitUntil: 'networkidle' });
      expect(problems.csp, `CSP violations on ${path}`).toEqual([]);
    });
  }
});
