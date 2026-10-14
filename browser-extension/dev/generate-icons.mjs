/**
 * Regenerates the toolbar icons (icons/idle-*.png and icons/running-*.png)
 * from the header glyph design: rounded square, blue→indigo gradient,
 * white timer glyph. The running variant carries a small red recording dot.
 *
 * Requires a Chromium/Brave instance with a CDP port (renders via the browser):
 *   brave.exe --remote-debugging-port=9333
 *   node dev/generate-icons.mjs 9333
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const port = process.argv[2] || '9333';
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(__dirname, '..', 'icons');

const SIZES = [128, 48, 32, 16];
const RUNNING_DOT = { size: 0.32, ring: 0.035 }; // fraction of tile size

function tileHtml(size, variant) {
  const glyph = Math.max(8, Math.round(size * 0.58));
  const radius = Math.max(3, Math.round(size * 0.225));
  const dotSize = Math.round(size * RUNNING_DOT.size);
  const ring = Math.max(1, Math.round(size * RUNNING_DOT.ring));
  const dot =
    variant === 'running'
      ? `<span style="position:absolute;right:${Math.round(size * 0.06)}px;` +
        `bottom:${Math.round(size * 0.06)}px;width:${dotSize}px;height:${dotSize}px;` +
        `border-radius:50%;background:#ff3b30;border:${ring}px solid #fff;"></span>`
      : '';
  return `<div class="tile" style="width:${size}px;height:${size}px;border-radius:${radius}px;">` +
    `<svg viewBox="0 0 24 24" style="width:${glyph}px;height:${glyph}px;" fill="none" ` +
    `stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">` +
    `<circle cx="12" cy="13" r="8"/><path d="M12 9v4l2.5 2.5M9 2h6"/></svg>${dot}</div>`;
}

const html = `<!DOCTYPE html><html><head><style>
  body { margin: 0; background: transparent; }
  .wrap { display: flex; flex-direction: column; gap: 10px; padding: 8px; }
  .tile {
    position: relative; display: grid; place-items: center;
    background: linear-gradient(135deg, #0a84ff, #5e5ce6);
    overflow: hidden;
  }
</style></head><body><div class="wrap" id="wrap"></div></body></html>`;

const browser = await chromium.connectOverCDP(`http://127.0.0.1:${port}`);
try {
  const ctx = browser.contexts()[0];
  const page = await ctx.newPage();

  for (const variant of ['idle', 'running']) {
    await page.setContent(html);
    await page.evaluate((cfg) => {
      document.getElementById('wrap').innerHTML = cfg.sizes
        .map((s) => `<div data-size="${s}">${'{{TILE}}'}</div>`)
        .join('');
    }, { sizes: SIZES });
    // tiles are built per-variant with exact markup
    for (const size of SIZES) {
      await page.evaluate(
        ({ size, variant, tileHtml }) => {
          const host = document.querySelector(`[data-size="${size}"]`);
          const template = document.createElement('div');
          template.innerHTML = tileHtml;
          host.replaceWith(template.firstElementChild);
        },
        { size, variant, tileHtml: tileHtml(size, variant) }
      );
    }
    await page.setViewportSize({ width: 220, height: 460 });
    for (const size of SIZES) {
      const tile = page.locator(`.tile[style*="width:${size}px"]`);
      const out = path.join(OUT, `${variant}-${size}.png`);
      await tile.screenshot({ path: out, omitBackground: true });
      const bytes = fs.statSync(out).size;
      console.log(`${variant}-${size}.png  ${bytes} bytes`);
    }
  }
  await page.close();
  console.log('done →', OUT);
} finally {
  await browser.close();
}
