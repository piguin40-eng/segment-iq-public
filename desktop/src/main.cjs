'use strict';
const {app, BrowserWindow, ipcMain, protocol, session, dialog, Menu} = require('electron');
const fs = require('node:fs/promises');
const path = require('node:path');
const crypto = require('node:crypto');
const {serverOrigin, sameOrigin, requestAllowed, audioOnly} = require('./policy.cjs');
const HOME = 'segmentiq://desktop/index.html';
const LOCAL = new Map([
  ['/index.html', ['index.html', 'text/html']],
  ['/style.css', ['style.css', 'text/css']],
  ['/home.js', ['home.js', 'text/javascript']]
]);
const CSP = "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'";
protocol.registerSchemesAsPrivileged([{scheme: 'segmentiq', privileges: {standard: true, secure: true, supportFetchAPI: true}}]);
let home, workspace, connecting = false, quitting = false;
if (!app.requestSingleInstanceLock()) app.quit();
app.on('second-instance', () => { if (home) {home.show(); home.focus();} });
app.on('before-quit', () => {quitting = true;});

const prefs = {sandbox: true, contextIsolation: true, nodeIntegration: false,
  webSecurity: true, allowRunningInsecureContent: false, webviewTag: false};

function guardIPC(event) {
  if (!home || event.sender !== home.webContents || event.senderFrame !== home.webContents.mainFrame || event.senderFrame.url !== HOME) {
    throw Error('Solicitud no permitida.');
  }
}

async function readConfig() {
  try { const data = JSON.parse(await fs.readFile(path.join(app.getPath('userData'), 'connection.json'), 'utf8')); return {origin: serverOrigin(data.origin)}; }
  catch { return {origin: 'http://127.0.0.1:8765'}; }
}

async function probe(origin) {
  const result = await fetch(origin + '/health', {redirect: 'error', signal: AbortSignal.timeout(8000)});
  if (!result.ok || Number(result.headers.get('content-length')) > 16384) throw Error('El servidor no respondió correctamente.');
  const reader = result.body.getReader(); let size = 0, parts = [];
  try {
    while (true) { const chunk = await reader.read(); if (chunk.done) break; size += chunk.value.length;
      if (size > 16384) throw Error('Respuesta inesperada del servidor.'); parts.push(chunk.value); }
  } finally { await reader.cancel(); }
  const data = JSON.parse(Buffer.concat(parts).toString('utf8'));
  if (data.service !== 'SEGMENT IQ' || data.status !== 'ok') throw Error('La dirección no corresponde a un servidor SEGMENT IQ disponible.');
  return String(data.version || '');
}

