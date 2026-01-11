// Shared configuration between main and renderer processes
// This is a simple wrapper around electron-store for the renderer process

let store = null;

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
  // Fallback to localStorage if electron API not available
  return {
    get: (key) => {
      const value = localStorage.getItem(key);
      return value ? JSON.parse(value) : null;
    },
    set: (key, value) => {
      localStorage.setItem(key, JSON.stringify(value));
    },
    delete: (key) => {
      localStorage.removeItem(key);
    },
    clear: () => {
      localStorage.clear();
    },
  };
}

const storeGet = async (key) => {
  if (window.electronAPI) {
    return await window.electronAPI.storeGet(key);
  }
  const value = localStorage.getItem(key);
  return value ? JSON.parse(value) : null;
};

const storeSet = async (key, value) => {
  if (window.electronAPI) {
    return await window.electronAPI.storeSet(key, value);
  }
  localStorage.setItem(key, JSON.stringify(value));
};

const storeDelete = async (key) => {
  if (window.electronAPI) {
    return await window.electronAPI.storeDelete(key);
  }
  localStorage.removeItem(key);
};

const storeClear = async () => {
  if (window.electronAPI) {
    return await window.electronAPI.storeClear();
  }
  localStorage.clear();
};

// Export for CommonJS
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { storeGet, storeSet, storeDelete, storeClear };
}

// Export for browser/ES modules
if (typeof window !== 'undefined') {
  window.config = { storeGet, storeSet, storeDelete, storeClear };
}
