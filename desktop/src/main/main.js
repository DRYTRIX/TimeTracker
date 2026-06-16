const { app, BrowserWindow, ipcMain, globalShortcut } = require('electron');
const { createWindow } = require('./window');
const { createTray, destroyTray } = require('./tray');
const Store = require('electron-store');

let store = null;

// Parse command line arguments for server URL
function parseCommandLineArgs(args = process.argv.slice(1)) {
  if (!store) return;
  const serverUrlIndex = args.findIndex(arg => arg === '--server-url' || arg === '--server');
  if (serverUrlIndex !== -1 && args[serverUrlIndex + 1]) {
    const serverUrl = args[serverUrlIndex + 1];
    // Validate and store server URL if provided
    try {
      const url = new URL(serverUrl);
      if (url.protocol === 'http:' || url.protocol === 'https:') {
        store.set('server_url', serverUrl);
        console.log(`Server URL set from command line: ${serverUrl}`);
      }
    } catch (e) {
      console.warn(`Invalid server URL provided: ${serverUrl}`);
    }
  }
  
  // Also check environment variable
  if (process.env.TIMETRACKER_SERVER_URL) {
    try {
      const url = new URL(process.env.TIMETRACKER_SERVER_URL);
      if (url.protocol === 'http:' || url.protocol === 'https:') {
        store.set('server_url', process.env.TIMETRACKER_SERVER_URL);
        console.log(`Server URL set from environment: ${process.env.TIMETRACKER_SERVER_URL}`);
      }
    } catch (e) {
      console.warn(`Invalid server URL in environment: ${process.env.TIMETRACKER_SERVER_URL}`);
    }
  }
}

// Keep a global reference of window and tray
let mainWindow = null;
let tray = null;
const { getSplashWindow } = require('./window');

const singleInstanceLock = app.requestSingleInstanceLock();
if (!singleInstanceLock) {
  app.quit();
}

function isLocalOrPrivateHost(hostname) {
  const h = String(hostname || '').toLowerCase();
  if (h === 'localhost' || h === '127.0.0.1' || h === '::1') return true;
  if (h.endsWith('.local')) return true;
  if (/^10\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(h)) return true;
  if (/^192\.168\.\d{1,3}\.\d{1,3}$/.test(h)) return true;
  const m = h.match(/^172\.(\d{1,2})\.\d{1,3}\.\d{1,3}$/);
  if (m) {
    const second = Number(m[1]);
    return second >= 16 && second <= 31;
  }
  return false;
}

app.on('certificate-error', (event, webContents, url, error, certificate, callback) => {
  let hostname = '';
  try {
    hostname = new URL(url).hostname;
  } catch (_) {
    callback(false);
    return;
  }

  if (isLocalOrPrivateHost(hostname)) {
    event.preventDefault();
    callback(true);
    return;
  }

  callback(false);
});

function isUsableWindow(win) {
  return win && !win.isDestroyed();
}

function sendToMainWindow(channel, payload) {
  if (!isUsableWindow(mainWindow)) return false;
  mainWindow.webContents.send(channel, payload);
  return true;
}

function focusMainWindow() {
  if (!isUsableWindow(mainWindow)) return;
  if (mainWindow.isMinimized()) mainWindow.restore();
  if (!mainWindow.isVisible()) mainWindow.show();
  mainWindow.focus();
}

function attachTray(win) {
  destroyTray();
  const trayResult = createTray(win);
  tray = trayResult && trayResult.tray ? trayResult.tray : null;
  updateTrayTooltip = trayResult && trayResult.updateTrayTooltip
    ? trayResult.updateTrayTooltip
    : () => {};
  global.updateTrayMenu = trayResult && trayResult.updateTrayMenu
    ? trayResult.updateTrayMenu
    : null;
}

function createMainWindow(options = {}) {
  mainWindow = createWindow(options);
  attachTray(mainWindow);

  mainWindow.on('close', (event) => {
    const minimizeToTray = store ? store.get('minimize_to_tray', true) : true;
    if (minimizeToTray && !app.isQuitting) {
      event.preventDefault();
      mainWindow.hide();
    }
  });

  mainWindow.on('closed', () => {
    if (mainWindow && mainWindow.isDestroyed()) {
      mainWindow = null;
    }
  });
  return mainWindow;
}

const DEFAULT_SHORTCUTS = {
  toggleTimer: 'CommandOrControl+Shift+T',
  showWindow: 'CommandOrControl+Shift+Period',
};

function registerGlobalShortcuts() {
  if (!store) return;
  const shortcuts = { ...DEFAULT_SHORTCUTS, ...(store.get('global_shortcuts') || {}) };
  try {
    globalShortcut.unregisterAll();
    globalShortcut.register(shortcuts.toggleTimer, () => {
      sendToMainWindow('shortcut:action', 'toggle-timer');
    });
    globalShortcut.register(shortcuts.showWindow, () => {
      focusMainWindow();
    });
  } catch (e) {
    console.warn('TimeTracker: could not register global shortcuts:', e.message);
  }
}

function unregisterGlobalShortcuts() {
  try {
    globalShortcut.unregisterAll();
  } catch (_) {
    /* ignore */
  }
}

