const { app, Tray, Menu, nativeImage } = require('electron');
const path = require('path');
const fs = require('fs');

let tray = null;

/** Valid minimal PNG (1x1) — used when asset files are missing. */
const FALLBACK_TRAY_PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
  'base64'
);

/**
 * Load tray image as NativeImage.
 * Paths inside app.asar cannot be passed to `new Tray(path)` on Linux; reading
 * bytes and using createFromBuffer works with asar archives.
 */
function loadTrayNativeImage() {
  const candidates = [
    path.join(__dirname, '../../assets/tray-icon.png'),
    path.join(__dirname, '../../assets/icon.png'),
  ];
  for (const candidate of candidates) {
    try {
      if (!fs.existsSync(candidate)) continue;
      const buf = fs.readFileSync(candidate);
      const img = nativeImage.createFromBuffer(buf);
      if (!img.isEmpty()) return img;
    } catch {
      /* try next candidate */
    }
  }
  return nativeImage.createFromBuffer(FALLBACK_TRAY_PNG);
}

function createTray(mainWindow) {
  let icon;
  try {
    icon = loadTrayNativeImage();
  } catch (e) {
    console.warn('TimeTracker: tray icon load failed:', e.message);
    return null;
  }
  if (!icon || icon.isEmpty()) {
    console.warn('TimeTracker: tray icon empty; skipping system tray');
    return null;
  }

  try {
    tray = new Tray(icon);
  } catch (e) {
    console.warn('TimeTracker: could not create tray:', e.message);
    tray = null;
    return null;
  }

  tray.setToolTip('TimeTracker');

  let isTimerRunning = false;
  let isTimerPaused = false;

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
          if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.webContents.send('tray:action', 'start-timer');
          }
        },
      },
      {
        label: 'Pause Timer',
        id: 'pause-timer',
        enabled: isTimerRunning && !isTimerPaused,
        visible: isTimerRunning && !isTimerPaused,
        click: () => {
          if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.webContents.send('tray:action', 'pause-timer');
          }
        },
      },
      {
        label: 'Resume Timer',
        id: 'resume-timer',
        enabled: isTimerRunning && isTimerPaused,
        visible: isTimerRunning && isTimerPaused,
        click: () => {
          if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.webContents.send('tray:action', 'resume-timer');
          }
        },
      },
      {
        label: 'Stop Timer',
        id: 'stop-timer',
        enabled: isTimerRunning,
        visible: isTimerRunning,
        click: () => {
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

  function updateTrayMenu(running, paused = false) {
    if (!tray || tray.isDestroyed()) return;
    isTimerRunning = running;
    isTimerPaused = Boolean(paused);
    tray.setContextMenu(buildMenu());
  }

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

  function updateTooltip(text) {
    if (!tray || tray.isDestroyed()) return;
    tray.setToolTip(`TimeTracker - ${text}`);
  }

  function updateTrayTitle(title) {
    if (!tray || tray.isDestroyed()) return;
    if (typeof tray.setTitle === 'function') {
      tray.setTitle(title || '');
    }
  }

  global.updateTrayTooltip = updateTooltip;
  global.updateTrayMenu = updateTrayMenu;
  global.updateTrayTitle = updateTrayTitle;

  return { tray, updateTrayMenu, updateTooltip, updateTrayTitle };
}

function destroyTray() {
  if (tray && !tray.isDestroyed()) {
    tray.destroy();
  }
  tray = null;
  global.updateTrayTooltip = null;
  global.updateTrayMenu = null;
}

module.exports = { createTray, destroyTray };
