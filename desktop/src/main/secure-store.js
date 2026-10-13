/**
 * Encrypted electron-store backed by Electron safeStorage when available.
 * Falls back to an opaque random key persisted only in userData when
 * safeStorage is unavailable (e.g. some CI/Linux headless environments).
 */
const { app, safeStorage } = require('electron');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const Store = require('electron-store');

const KEY_FILE = 'store-encryption.key';

function loadOrCreateRawKey() {
  const keyPath = path.join(app.getPath('userData'), KEY_FILE);
  try {
    if (fs.existsSync(keyPath)) {
      const raw = fs.readFileSync(keyPath);
      if (raw && raw.length >= 32) return raw.subarray(0, 32);
    }
  } catch (_) {
    /* recreate below */
  }
  const key = crypto.randomBytes(32);
  try {
    fs.writeFileSync(keyPath, key, { mode: 0o600 });
  } catch (_) {
    /* best-effort */
  }
  return key;
}

function resolveEncryptionKey() {
  const raw = loadOrCreateRawKey();
  if (safeStorage && typeof safeStorage.isEncryptionAvailable === 'function' && safeStorage.isEncryptionAvailable()) {
    const sealedPath = path.join(app.getPath('userData'), 'store-encryption.sealed');
    try {
      if (fs.existsSync(sealedPath)) {
        const sealed = fs.readFileSync(sealedPath);
        const opened = safeStorage.decryptString(sealed);
        if (opened && opened.length >= 32) {
          return Buffer.from(opened, 'base64').subarray(0, 32).toString('utf8');
        }
      }
    } catch (_) {
      /* fall through to seal new key */
    }
    try {
      const b64 = raw.toString('base64');
      const sealed = safeStorage.encryptString(b64);
      fs.writeFileSync(sealedPath, sealed, { mode: 0o600 });
      // Prefer sealed key going forward; remove plaintext key file if present
      try {
        fs.unlinkSync(path.join(app.getPath('userData'), KEY_FILE));
      } catch (_) {
        /* ignore */
      }
      return Buffer.from(b64, 'base64').subarray(0, 32).toString('utf8');
    } catch (_) {
      /* fall back to raw key string */
    }
  }
  // electron-store encryptionKey must be a string
  return raw.toString('base64');
}

function createSecureStore() {
  const encryptionKey = resolveEncryptionKey();
  const store = new Store({
    name: 'config-enc',
    encryptionKey,
    clearInvalidConfig: true,
  });

  // One-time migrate from legacy plaintext electron-store ("config")
  try {
    const legacy = new Store({ name: 'config' });
    const legacyData = legacy.store;
    if (legacyData && typeof legacyData === 'object' && Object.keys(legacyData).length > 0) {
      if (!store.get('__migrated_from_plaintext')) {
        for (const [k, v] of Object.entries(legacyData)) {
          if (store.get(k) === undefined) {
            store.set(k, v);
          }
        }
        store.set('__migrated_from_plaintext', true);
        try {
          legacy.clear();
        } catch (_) {
          /* ignore */
        }
      }
    }
  } catch (_) {
    /* ignore migration failures */
  }

  return store;
}

module.exports = { createSecureStore };
