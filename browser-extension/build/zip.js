/**
 * Package the extension into dist/timetracker-extension-vX.Y.Z[.firefox].zip
 * for Chrome Web Store / Firefox AMO / sideload distribution.
 *
 * Usage (from browser-extension/):
 *   npm run zip
 *   npm run zip:firefox
 *   node build/zip.js --target firefox
 *
 * Pure Node — no npm dependencies.
 */

import { existsSync, mkdirSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { dirname, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..');
const DIST = join(ROOT, 'dist');

const INCLUDE = [
  'manifest.json',
  'background.js',
  'popup.html',
  'popup.js',
  'popup.css',
  'options.html',
  'options.js',
  'lib/api.js',
  'lib/picker.js',
  'lib/url_suggest.js',
  'lib/browser.js',
  'icons',
];

const SKIP_NAMES = new Set(['.DS_Store', 'Thumbs.db']);

function collectFiles(entry, base = ROOT, out = []) {
  const abs = join(base, entry);
  if (!existsSync(abs)) {
    throw new Error(`Missing required path: ${entry}`);
  }
  const st = statSync(abs);
  if (st.isDirectory()) {
    for (const name of readdirSync(abs).sort()) {
      if (SKIP_NAMES.has(name) || name.startsWith('.')) continue;
      collectFiles(name, abs, out);
    }
    return out;
  }
  out.push({ abs, rel: relative(ROOT, abs).split('\\').join('/') });
  return out;
}

function readManifestVersion() {
  const manifest = JSON.parse(readFileSync(join(ROOT, 'manifest.json'), 'utf8'));
  return manifest.version || '0.0.0';
}

function deepMerge(base, overlay) {
  if (Array.isArray(overlay)) return overlay.slice();
  if (overlay && typeof overlay === 'object') {
    const out = { ...(base && typeof base === 'object' && !Array.isArray(base) ? base : {}) };
    for (const [k, v] of Object.entries(overlay)) {
      out[k] = deepMerge(out[k], v);
    }
    return out;
  }
  return overlay;
}

function buildManifestForTarget(target) {
  const chromeManifest = JSON.parse(readFileSync(join(ROOT, 'manifest.json'), 'utf8'));
  if (target !== 'firefox') return chromeManifest;
  const overlay = JSON.parse(readFileSync(join(ROOT, 'build/manifest.firefox.json'), 'utf8'));
  const merged = deepMerge(chromeManifest, overlay);
  // Firefox MV3 uses background.scripts; drop Chromium-only service_worker key if both present.
  if (merged.background?.scripts) {
    delete merged.background.service_worker;
  }
  return merged;
}

function crc32(buf) {
  let c = ~0;
  for (let i = 0; i < buf.length; i++) {
    c ^= buf[i];
    for (let k = 0; k < 8; k++) c = c & 1 ? (c >>> 1) ^ 0xedb88320 : c >>> 1;
  }
  return ~c >>> 0;
}

function u16(n) {
  const b = Buffer.alloc(2);
  b.writeUInt16LE(n, 0);
  return b;
}

function u32(n) {
  const b = Buffer.alloc(4);
  b.writeUInt32LE(n >>> 0, 0);
  return b;
}

/** ZIP with store (no compression) — valid for Chrome Web Store upload. */
function buildZipStore(files) {
  const localParts = [];
  const centralParts = [];
  let offset = 0;

  for (const file of files) {
    const data = file.data || readFileSync(file.abs);
    const nameBuf = Buffer.from(file.rel, 'utf8');
    const crc = crc32(data);
    const localHeader = Buffer.concat([
      u32(0x04034b50),
      u16(20),
      u16(0),
      u16(0),
      u16(0),
      u16(0),
      u32(crc),
      u32(data.length),
      u32(data.length),
      u16(nameBuf.length),
      u16(0),
      nameBuf,
    ]);
    const centralHeader = Buffer.concat([
      u32(0x02014b50),
      u16(20),
      u16(20),
      u16(0),
      u16(0),
      u16(0),
      u16(0),
      u32(crc),
      u32(data.length),
      u32(data.length),
      u16(nameBuf.length),
      u16(0),
      u16(0),
      u16(0),
      u16(0),
      u32(0),
      u32(offset),
      nameBuf,
    ]);
    localParts.push(localHeader, data);
    centralParts.push(centralHeader);
    offset += localHeader.length + data.length;
  }

  const central = Buffer.concat(centralParts);
  const end = Buffer.concat([
    u32(0x06054b50),
    u16(0),
    u16(0),
    u16(files.length),
    u16(files.length),
    u32(central.length),
    u32(offset),
    u16(0),
  ]);

  return Buffer.concat([...localParts, central, end]);
}

function parseTarget() {
  const idx = process.argv.indexOf('--target');
  if (idx >= 0 && process.argv[idx + 1]) return process.argv[idx + 1];
  return 'chromium';
}

function main() {
  mkdirSync(DIST, { recursive: true });
  const target = parseTarget();
  if (target !== 'chromium' && target !== 'firefox') {
    throw new Error(`Unknown target: ${target} (use chromium or firefox)`);
  }

  const files = [];
  for (const entry of INCLUDE) {
    if (entry === 'manifest.json') continue;
    collectFiles(entry, ROOT, files);
  }

  const manifest = buildManifestForTarget(target);
  files.unshift({
    abs: join(ROOT, 'manifest.json'),
    rel: 'manifest.json',
    data: Buffer.from(`${JSON.stringify(manifest, null, 2)}\n`, 'utf8'),
  });

  const version = readManifestVersion();
  const suffix = target === 'firefox' ? '.firefox' : '';
  const zipName = `timetracker-extension-v${version}${suffix}.zip`;
  const zipPath = join(DIST, zipName);
  const buffer = buildZipStore(files);
  writeFileSync(zipPath, buffer);

  console.log(`Wrote ${zipPath} (target=${target})`);
  console.log(`  ${files.length} files, ${(buffer.length / 1024).toFixed(1)} KiB`);
  for (const f of files) console.log(`  + ${f.rel}`);
}

try {
  main();
} catch (err) {
  console.error(err.message || err);
  process.exit(1);
}
