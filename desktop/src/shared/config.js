// Shared configuration between main and renderer processes.
// Prefer Electron IPC + encrypted electron-store; memory-only fallback (no localStorage).

const memory = new Map();

function initStore() {
  if (typeof window !== 'undefined' && window.electronAPI) {
    return {
      get: (key) => window.electronAPI.storeGet(key),
      set: (key, value) => window.electronAPI.storeSet(key, value),
      delete: (key) => window.electronAPI.storeDelete(key),
      clear: () => window.electronAPI.storeClear(),
    };
  }
  return {
    get: (key) => (memory.has(key) ? memory.get(key) : null),
    set: (key, value) => {
      memory.set(key, value);
    },
    delete: (key) => {
      memory.delete(key);
    },
    clear: () => {
      memory.clear();
    },
  };
}

const storeGet = async (key) => {
  if (typeof window !== 'undefined' && window.electronAPI) {
    return await window.electronAPI.storeGet(key);
  }
  return memory.has(key) ? memory.get(key) : null;
};

const storeSet = async (key, value) => {
  if (typeof window !== 'undefined' && window.electronAPI) {
    return await window.electronAPI.storeSet(key, value);
  }
  memory.set(key, value);
};

const storeDelete = async (key) => {
  if (typeof window !== 'undefined' && window.electronAPI) {
    return await window.electronAPI.storeDelete(key);
  }
  memory.delete(key);
};

const storeClear = async () => {
  if (typeof window !== 'undefined' && window.electronAPI) {
    return await window.electronAPI.storeClear();
  }
  memory.clear();
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { storeGet, storeSet, storeDelete, storeClear, initStore };
}

if (typeof window !== 'undefined') {
  window.config = { storeGet, storeSet, storeDelete, storeClear };
}
