const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { createWindow } = require('./window');
const { createTray } = require('./tray');
const Store = require('electron-store');

// Initialize store
const store = new Store();

// Keep a global reference of window and tray
let mainWindow = null;
let tray = null;

// This method will be called when Electron has finished initialization
app.whenReady().then(() => {
  // Create main window
  mainWindow = createWindow();
  
  // Create system tray
  tray = createTray(mainWindow);
  
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      mainWindow = createWindow();
      tray = createTray(mainWindow);
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

// Prevent navigation to external URLs
app.on('web-contents-created', (event, contents) => {
  contents.on('will-navigate', (event, navigationUrl) => {
    const parsedUrl = new URL(navigationUrl);
    if (parsedUrl.origin !== 'file://') {
      event.preventDefault();
    }
  });
});
