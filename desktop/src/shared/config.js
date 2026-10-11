// Shared configuration between main and renderer processes
// Prefer Electron IPC + encrypted electron-store; never persist secrets in localStorage.

let store = null;

/** Keys that must never be persisted to localStorage (secrets / auth). */
const SENSITIVE_KEYS = new Set([
  'api_token',
  'api_token_server_url',
]);

const memory = new Map();

function readLocalStorageJson(key) {
  if (SENSITIVE_KEYS.has(key)) return null;
  const value = localStorage.getItem(key);
  if (!value) return null;
  try {
    return JSON.parse(value);
  } catch (e) {
    console.warn(`Ignoring corrupt local setting "${key}":`, e);
    localStorage.removeItem(key);
    return null;
  }
}

// Initialize store (called from renderer process)
function initStore() {
  if (window.electronAPI) {
    return {
      get: (key) => window.electronAPI.storeGet(key),
      set: (key, value) => window.electronAPI.storeSet(key, value),
      delete: (key) => window.electronAPI.storeDelete(key),
      clear: () => window.electronAPI.storeClear(),
    };
  }
  // Dev/browser fallback: memory for secrets, localStorage for non-secrets only
  return {
    get: (key) => {
      if (memory.has(key)) return memory.get(key);
      return readLocalStorageJson(key);
    },
    set: (key, value) => {
      memory.set(key, value);
      if (!SENSITIVE_KEYS.has(key)) {
        localStorage.setItem(key, JSON.stringify(value));
      }
    },
    delete: (key) => {
      memory.delete(key);
      localStorage.removeItem(key);
    },
    clear: () => {
      memory.clear();
      localStorage.clear();
    },
  };
}

const storeGet = async (key) => {
  if (window.electronAPI) {
    return await window.electronAPI.storeGet(key);
  }
  if (memory.has(key)) return memory.get(key);
  return readLocalStorageJson(key);
};

const storeSet = async (key, value) => {
  if (window.electronAPI) {
    return await window.electronAPI.storeSet(key, value);
  }
  memory.set(key, value);
  if (!SENSITIVE_KEYS.has(key)) {
    localStorage.setItem(key, JSON.stringify(value));
  }
};

const storeDelete = async (key) => {
  if (window.electronAPI) {
    return await window.electronAPI.storeDelete(key);
  }
  memory.delete(key);
  localStorage.removeItem(key);
};

const storeClear = async () => {
  if (window.electronAPI) {
    return await window.electronAPI.storeClear();
  }
  memory.clear();
  localStorage.clear();
};

// Export for CommonJS
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { storeGet, storeSet, storeDelete, storeClear, initStore };
}

// Export for browser/ES modules
if (typeof window !== 'undefined') {
  window.config = { storeGet, storeSet, storeDelete, storeClear };
}