// This method will be called when Electron has finished initialization
if (singleInstanceLock) {
app.whenReady().then(() => {
  store = new Store();
  parseCommandLineArgs();
  createMainWindow({ showSplash: true });
  registerGlobalShortcuts();
  
  // Listen for timer status updates from renderer (via IPC)
  ipcMain.on('timer:status-update', (event, data) => {
    const active = Boolean(data && data.active);
    if (global.updateTrayMenu) {
      global.updateTrayMenu(active);
    }
    if (global.updateTrayTitle) {
      global.updateTrayTitle(active ? (data.elapsedLabel || '') : '');
    }
    if (updateTrayTooltip && active && data.timer) {
      const startTime = new Date(data.timer.start_time);
      const elapsed = Math.floor((new Date() - startTime) / 1000);
      const hours = Math.floor(elapsed / 3600);
      const minutes = Math.floor((elapsed % 3600) / 60);
      const seconds = elapsed % 60;
      const timeStr = hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m ${seconds}s`;
      updateTrayTooltip(`Timer: ${timeStr}`);
    } else if (updateTrayTooltip) {
      updateTrayTooltip('TimeTracker');
    }
  });
  
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createMainWindow({ showSplash: false });
    } else {
      focusMainWindow();
    }
  });
});

app.on('second-instance', (event, argv) => {
  parseCommandLineArgs(argv.slice(1));
  focusMainWindow();
});
}

// Quit when all windows are closed, except on macOS (or when minimizing to tray)
app.on('before-quit', () => {
  app.isQuitting = true;
  unregisterGlobalShortcuts();
});

app.on('window-all-closed', () => {
  const minimizeToTray = store ? store.get('minimize_to_tray', true) : false;
  if (process.platform !== 'darwin' && !minimizeToTray) {
    app.quit();
  }
});

// IPC handlers
ipcMain.handle('app:get-version', () => {
  return app.getVersion();
});

ipcMain.handle('store:get', (event, key) => {
  if (!isAllowedStoreKey(key)) return undefined;
  return store ? store.get(key) : undefined;
});

ipcMain.handle('store:set', (event, key, value) => {
  if (!isAllowedStoreKey(key)) return;
  if (!store) return;
  store.set(key, value);
});

ipcMain.handle('store:delete', (event, key) => {
  if (!isAllowedStoreKey(key)) return;
  if (!store) return;
  store.delete(key);
});

ipcMain.handle('store:clear', () => {
  if (!store) return;
  store.clear();
});

// Timer IPC handlers
let timerInterval = null;
let currentTimer = null;

ipcMain.on('timer:start', async (event, data) => {
  // Timer start logic would go here
  // For now, just notify renderer
  currentTimer = { ...data, startTime: new Date() };
  sendToMainWindow('timer:start', currentTimer);
  
  // Start polling timer status
  if (timerInterval) clearInterval(timerInterval);
  timerInterval = setInterval(() => {
    if (currentTimer) {
      const elapsed = Math.floor((new Date() - currentTimer.startTime) / 1000);
      if (!sendToMainWindow('timer:update', { elapsed })) {
        clearInterval(timerInterval);
        timerInterval = null;
        return;
      }
      if (tray) {
        updateTrayTooltip(`Running: ${formatDuration(elapsed)}`);
      }
    }
  }, 1000);
});

ipcMain.on('timer:stop', async (event) => {
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }
  currentTimer = null;
  sendToMainWindow('timer:stop');
  if (tray) {
    updateTrayTooltip('TimeTracker');
  }
});

ipcMain.handle('timer:get-status', () => {
  return currentTimer;
});

function formatDuration(seconds) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  return `${minutes}m ${secs}s`;
}

let updateTrayTooltip = (text) => {
  // Will be set by tray module
};

const ALLOWED_STORE_KEYS = new Set([
  'server_url',
  'api_token',
  'api_token_server_url',
  'username',
  'theme_mode',
  'auto_sync',
  'sync_interval',
  'minimize_to_tray',
  'global_shortcuts',
]);

function isAllowedStoreKey(key) {
  return typeof key === 'string' && ALLOWED_STORE_KEYS.has(key);
}

// Window management
ipcMain.on('window:minimize', () => {
  if (isUsableWindow(mainWindow)) mainWindow.minimize();
});

ipcMain.on('window:maximize', () => {
  if (isUsableWindow(mainWindow)) {
    if (mainWindow.isMaximized()) {
      mainWindow.unmaximize();
    } else {
      mainWindow.maximize();
    }
  }
});

ipcMain.on('window:close', () => {
  if (isUsableWindow(mainWindow)) mainWindow.close();
});

ipcMain.on('window:hide', () => {
  if (isUsableWindow(mainWindow)) mainWindow.hide();
});

ipcMain.on('window:show', () => {
  focusMainWindow();
});

// Splash screen handler
ipcMain.on('splash:ready', () => {
  const splash = getSplashWindow();
  if (splash && !splash.isDestroyed()) {
    splash.close();
  }
});

// Prevent navigation to external URLs (file: uses opaque origin "null", not "file://")
app.on('web-contents-created', (event, contents) => {
  contents.on('will-navigate', (event, navigationUrl) => {
    let parsedUrl;
    try {
      parsedUrl = new URL(navigationUrl);
    } catch {
      event.preventDefault();
      return;
    }
    const protocol = parsedUrl.protocol;
    if (
      protocol === 'file:' ||
      protocol === 'about:' ||
      protocol === 'devtools:'
    ) {
      return;
    }
    if (protocol === 'http:' || protocol === 'https:') {
      event.preventDefault();
      return;
    }
    event.preventDefault();
  });
});
