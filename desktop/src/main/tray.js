const { app, Tray, Menu, nativeImage } = require('electron');
const path = require('path');

let tray = null;

function createTray(mainWindow) {
  // Create tray icon
  const iconPath = path.join(__dirname, '../../assets/tray-icon.png');
  const icon = nativeImage.createFromPath(iconPath);
  
  // Fallback to a simple icon if file doesn't exist
  if (icon.isEmpty()) {
    // Create a simple colored icon (16x16)
    const { nativeImage } = require('electron');
    const img = nativeImage.createEmpty();
    // In production, you'd want to use actual icon files
  }

  tray = new Tray(iconPath);
  tray.setToolTip('TimeTracker');

  let isTimerRunning = false;

  // Create context menu
  function buildMenu() {
    return Menu.buildFromTemplate([
      {
        label: 'Show Timer',
        click: () => {
          if (mainWindow) {
            mainWindow.show();
            mainWindow.focus();
          }
        },
      },
      {
        label: 'Start Timer',
        id: 'start-timer',
        enabled: !isTimerRunning,
        visible: !isTimerRunning,
        click: () => {
          // Send message to renderer to start timer via IPC
          if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.webContents.send('tray:action', 'start-timer');
          }
        },
      },
      {
        label: 'Stop Timer',
        id: 'stop-timer',
        enabled: isTimerRunning,
        visible: isTimerRunning,
        click: () => {
          // Send message to renderer to stop timer via IPC
          if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.webContents.send('tray:action', 'stop-timer');
          }
        },
      },
      { type: 'separator' },
      {
        label: 'Quit',
        click: () => {
          app.quit();
        },
      },
    ]);
  }

  tray.setContextMenu(buildMenu());

  // Update tray menu when timer state changes
  function updateTrayMenu(running) {
    isTimerRunning = running;
    tray.setContextMenu(buildMenu());
  }

  // Handle tray click
  tray.on('click', () => {
    if (mainWindow) {
      if (mainWindow.isVisible()) {
        mainWindow.hide();
      } else {
        mainWindow.show();
        mainWindow.focus();
      }
    }
  });

  // Update tray tooltip with timer info
  function updateTooltip(text) {
    tray.setToolTip(`TimeTracker - ${text}`);
  }

  // Listen for timer state changes from renderer
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.on('did-finish-load', () => {
      // Listen for timer status updates from renderer
      mainWindow.webContents.on('timer-status-update', (event, data) => {
        if (data && data.active) {
          updateTrayMenu(true);
          if (data.timer && data.timer.start_time) {
            const startTime = new Date(data.timer.start_time);
            const elapsed = Math.floor((new Date() - startTime) / 1000);
            const hours = Math.floor(elapsed / 3600);
            const minutes = Math.floor((elapsed % 3600) / 60);
            const secs = elapsed % 60;
            const timeStr = hours > 0 
              ? `${hours}h ${minutes}m`
              : `${minutes}m ${secs}s`;
            updateTooltip(`Timer running: ${timeStr}`);
          }
        } else {
          updateTrayMenu(false);
          updateTooltip('TimeTracker');
        }
      });
    });
  }

  // Export functions for use in main.js
  global.updateTrayTooltip = updateTooltip;
  global.updateTrayMenu = updateTrayMenu;

  return { tray, updateTrayMenu, updateTooltip };
}

module.exports = { createTray };
