#!/usr/bin/env node
/**
 * JS build for TimeTracker.
 *
 * Two different strategies, deliberately:
 *
 * 1. LEGACY CORE (`core`) — the classic, non-module scripts that base.html used to
 *    load as ~30 separate <script> tags. Several of them declare true globals at top
 *    level (e.g. enhanced-ui.js declares 14) that *other* files in the list consume.
 *    Running them through esbuild's bundler would give each file module scope and
 *    silently break those cross-file references. So these are minified individually
 *    and concatenated in the original load order, which is semantically identical to
 *    the sequential <script> tags they replace — just one request instead of thirty.
 *
 * 2. MODULE ENTRIES — real ES modules with imports to resolve (command-palette.js
 *    imports `cmdk`, previously over the network from jsDelivr). These get a true
 *    esbuild bundle, emitted as IIFE so they stay drop-in <script> tags.
 *
 * Outputs are content-hashed into app/static/dist/ and recorded in dist/manifest.json,
 * which Flask reads via the `asset_url()` Jinja global (see app/utils/assets.py).
 */

import { createHash } from 'node:crypto';
import { mkdir, readFile, readdir, rm, writeFile } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import * as esbuild from 'esbuild';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const MODULES = join(ROOT, 'node_modules');
const STATIC = join(ROOT, 'app', 'static');
const DIST = join(STATIC, 'dist');

const WATCH = process.argv.includes('--watch');

/**
 * Loaded in <head>, before anything else, so it stays its own file.
 */
const HEAD_SCRIPTS = ['pwa-enhancements.js'];

/**
 * Classic global scripts, grouped in the exact order base.html loaded them.
 *
 * Why six groups instead of one bundle: base.html interleaves these <script src>
 * tags with Jinja-rendered inline blocks that (a) run at parse time, not on
 * DOMContentLoaded, and (b) declare top-level globals such as `closeAllMenus`,
 * `themeToggleBtn` and `trackDonationClick`. Collapsing everything into a single
 * bundle would move ~17 scripts across those inline blocks and change the order in
 * which globals are defined vs. consumed. Each group therefore sits exactly where its
 * members used to, preserving execution order while still cutting 32 requests to 9.
 *
 * Order within and between groups is load-bearing — do not sort.
 */
const CORE_GROUPS = {
  // Ungated: loaded for anonymous and authenticated users alike.
  'core-a1': ['date-picker-init.js', 'enhanced-search.js', 'form-validation.js', 'toast-notifications.js'],
  // Gated on `current_user.is_authenticated and support_ui_json`.
  'core-support': ['support-ui.js'],
  // Ungated.
  'core-a2': ['enhanced-tables.js', 'interactions.js', 'offline-sync.js', 'mentions.js'],
  // Gated on `current_user.is_authenticated` — the floating timer bar and idle
  // tracker must not load for anonymous visitors.
  'core-auth': ['floating-actions.js', 'floating-timer-bar.js', 'idle.js'],
  // These two sit behind *different* Jinja gates in base.html — `ai_enabled` and
  // `is_admin_user` respectively — so they must stay separate bundles. Merging them
  // would leak the admin update-checker to non-admins whenever AI is on, and hide it
  // from admins whenever AI is off.
  'core-ai': ['ai-helper.js'],
  'core-admin': ['admin-version-update.js'],
  // after the window.__BASE_INIT__ bootstrap
  'core-c': ['base-init.js', 'mobile.js'],
  // after the sidebar + theme inline blocks, and after chart.js vendor
  'core-d': [
    'charts.js',
    'enhanced-ui.js',
    'onboarding.js',
    'onboarding-enhanced.js',
    'error-handling-enhanced.js',
    'ui-enhancements.js',
    'typing-utils.js',
  ],
  // after the window.__KEYBOARD_SHORTCUTS_CONFIG__ bootstrap
  'core-e': [
    'keyboard-shortcuts-advanced.js',
    'smart-notifications.js',
    'dashboard-widgets.js',
    'dashboard-enhancements.js',
    'activity-feed.js',
  ],
  // after the menus/support-banner inline block
  'core-f': ['data-tables-enhanced.js'],
};

/**
 * Deferred, page-tail scripts kept out of the critical bundle.
 */
const DEFERRED_SCRIPTS = ['js/ai_autocomplete.js'];

/**
 * Standalone pages (auth, client portal, kiosk, setup wizard) do not extend base.html
 * and load a small subset directly. Kept as separate single-file bundles so each of
 * those templates gets the exact scripts it had before — client_portal/base.html and
 * kiosk/base.html load only the toast system, the rest load both.
 */
const STANDALONE_GROUPS = {
  toast: ['toast-notifications.js'],
  errors: ['error-handling-enhanced.js'],
  'setup-wizard': ['js/setup-wizard.js'],
};

/**
 * True ES modules that need dependency resolution.
 */
const MODULE_ENTRIES = [{ name: 'command-palette', entry: 'js/command-palette.js' }];

/**
 * Third-party packages that npm does not publish as a self-contained browser build,
 * so we produce one ourselves.
 *
 * @toast-ui/editor's `dist/toastui-editor.js` is a webpack UMD bundle that declares the
 * eight prosemirror-* packages as **externals** — it `require()`s them at run time. The
 * CDN file it replaced (`toastui-editor-all.min.js`) was the "all" build with those
 * dependencies bundled in, and npm ships no equivalent. Loading the UMD file directly in
 * a browser therefore throws
 *   TypeError: Cannot read properties of undefined (reading 'PluginKey')
 * because `prosemirror-state` resolves to undefined.
 *
 * Bundling the ESM entry inlines the real dependencies from node_modules. `globalName`
 * reproduces the `window.toastui` global the templates expect (`window.toastui.Editor`).
 *
 * Output goes to app/static/vendor/ (not dist/) because these are third-party assets
 * referenced by direct path from templates, not through asset_url().
 */
