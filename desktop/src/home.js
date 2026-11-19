'use strict';
const form = document.querySelector('#connect'), button = document.querySelector('#submit'), message = document.querySelector('#message');
window.segmentIQ.connection().then(config => {
  document.querySelector('#origin').value = config.origin;
  document.querySelector('#version').textContent = `SEGMENT IQ · ${config.version} · ${config.platform === 'darwin' ? 'macOS' : 'Windows'}`;
}).catch(() => {message.textContent = 'No se pudo leer la conexión guardada.';});
form.addEventListener('submit', async event => {
  event.preventDefault(); button.disabled = true; message.textContent = 'Comprobando el servidor…';
  try {const result = await window.segmentIQ.open(document.querySelector('#origin').value); message.textContent = result.message;}
  catch {message.textContent = 'No se pudo abrir el laboratorio.';}
  finally {button.disabled = false;}
});
