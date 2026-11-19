'use strict';
const {contextBridge, ipcRenderer} = require('electron');
contextBridge.exposeInMainWorld('segmentIQ', Object.freeze({
  connection: () => ipcRenderer.invoke('connection:get'),
  open: origin => ipcRenderer.invoke('connection:open', origin)
}));
