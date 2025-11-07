const { app, BrowserWindow, screen, ipcMain } = require('electron');
const path = require('path');
const mic = require('mic');
const WebSocket = require('ws');

let overlayWindow;
let ws;
let micInstance;
let isRecording = false;

function createOverlay() {
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width, height } = primaryDisplay.workAreaSize;

  // Create a bottom-positioned panel instead of fullscreen
  overlayWindow = new BrowserWindow({
    width: 1000,           // Wide panel
    height: 1000,           // Tall enough for content
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: false,
    hasShadow: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    // Position at bottom center
    x: Math.floor((width - 1000) / 2),
    y: height - 530  // 280px from bottom (leaves space)
  });

  overlayWindow.loadFile('overlay.html');
  
  overlayWindow.setAlwaysOnTop(true, 'floating', 1);
  overlayWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
}

function connectWebSocket() {
  ws = new WebSocket('ws://localhost:8000/ws');
  
  ws.on('open', () => {
    console.log('✅ Connected to backend');
  });
  
  ws.on('message', (data) => {
    const message = JSON.parse(data);
    overlayWindow.webContents.send('backend-message', message);
  });
  
  ws.on('error', (error) => {
    console.error('❌ WebSocket error:', error);
  });
  
  ws.on('close', () => {
    console.log('❌ Disconnected from backend');
  });
}

function startMicrophone() {
  if (isRecording) return;
  
  micInstance = mic({
    rate: '16000',
    channels: '1',
    debug: false,
    exitOnSilence: 0,
    fileType: 'raw'
  });
  
  const micInputStream = micInstance.getAudioStream();
  
  micInputStream.on('data', (data) => {
    if (ws && ws.readyState === WebSocket.OPEN && isRecording) {
      ws.send(data);
    }
  });
  
  micInputStream.on('error', (err) => {
    console.error('❌ Microphone error:', err);
  });
  
  micInstance.start();
  isRecording = true;
  console.log('🎤 Microphone started');
}

function stopMicrophone() {
  if (micInstance) {
    micInstance.stop();
    isRecording = false;
    console.log('⏹️ Microphone stopped');
  }
}

// Handle control commands from overlay
ipcMain.on('start-session', () => {
  console.log('▶️ Starting session...');
  startMicrophone();
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'START_SESSION' }));
  }
});

ipcMain.on('pause-session', () => {
  console.log('⏸️ Pausing session...');
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'PAUSE_SESSION' }));
  }
});

ipcMain.on('resume-session', () => {
  console.log('▶️ Resuming session...');
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'RESUME_SESSION' }));
  }
});

ipcMain.on('end-session', () => {
  console.log('⏹️ Ending session...');
  stopMicrophone();
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'END_SESSION' }));
  }
});

// Handle window dragging
ipcMain.on('start-drag', (event, { mouseX, mouseY }) => {
  const bounds = overlayWindow.getBounds();
  const offsetX = mouseX;
  const offsetY = mouseY;
  
  overlayWindow.on('will-move', (event, newBounds) => {
    // Prevent moving outside screen
    const display = screen.getPrimaryDisplay();
    const maxX = display.bounds.width - bounds.width;
    const maxY = display.bounds.height - bounds.height;
    
    if (newBounds.x < 0) newBounds.x = 0;
    if (newBounds.y < 0) newBounds.y = 0;
    if (newBounds.x > maxX) newBounds.x = maxX;
    if (newBounds.y > maxY) newBounds.y = maxY;
  });
});

app.whenReady().then(() => {
  createOverlay();
  
  setTimeout(() => {
    connectWebSocket();
  }, 1000);
});

app.on('window-all-closed', () => {
  stopMicrophone();
  if (ws) ws.close();
  app.quit();
});



