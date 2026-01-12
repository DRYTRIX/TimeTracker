const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { createWindow } = require('./window');
const { createTray } = require('./tray');
const Store = require('electron-store');

// Initialize store
const store = new Store();

// Parse command line arguments for server URL
function parseCommandLineArgs() {
  const args = process.argv.slice(1); // Skip electron/node path
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

// Parse command line arguments before app is ready
parseCommandLineArgs();

// Keep a global reference of window and tray
let mainWindow = null;
let tray = null;
const { getSplashWindow } = require('./window');

// This method will be called when Electron has finished initialization
app.whenReady().then(() => {
  // Create main window
  mainWindow = createWindow();
  
  // Create system tray
  const trayResult = createTray(mainWindow);
  if (trayResult && trayResult.updateTrayTooltip) {
    updateTrayTooltip = trayResult.updateTrayTooltip;
  }
  if (trayResult && trayResult.updateTrayMenu) {
    global.updateTrayMenu = trayResult.updateTrayMenu;
  }
  
  // Listen for timer status updates from renderer (via IPC)
  ipcMain.on('timer:status-update', (event, data) => {
    if (global.updateTrayMenu) {
      global.updateTrayMenu(data && data.active);
    }
    if (updateTrayTooltip && data && data.active && data.timer) {
      const startTime = new Date(data.timer.start_time);
      const elapsed = Math.floor((new Date() - startTime) / 1000);
      const hours = Math.floor(elapsed / 3600);
      const minutes = Math.floor((elapsed % 3600) / 60);
      const timeStr = hours > 0 
        ? `${hours}h ${minutes}m`
        : `${minutes}m`;
      updateTrayTooltip(`Timer: ${timeStr}`);
    } else if (updateTrayTooltip) {
      updateTrayTooltip('TimeTracker');
    }
  });
  
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      mainWindow = createWindow();
      const trayResult = createTray(mainWindow);
      if (trayResult && trayResult.updateTrayTooltip) {
        updateTrayTooltip = trayResult.updateTrayTooltip;
      }
      if (trayResult && trayResult.updateTrayMenu) {
        global.updateTrayMenu = trayResult.updateTrayMenu;
      }
    }
  });
});

// Quit when all windows are closed, except on macOS
app.on('window-all-closed', () => {
  // On macOS, keep app running even when all windows are closed
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// IPC handlers
ipcMain.handle('app:get-version', () => {
  return app.getVersion();
});

ipcMain.handle('store:get', (event, key) => {
  return store.get(key);
});

ipcMain.handle('store:set', (event, key, value) => {
  store.set(key, value);
});

ipcMain.handle('store:delete', (event, key) => {
  store.delete(key);
});

ipcMain.handle('store:clear', () => {
  store.clear();
});

// Timer IPC handlers
let timerInterval = null;
let currentTimer = null;

ipcMain.on('timer:start', async (event, data) => {
  // Timer start logic would go here
  // For now, just notify renderer
  currentTimer = { ...data, startTime: new Date() };
  mainWindow.webContents.send('timer:start', currentTimer);
  
  // Start polling timer status
  if (timerInterval) clearInterval(timerInterval);
  timerInterval = setInterval(() => {
    if (currentTimer) {
      const elapsed = Math.floor((new Date() - currentTimer.startTime) / 1000);
      mainWindow.webContents.send('timer:update', { elapsed });
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
  mainWindow.webContents.send('timer:stop');
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

// Window management
ipcMain.on('window:minimize', () => {
  if (mainWindow) mainWindow.minimize();
});

ipcMain.on('window:maximize', () => {
  if (mainWindow) {
    if (mainWindow.isMaximized()) {
      mainWindow.unmaximize();
    } else {
      mainWindow.maximize();
    }
  }
});

ipcMain.on('window:close', () => {
  if (mainWindow) mainWindow.close();
});

ipcMain.on('window:hide', () => {
  if (mainWindow) mainWindow.hide();
});

ipcMain.on('window:show', () => {
  if (mainWindow) mainWindow.show();
});

// Splash screen handler
ipcMain.on('splash:ready', () => {
  const splash = getSplashWindow();
  if (splash && !splash.isDestroyed()) {
    splash.close();
  }
});

// Prevent navigation to external URLs
app.on('web-contents-created', (event, contents) => {
  contents.on('will-navigate', (event, navigationUrl) => {
    const parsedUrl = new URL(navigationUrl);
    if (parsedUrl.origin !== 'file://') {
      event.preventDefault();
    }
  });
});
