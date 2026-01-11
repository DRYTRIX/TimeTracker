const { BrowserWindow, screen } = require('electron');
const path = require('path');

let windowState = {
  width: 1200,
  height: 800,
  x: undefined,
  y: undefined,
  isMaximized: false,
};

// Try to restore window state
try {
  const fs = require('fs');
  const userDataPath = require('electron').app.getPath('userData');
  const stateFile = path.join(userDataPath, 'window-state.json');
  if (fs.existsSync(stateFile)) {
    windowState = { ...windowState, ...JSON.parse(fs.readFileSync(stateFile, 'utf8')) };
  }
} catch (e) {
  // Ignore errors loading window state
}

function saveWindowState() {
  try {
    const fs = require('fs');
    const userDataPath = require('electron').app.getPath('userData');
    const stateFile = path.join(userDataPath, 'window-state.json');
    fs.writeFileSync(stateFile, JSON.stringify(windowState));
  } catch (e) {
    // Ignore errors saving window state
  }
}

let splashWindow = null;

function createWindow() {
  // Create splash screen first (only if splash.html exists)
  const splashPath = path.join(__dirname, '../renderer/splash.html');
  const fs = require('fs');
  
  if (fs.existsSync(splashPath)) {
    splashWindow = new BrowserWindow({
      width: 500,
      height: 400,
      frame: false,
      transparent: true,
      alwaysOnTop: true,
      skipTaskbar: true,
      backgroundColor: '#00000000',
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true,
        sandbox: false,
      },
    });

    splashWindow.loadFile(splashPath);
    splashWindow.center();
  }

  // Center window if no saved position
  if (windowState.x === undefined || windowState.y === undefined) {
    const { width, height } = screen.getPrimaryDisplay().workAreaSize;
    windowState.x = Math.floor((width - windowState.width) / 2);
    windowState.y = Math.floor((height - windowState.height) / 2);
  }

  const mainWindow = new BrowserWindow({
    width: windowState.width,
    height: windowState.height,
    x: windowState.x,
    y: windowState.y,
    minWidth: 800,
    minHeight: 600,
    show: false, // Don't show until ready
    backgroundColor: '#ffffff',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: false,
    },
    // Icon path - use .ico on Windows, .icns on macOS, .png on Linux
    icon: (() => {
      const iconDir = path.join(__dirname, '../../assets');
      if (process.platform === 'win32') {
        const icoPath = path.join(iconDir, 'icon.ico');
        return require('fs').existsSync(icoPath) ? icoPath : path.join(iconDir, 'icon.png');
      } else if (process.platform === 'darwin') {
        const icnsPath = path.join(iconDir, 'icon.icns');
        return require('fs').existsSync(icnsPath) ? icnsPath : path.join(iconDir, 'icon.png');
      } else {
        return path.join(iconDir, 'icon.png');
      }
    })(),
  });

  // Show window when ready and close splash
  mainWindow.once('ready-to-show', () => {
    if (windowState.isMaximized) {
      mainWindow.maximize();
    }
    mainWindow.show();
    // Close splash screen after a short delay (if it exists)
    if (splashWindow) {
      setTimeout(() => {
        if (splashWindow && !splashWindow.isDestroyed()) {
          splashWindow.close();
        }
      }, 500);
    }
  });

  // Save window state on resize/move
  mainWindow.on('resized', () => {
    windowState.isMaximized = mainWindow.isMaximized();
    if (!windowState.isMaximized) {
      const [width, height] = mainWindow.getSize();
      windowState.width = width;
      windowState.height = height;
    }
    saveWindowState();
  });

  mainWindow.on('moved', () => {
    if (!mainWindow.isMaximized()) {
      const [x, y] = mainWindow.getPosition();
      windowState.x = x;
      windowState.y = y;
      saveWindowState();
    }
  });

  mainWindow.on('maximize', () => {
    windowState.isMaximized = true;
    saveWindowState();
  });

  mainWindow.on('unmaximize', () => {
    windowState.isMaximized = false;
    saveWindowState();
  });

  // Load the HTML file
  const isDev = process.argv.includes('--dev');
  if (isDev) {
    mainWindow.loadURL('http://localhost:3000');
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, '../renderer/index.html'));
  }

  return mainWindow;
}

module.exports = { createWindow, getSplashWindow: () => splashWindow };
