/**
 * Package the extension into dist/timetracker-extension-vX.Y.Z.zip
 * for Chrome Web Store / sideload distribution.
 *
 * Usage (from browser-extension/):
 *   npm run zip
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
    const data = readFileSync(file.abs);
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

function main() {
  mkdirSync(DIST, { recursive: true });

  const files = [];
  for (const entry of INCLUDE) {
    collectFiles(entry, ROOT, files);
  }

  const version = readManifestVersion();
  const zipName = `timetracker-extension-v${version}.zip`;
  const zipPath = join(DIST, zipName);
  const buffer = buildZipStore(files);
  writeFileSync(zipPath, buffer);

  console.log(`Wrote ${zipPath}`);
  console.log(`  ${files.length} files, ${(buffer.length / 1024).toFixed(1)} KiB`);
  for (const f of files) console.log(`  + ${f.rel}`);
}

try {
  main();
} catch (err) {
  console.error(err.message || err);
  process.exit(1);
}
