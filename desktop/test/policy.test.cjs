const {test} = require('node:test');
const assert = require('node:assert/strict');
const {serverOrigin, sameOrigin, requestAllowed, audioOnly} = require('../src/policy.cjs');
test('only TLS and literal loopback HTTP are accepted', () => {
  assert.equal(serverOrigin(' https://lab.example/ '), 'https://lab.example');
  assert.equal(serverOrigin('http://127.0.0.1:8765'), 'http://127.0.0.1:8765');
  for (const url of ['http://cad-cam:8765', 'http://192.168.1.3', 'file:///etc/passwd', 'javascript:alert(1)', 'https://a:b@lab.example', 'https://lab.example/?token=x', 'https://lab.example/evil', 'https://lab.example#x', 'http://127.0.0.1.evil']) assert.throws(() => serverOrigin(url));
});
test('navigation and requests cannot escape configured origin', () => {
  const origin = 'https://lab.example';
  assert.equal(sameOrigin(origin + '/api/cases', origin), true);
  for (const url of ['https://lab.example.evil', 'https://lab.example@evil', 'http://lab.example', 'file:///tmp/a']) assert.equal(sameOrigin(url, origin), false);
  assert.equal(requestAllowed('blob:https://lab.example/123', origin), true);
  assert.equal(requestAllowed('blob:https://evil.example/123', origin), false);
});
test('camera, screen, unknown permission and untrusted frames are refused', () => {
  const origin = 'https://lab.example', good = {requestingUrl: origin + '/', mediaTypes: ['audio'], isMainFrame: true};
  assert.equal(audioOnly('media', origin, good), true);
  for (const details of [{...good, mediaTypes: ['video']}, {...good, mediaTypes: ['audio', 'video']}, {...good, mediaTypes: []}, {...good, requestingUrl: 'https://evil'}, {...good, isMainFrame: false}]) assert.equal(audioOnly('media', origin, details), false);
  assert.equal(audioOnly('display-capture', origin, good), false);
});
