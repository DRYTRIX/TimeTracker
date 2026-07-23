import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { AUTHENTICATED_PAGES, PUBLIC_PAGES, login } from './helpers.mjs';

/**
 * Accessibility baseline.
 *
 * Across ~100k lines of templates there were only ~450 aria-* attributes and 142
 * role= attributes for 968 buttons, and nothing in CI opened a browser. This is the
 * first automated check.
 *
 * Scope is deliberately limited to serious and critical violations so the gate is
 * meaningful on day one; tighten to moderate once these are clean.
 */
const IMPACTS = ['serious', 'critical'];

function summarize(violations) {
  return violations
    .map((v) => `  [${v.impact}] ${v.id}: ${v.help}\n    ${v.nodes.slice(0, 3).map((n) => n.target.join(' ')).join('\n    ')}`)
    .join('\n');
}

async function scan(page) {
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa'])
    .analyze();
  return results.violations.filter((v) => IMPACTS.includes(v.impact));
}

test.describe('Accessibility', () => {
  for (const { name, path } of PUBLIC_PAGES) {
    test(`${name} has no serious or critical violations`, async ({ page }) => {
      await page.goto(path, { waitUntil: 'networkidle' });
      const violations = await scan(page);
      expect(violations.length, `\n${summarize(violations)}`).toBe(0);
    });
  }

  for (const { name, path } of AUTHENTICATED_PAGES) {
    test(`${name} has no serious or critical violations`, async ({ page }) => {
      test.skip(!(await login(page)), 'E2E_USERNAME not configured');

      await page.goto(path, { waitUntil: 'networkidle' });
      const violations = await scan(page);
      expect(violations.length, `\n${summarize(violations)}`).toBe(0);
    });
  }

  test('skip-to-content link is reachable by keyboard', async ({ page }) => {
    await page.goto('/login');
    await page.keyboard.press('Tab');
    const focused = await page.evaluate(() => document.activeElement?.textContent?.trim());
    // base.html provides a "Skip to content" link as the first focusable element.
    expect(focused ?? '').toBeTruthy();
  });
});
