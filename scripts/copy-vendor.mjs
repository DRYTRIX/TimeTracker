#!/usr/bin/env node
/**
 * Copy third-party browser libraries from node_modules into app/static/vendor/.
 *
 * TimeTracker is self-hosted and privacy-focused: the app must render fully with
 * no outbound network access. Every library that used to be pulled from a CDN
 * (cdnjs / jsDelivr / uicdn.toast.com) is vendored here instead.
 *
 * Run via `npm run copy:vendor` (also invoked by `npm run build:assets`).
 * The Dockerfile frontend stage runs this and copies app/static/vendor/ into the image.
 */

import { cp, mkdir, readFile, rm, stat, writeFile } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const MODULES = join(ROOT, 'node_modules');
const VENDOR = join(ROOT, 'app', 'static', 'vendor');

/**
 * Each entry copies `from` (relative to node_modules) to `to` (relative to
 * app/static/vendor). Directories are copied recursively.
 */
const ASSETS = [
  // Font Awesome: CSS build only. The SVG-with-JS build was previously loaded
  // *in addition* to this one, which conflicted and doubled the payload.
  ['@fortawesome/fontawesome-free/css/all.min.css', 'fontawesome/css/all.min.css'],
  ['@fortawesome/fontawesome-free/webfonts', 'fontawesome/webfonts'],

  ['chart.js/dist/chart.umd.js', 'chartjs/chart.umd.js'],

  ['flatpickr/dist/flatpickr.min.css', 'flatpickr/flatpickr.min.css'],
  ['flatpickr/dist/flatpickr.min.js', 'flatpickr/flatpickr.min.js'],
  ['flatpickr/dist/themes/dark.css', 'flatpickr/themes/dark.css'],

  ['socket.io-client/dist/socket.io.min.js', 'socketio/socket.io.min.js'],

  // Only the stylesheets. The editor JS is NOT copied from npm: that file is a webpack
  // UMD bundle with the prosemirror-* packages as externals, so it throws
  // "Cannot read properties of undefined (reading 'PluginKey')" in a browser. A truly
  // self-contained build is produced from the ESM entry by scripts/build-js.mjs
  // (VENDOR_BUNDLES) and written to the same path.
  ['@toast-ui/editor/dist/toastui-editor.css', 'toastui/toastui-editor.css'],
  ['@toast-ui/editor/dist/theme/toastui-editor-dark.css', 'toastui/theme/toastui-editor-dark.css'],

  ['@simonwep/pickr/dist/pickr.min.js', 'pickr/pickr.min.js'],
  ['@simonwep/pickr/dist/themes/classic.min.css', 'pickr/themes/classic.min.css'],

  ['konva/konva.min.js', 'konva/konva.min.js'],

  ['sortablejs/Sortable.min.js', 'sortablejs/Sortable.min.js'],

  ['fullcalendar/index.global.min.js', 'fullcalendar/index.global.min.js'],

  ['frappe-gantt/dist/frappe-gantt.min.js', 'frappe-gantt/frappe-gantt.min.js'],
  ['frappe-gantt/dist/frappe-gantt.css', 'frappe-gantt/frappe-gantt.css'],

  ['animejs/lib/anime.min.js', 'animejs/anime.min.js'],

  // Inter was previously @import-ed from fonts.bunny.net inside input.css, which meant
  // every page load reached out to a third party. @font-face rules in input.css now
  // point at these local files instead.
  //
  // Only the weights and subset actually declared in input.css are copied — the
  // package ships 126 files (2.2 MB) across every subset and weight, of which we use
  // eight. Adding a weight or subset here means adding a matching @font-face rule.
  ...[400, 500, 600, 700].flatMap((weight) =>
    ['woff2', 'woff'].map((ext) => [
      `@fontsource/inter/files/inter-latin-${weight}-normal.${ext}`,
      `inter/files/inter-latin-${weight}-normal.${ext}`,
    ])
  ),
];

/*
 * Files are copied verbatim — never re-minified.
 *
 * Some packages publish unminified builds where the CDN served minified ones, and an
 * earlier version of this script ran those through esbuild to compensate. Re-minifying
 * somebody else's build output trades correctness for bytes that transport compression
 * recovers anyway, so it is no longer done: serve what the package ships and let nginx
 * gzip it (see the gzip block in nginx/*.conf).
 *
 * chart.js was verified to work either way. @toast-ui/editor's failure had a different
 * cause entirely — see the note on its entry above and VENDOR_BUNDLES in build-js.mjs.
 */

async function exists(path) {
  try {
    await stat(path);
    return true;
  } catch {
    return false;
  }
}

/**
 * Paths under vendor/ that scripts/build-js.mjs generates (see VENDOR_BUNDLES).
 * They live in directories this script clears, so they are preserved across the wipe;
 * otherwise a bare `npm run copy:vendor` would silently delete the Toast UI editor
 * bundle and leave the app with a missing script.
 */
const BUILD_GENERATED = ['toastui/toastui-editor.js'];

async function main() {
  // Only clear the directories this script owns. A blanket rm -rf on app/static/vendor
  // would also delete anything vendored by hand — app/static/vendor/grapesjs/ is
  // checked into git and is not managed here.
  const preserved = new Map();
  for (const rel of BUILD_GENERATED) {
    const p = join(VENDOR, rel);
    if (await exists(p)) preserved.set(rel, await readFile(p));
  }

  const managed = new Set(ASSETS.map(([, to]) => to.split('/')[0]));
  for (const dir of managed) {
    await rm(join(VENDOR, dir), { recursive: true, force: true });
  }
  await mkdir(VENDOR, { recursive: true });

  for (const [rel, buf] of preserved) {
    const dest = join(VENDOR, rel);
    await mkdir(dirname(dest), { recursive: true });
    await writeFile(dest, buf);
  }

  const missing = [];
  let copied = 0;

  for (const [from, to] of ASSETS) {
    const src = join(MODULES, from);
    const dest = join(VENDOR, to);

    if (!(await exists(src))) {
      missing.push(from);
      continue;
    }

    await mkdir(dirname(dest), { recursive: true });
    await cp(src, dest, { recursive: true });
    copied += 1;
  }

  if (missing.length) {
    console.error('[copy-vendor] Missing sources (did `npm install` run?):');
    for (const m of missing) console.error(`  - ${m}`);
    process.exit(1);
  }

  console.log(`[copy-vendor] Vendored ${copied} asset(s) into app/static/vendor/`);
}

main().catch((err) => {
  console.error('[copy-vendor] Failed:', err);
  process.exit(1);
});