async function connect(origin) {
  await probe(origin);
  if (workspace && !workspace.isDestroyed()) { workspace.close(); if (!workspace.isDestroyed()) throw Error('Cierra primero la ventana del trabajo.'); }
  // Memory-only session: never write laboratory passwords/cookies to this client.
  const isolated = session.fromPartition('lab-' + crypto.createHash('sha256').update(origin).digest('hex'));
  await isolated.clearStorageData();
  isolated.webRequest.onBeforeRequest((details, callback) => callback({cancel: !requestAllowed(details.url, origin)}));
  isolated.setPermissionCheckHandler((_wc, permission, requestingOrigin, details) =>
    permission === 'media' && sameOrigin(requestingOrigin, origin) && details.mediaType === 'audio');
  isolated.setPermissionRequestHandler(async (wc, permission, callback, details) => {
    if (!workspace || workspace.isDestroyed() || wc !== workspace.webContents || !audioOnly(permission, origin, details)) return callback(false);
    const answer = await dialog.showMessageBox(workspace, {type: 'question', buttons: ['Permitir micrófono', 'Cancelar'], defaultId: 1, cancelId: 1,
      title: 'Dictado de correcciones', message: '¿Permitir el micrófono para esta sesión?', detail: 'El audio se enviará a tu servidor SEGMENT IQ para transcribirlo. No se permite grabar la cámara ni la pantalla.'});
    callback(answer.response === 0);
  });
  isolated.on('will-download', (_event, item) => { item.setSaveDialogOptions({title: 'Guardar resultado de SEGMENT IQ'}); });
  workspace = new BrowserWindow({width: 1440, height: 950, minWidth: 900, title: 'SEGMENT IQ · Laboratorio',
    webPreferences: {...prefs, session: isolated}}); // No preload/IPC bridge on remote pages.
  workspace.webContents.setWindowOpenHandler(() => ({action: 'deny'}));
  for (const name of ['will-navigate', 'will-redirect']) workspace.webContents.on(name, (event, url) => {if (!sameOrigin(url, origin)) event.preventDefault();});
  workspace.on('closed', () => {workspace = null; isolated.clearStorageData().catch(() => {}); if (!quitting && home && !home.isDestroyed()) home.show();});
  await workspace.loadURL(origin + '/');
  await fs.mkdir(app.getPath('userData'), {recursive: true});
  const dest = path.join(app.getPath('userData'), 'connection.json');
  await fs.writeFile(dest + '.tmp', JSON.stringify({origin}), {mode: 0o600}); await fs.rename(dest + '.tmp', dest);
}

app.whenReady().then(async () => {
  protocol.handle('segmentiq', async request => {
    const url = new URL(request.url), item = LOCAL.get(url.pathname);
    if (url.host !== 'desktop' || !item) return new Response('Not found', {status: 404});
    return new Response(await fs.readFile(path.join(__dirname, item[0])), {headers: {'content-type': item[1], 'content-security-policy': CSP, 'x-content-type-options': 'nosniff'}});
  });
  session.defaultSession.setPermissionRequestHandler((_wc, _permission, callback) => callback(false));
  session.defaultSession.setPermissionCheckHandler(() => false);
  Menu.setApplicationMenu(Menu.buildFromTemplate([
    ...(process.platform === 'darwin' ? [{role: 'appMenu'}] : []),
    {label: 'SEGMENT IQ', submenu: [{label: 'Conexión al laboratorio', click: () => {home.show(); home.focus();}}, {role: 'quit'}]},
    {role: 'editMenu'}, {label: 'Ver', submenu: [{role: 'reload'}, {role: 'resetZoom'}, {role: 'zoomIn'}, {role: 'zoomOut'}, {role: 'togglefullscreen'}]}
  ]));
  home = new BrowserWindow({width: 1100, height: 800, minWidth: 780, minHeight: 650, title: 'SEGMENT IQ Preview', backgroundColor: '#101119',
    webPreferences: {...prefs, preload: path.join(__dirname, 'preload.cjs')}});
  home.webContents.setWindowOpenHandler(() => ({action: 'deny'}));
  home.webContents.on('will-navigate', (event, url) => {if (url !== HOME) event.preventDefault();});
  ipcMain.handle('connection:get', async event => {guardIPC(event); return {...await readConfig(), version: app.getVersion(), platform: process.platform};});
  ipcMain.handle('connection:open', async (event, value) => {
    guardIPC(event);
    if (connecting) return {ok: false, message: 'Comprobando la conexión…'};
    connecting = true;
    try { const origin = serverOrigin(value); await connect(origin); return {ok: true, message: 'Laboratorio abierto. Inicia sesión con tu cuenta.'}; }
    catch (error) { return {ok: false, message: error.message.startsWith('fetch') ? 'No se pudo conectar. Comprueba la dirección, el certificado y que el servidor esté encendido.' : error.message}; }
    finally {connecting = false;}
  });
  await home.loadURL(HOME);
  home.on('close', event => { if (!quitting && workspace && !workspace.isDestroyed()) {event.preventDefault(); home.hide();} });
});
app.on('window-all-closed', () => app.quit());
