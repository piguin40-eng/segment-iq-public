// Optional integration test. Uses a synthetic HTTP server, never a real case.
const assert = require('node:assert/strict');
const http = require('node:http');
const path = require('node:path');
const fs = require('node:fs/promises');
const {_electron} = require(process.env.SEGMENT_IQ_PLAYWRIGHT || 'playwright');
async function main() {
  const server = http.createServer((req, res) => {
    if (req.url === '/health') { res.setHeader('Content-Type', 'application/json'); res.end(JSON.stringify({status: 'ok', service: 'SEGMENT IQ', version: 'synthetic'})); }
    else {res.setHeader('Content-Type', 'text/html'); res.end('<!doctype html><title>Synthetic SEGMENT IQ</title><h1>Laboratorio de prueba sin casos</h1>');}
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const directory = path.resolve('dist/smoke'); await fs.mkdir(directory, {recursive: true});
  const profile = await fs.mkdtemp(path.join(directory, 'profile-'));
  let electron;
  try {
    electron = await _electron.launch({executablePath: process.env.SEGMENT_IQ_EXECUTABLE || require('electron'),
      args: process.env.SEGMENT_IQ_EXECUTABLE ? ['--user-data-dir=' + profile] : [path.resolve('.'), '--user-data-dir=' + profile],
      timeout: 30000});
    const home = await electron.firstWindow();
    await home.waitForSelector('#origin');
    await electron.evaluate(({BrowserWindow}) => BrowserWindow.getAllWindows()[0].setSize(1100, 940));
    await home.locator('#origin').fill('http://127.0.0.1:8765');
    await home.screenshot({path: path.join(directory, 'Inicio_SEGMENT_IQ.png')});
    const blocked = await home.evaluate(() => window.segmentIQ.open('http://remote.example'));
    assert.equal(blocked.ok, false);
    const opened = electron.waitForEvent('window');
    const response = await home.evaluate(origin => window.segmentIQ.open(origin), `http://127.0.0.1:${server.address().port}`);
    assert.equal(response.ok, true, response.message);
    const workspace = await opened;
    await workspace.waitForSelector('h1');
    assert.equal(await workspace.locator('h1').textContent(), 'Laboratorio de prueba sin casos');
    assert.deepEqual(await workspace.evaluate(() => [typeof window.segmentIQ, typeof require, typeof process]), ['undefined', 'undefined', 'undefined']);
    const origin = workspace.url();
    await workspace.evaluate(() => {location.href = 'https://example.com/';});
    await new Promise(resolve => setTimeout(resolve, 500));
    assert.equal(workspace.url(), origin);
    const unsafe = await workspace.evaluate(async () => {try {await fetch('https://example.com/'); return false;} catch {return true;}});
    assert.equal(unsafe, true);
    console.log('PASS: native window, real IPC, connection, no remote Node/IPC, blocked HTTP LAN, navigation and remote network. Synthetic server only.');
  } finally {if (electron) await electron.close(); server.closeAllConnections(); await new Promise(resolve => server.close(resolve));}
}
main().catch(error => {console.error(error); process.exitCode = 1;});
