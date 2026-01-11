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

  // Create context menu
  const contextMenu = Menu.buildFromTemplate([
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
      enabled: true,
      click: () => {
        // TODO: Start timer
        updateTrayMenu(false);
      },
    },
    {
      label: 'Stop Timer',
      id: 'stop-timer',
      enabled: false,
      click: () => {
        // TODO: Stop timer
        updateTrayMenu(true);
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

  tray.setContextMenu(contextMenu);

  // Update tray menu when timer state changes
  function updateTrayMenu(isRunning) {
    const menu = Menu.buildFromTemplate([
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
        enabled: !isRunning,
        visible: !isRunning,
        click: () => {
          // TODO: Start timer
          updateTrayMenu(false);
        },
      },
      {
        label: 'Stop Timer',
        id: 'stop-timer',
        enabled: isRunning,
        visible: isRunning,
        click: () => {
          // TODO: Stop timer
          updateTrayMenu(true);
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
    tray.setContextMenu(menu);
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

  // Export functions for use in main.js
  global.updateTrayTooltip = updateTooltip;
  global.updateTrayMenu = updateTrayMenu;

  return { tray, updateTrayMenu, updateTooltip };
}

module.exports = { createTray };
