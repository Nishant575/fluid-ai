const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  onFeedback: (callback) => ipcRenderer.on('feedback', callback),
  onBackendMessage: (callback) => ipcRenderer.on('backend-message', (event, data) => callback(data)),
  startSession: () => ipcRenderer.send('start-session'),
  pauseSession: () => ipcRenderer.send('pause-session'),
  resumeSession: () => ipcRenderer.send('resume-session'),
  endSession: () => ipcRenderer.send('end-session'),
  enableMouse: (bounds) => ipcRenderer.send('enable-mouse', bounds),
  disableMouse: () => ipcRenderer.send('disable-mouse')
});