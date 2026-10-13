const memory = new Map();

/**
 * Renderer store: prefer Electron IPC (encrypted main-process store).
 * Browser/dev fallback uses in-memory only — never localStorage for any key
 * (avoids clear-text persistence of tokens and settings).
 */
export async function storeGet(key) {
  if (window.electronAPI?.storeGet) return window.electronAPI.storeGet(key);
  if (memory.has(key)) return memory.get(key);
  return null;
}

export async function storeSet(key, value) {
  if (window.electronAPI?.storeSet) return window.electronAPI.storeSet(key, value);
  memory.set(key, value);
  return undefined;
}

export async function storeDelete(key) {
  if (window.electronAPI?.storeDelete) return window.electronAPI.storeDelete(key);
  memory.delete(key);
  return undefined;
}

export async function storeClear() {
  if (window.electronAPI?.storeClear) return window.electronAPI.storeClear();
  memory.clear();
  return undefined;
}
