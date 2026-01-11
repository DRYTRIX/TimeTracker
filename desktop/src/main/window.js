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

function createWindow() {
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
    icon: path.join(__dirname, '../../assets/icon.png'),
  });

  // Show window when ready
  mainWindow.once('ready-to-show', () => {
    if (windowState.isMaximized) {
      mainWindow.maximize();
    }
    mainWindow.show();
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

module.exports = { createWindow };
