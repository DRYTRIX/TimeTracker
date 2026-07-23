import { test, expect } from '@playwright/test';
import { AUTHENTICATED_PAGES, collectPageProblems, login } from './helpers.mjs';

/**
 * The self-hosting guarantee, verified the only way that really counts: block every
 * external host at the network layer and confirm the app still works.
 *
 * Before the assets were vendored, 17 resources came from cdnjs, jsDelivr,
 * uicdn.toast.com and fonts.bunny.net, so an air-gapped install rendered without
 * icons, fonts, date pickers, charts or the command palette.
 */
test.describe('Offline / air-gapped rendering', () => {
  test.beforeEach(async ({ context, baseURL }) => {
    const allowedHost = new URL(baseURL).host;
    await context.route('**/*', (route) => {
      const url = new URL(route.request().url());
      if (url.host === allowedHost || url.protocol === 'data:' || url.protocol === 'blob:') {
        return route.continue();
      }
      // Anything else would be a third-party dependency: fail it loudly.
      return route.abort('blockedbyclient');
    });
  });

  test('login page renders with all external hosts blocked', async ({ page }) => {
    const problems = collectPageProblems(page);
    await page.goto('/login', { waitUntil: 'networkidle' });

    await expect(page.locator('input[name="username"]')).toBeVisible();
    expect(problems.failedRequests, 'no request may go to a third-party host').toEqual([]);
  });

  test('stylesheets and fonts resolve locally', async ({ page }) => {
    await page.goto('/login', { waitUntil: 'networkidle' });

    const fontFamily = await page.evaluate(() => getComputedStyle(document.body).fontFamily);
    expect(fontFamily).toMatch(/Inter/i);

    const remote = await page.evaluate(() =>
      Array.from(document.querySelectorAll('link[rel="stylesheet"], script[src]'))
        .map((el) => el.href || el.src)
        .filter((url) => url && !url.startsWith(window.location.origin))
    );
    expect(remote, 'every asset must be same-origin').toEqual([]);
  });

  for (const { name, path } of AUTHENTICATED_PAGES) {
    test(`${name} renders offline without script errors`, async ({ page }) => {
      test.skip(!(await login(page)), 'E2E_USERNAME not configured');

      const problems = collectPageProblems(page);
      await page.goto(path, { waitUntil: 'networkidle' });

      expect(problems.failedRequests, `third-party requests on ${path}`).toEqual([]);
      expect(problems.errors, `JS errors on ${path}`).toEqual([]);
    });
  }

  test('command palette works without network access', async ({ page }) => {
    test.skip(!(await login(page)), 'E2E_USERNAME not configured');

    await page.goto('/', { waitUntil: 'networkidle' });
    // Previously imported its scoring helper from jsDelivr at runtime, so this
    // silently did nothing when offline.
    await page.keyboard.press('Control+k');
    await expect(page.locator('#ttCommandPalette, #commandPaletteModal')).toBeVisible();
  });
});
