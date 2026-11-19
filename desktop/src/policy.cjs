'use strict';

function serverOrigin(value) {
  if (typeof value !== 'string' || value.length > 2048) throw Error('Dirección no válida.');
  let url;
  try { url = new URL(value.trim()); } catch { throw Error('Introduce una dirección completa: https://servidor o http://127.0.0.1:8765'); }
  if (url.username || url.password || url.search || url.hash || !['', '/'].includes(url.pathname)) {
    throw Error('Usa solo la dirección del servidor, sin claves, rutas ni parámetros.');
  }
  const loopback = ['127.0.0.1', '[::1]'].includes(url.hostname);
  if (url.protocol !== 'https:' && !(url.protocol === 'http:' && loopback)) {
    throw Error('Para otro ordenador se requiere HTTPS con un certificado válido. En este equipo puedes usar http://127.0.0.1:8765');
  }
  return url.origin;
}

function sameOrigin(candidate, origin) {
  try { return new URL(candidate).origin === origin; } catch { return false; }
}

function requestAllowed(candidate, origin) {
  // blob resources inherit their creator's origin. No arbitrary remote CDNs.
  return sameOrigin(candidate, origin) || candidate.startsWith('data:');
}

function audioOnly(permission, origin, details = {}) {
  return permission === 'media' && details.isMainFrame !== false &&
    sameOrigin(details.requestingUrl || details.requestingOrigin || '', origin) &&
    Array.isArray(details.mediaTypes) && details.mediaTypes.length === 1 && details.mediaTypes[0] === 'audio';
}

module.exports = {serverOrigin, sameOrigin, requestAllowed, audioOnly};
