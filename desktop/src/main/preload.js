const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
  // App info
  getVersion: () => ipcRenderer.invoke('app:get-version'),
  
  // Store operations
  storeGet: (key) => ipcRenderer.invoke('store:get', key),
  storeSet: (key, value) => ipcRenderer.invoke('store:set', key, value),
  storeDelete: (key) => ipcRenderer.invoke('store:delete', key),
  storeClear: () => ipcRenderer.invoke('store:clear'),
  
  // Window operations
  minimizeWindow: () => ipcRenderer.send('window:minimize'),
  maximizeWindow: () => ipcRenderer.send('window:maximize'),
  closeWindow: () => ipcRenderer.send('window:close'),
  hideWindow: () => ipcRenderer.send('window:hide'),
  showWindow: () => ipcRenderer.send('window:show'),
  
  // Timer events (from main process)
  onTimerUpdate: (callback) => {
    ipcRenderer.on('timer:update', (event, data) => callback(data));
  },
  onTimerStart: (callback) => {
    ipcRenderer.on('timer:start', (event, data) => callback(data));
  },
  onTimerStop: (callback) => {
    ipcRenderer.on('timer:stop', (event) => callback());
  },
  
  // Tray timer events (from main process)
  onTrayAction: (callback) => {
    ipcRenderer.on('tray:action', (event, action) => callback(action));
  },
  
  // Timer actions (to main process)
  timerStart: (projectId, taskId) => ipcRenderer.send('timer:start', { projectId, taskId }),
  timerStop: () => ipcRenderer.send('timer:stop'),
  timerGetStatus: () => ipcRenderer.invoke('timer:get-status'),
  
  // Send timer status to main process (for tray updates)
  sendTimerStatus: (data) => ipcRenderer.send('timer:status-update', data),
  
  // Splash screen
  splashReady: () => ipcRenderer.send('splash:ready'),
});