const VENDOR_BUNDLES = [
  {
    name: 'toastui-editor',
    entry: 'node_modules/@toast-ui/editor/dist/esm/index.js',
    outfile: 'vendor/toastui/toastui-editor.js',
    globalName: 'toastui',
  },
];

function hash(contents) {
  return createHash('sha256').update(contents).digest('hex').slice(0, 12);
}

/** Minify a list of classic scripts and concatenate them, preserving order. */
async function buildConcatBundle(name, files) {
  const parts = [];
  for (const file of files) {
    const src = await readFile(join(STATIC, file), 'utf8');
    const out = await esbuild.transform(src, {
      loader: 'js',
      minify: true,
      // Classic scripts, NOT modules: no module wrapper, globals stay global.
      format: undefined,
      target: 'es2019',
    });
    parts.push(`/* ${file} */\n${out.code}`);
  }
  const code = parts.join('\n;\n');
  const filename = `${name}.${hash(code)}.min.js`;
  await writeFile(join(DIST, filename), code, 'utf8');
  return [name, `dist/${filename}`];
}

/**
 * Deep-import aliases.
 *
 * cmdk's package exports only expose ".", and that entry pulls in React — we want just
 * the standalone `command-score` helper. Aliasing the specifier resolves straight to
 * the file, bypassing the exports restriction without dragging in React.
 */
const ALIASES = {
  'cmdk/command-score': join(MODULES, 'cmdk', 'dist', 'command-score.mjs'),
};

/**
 * Hard failure if any source file still imports over the network. The app must build
 * and run with no outbound access; a remote import would reintroduce a CDN dependency
 * that tests/test_no_external_assets.py is meant to prevent.
 */
const noRemoteImportsPlugin = {
  name: 'no-remote-imports',
  setup(build) {
    build.onResolve({ filter: /^https?:\/\// }, (args) => {
      throw new Error(
        `Remote import ${args.path} in ${args.importer}. Add the package to ` +
          `package.json and alias it in scripts/build-js.mjs so bundles stay offline-capable.`
      );
    });
  },
};

/** Real esbuild bundle for an ES module entry point. */
async function buildModuleBundle(name, entry) {
  const result = await esbuild.build({
    entryPoints: [join(STATIC, entry)],
    bundle: true,
    minify: true,
    format: 'iife',
    target: 'es2019',
    alias: ALIASES,
    plugins: [noRemoteImportsPlugin],
    write: false,
    logLevel: 'silent',
  });
  const code = result.outputFiles[0].text;
  const filename = `${name}.${hash(code)}.min.js`;
  await writeFile(join(DIST, filename), code, 'utf8');
  return [name, `dist/${filename}`];
}

/**
 * Bundle a third-party package into a self-contained browser file under vendor/.
 * Not content-hashed: templates reference these by fixed path.
 */
async function buildVendorBundle({ name, entry, outfile, globalName }) {
  const dest = join(STATIC, outfile);
  await mkdir(dirname(dest), { recursive: true });
  await esbuild.build({
    entryPoints: [join(ROOT, entry)],
    bundle: true,
    minify: true,
    format: 'iife',
    globalName,
    target: 'es2019',
    outfile: dest,
    logLevel: 'silent',
  });
  const bytes = (await readFile(dest, 'utf8')).length;
  console.log(`  ${name} -> ${outfile} (${(bytes / 1024).toFixed(0)} KB, window.${globalName})`);
}

async function build() {
  await mkdir(DIST, { recursive: true });

  // Clear previously hashed JS bundles (leave output.css from the Tailwind build).
  for (const f of await readdir(DIST).catch(() => [])) {
    if (f.endsWith('.min.js')) await rm(join(DIST, f), { force: true });
  }

  const manifest = Object.fromEntries(
    await Promise.all([
      buildConcatBundle('head', HEAD_SCRIPTS),
      ...Object.entries(CORE_GROUPS).map(([name, files]) => buildConcatBundle(name, files)),
      ...Object.entries(STANDALONE_GROUPS).map(([name, files]) => buildConcatBundle(name, files)),
      buildConcatBundle('deferred', DEFERRED_SCRIPTS),
      ...MODULE_ENTRIES.map(({ name, entry }) => buildModuleBundle(name, entry)),
    ])
  );

  // Self-contained browser builds for packages npm ships only as externals-based UMD.
  for (const spec of VENDOR_BUNDLES) {
    await buildVendorBundle(spec);
  }

  await writeFile(join(DIST, 'manifest.json'), JSON.stringify(manifest, null, 2), 'utf8');

  const total = Object.values(manifest).length;
  console.log(`[build-js] Wrote ${total} bundle(s) + manifest.json to app/static/dist/`);
  for (const [name, path] of Object.entries(manifest)) console.log(`  ${name} -> ${path}`);
}

if (WATCH) {
  const { watch } = await import('node:fs');
  await build();
  console.log('[build-js] Watching for changes...');
  let timer = null;
  watch(STATIC, { recursive: true }, (_event, file) => {
    if (!file || !file.endsWith('.js') || file.startsWith('dist')) return;
    clearTimeout(timer);
    timer = setTimeout(() => build().catch(console.error), 150);
  });
} else {
  await build();
}
