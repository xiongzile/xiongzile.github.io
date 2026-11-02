const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const script = fs.readFileSync(require('node:path').join(__dirname, '../assets/analytics-preference.js'), 'utf8');
function run({ saved = false, hash = '', blocked = false, hostname = 'xiongzile.me' } = {}) {
  const store = new Map(saved ? [['blog.analytics.excluded', '1']] : []);
  const appended = [];
  const button = { setAttribute() {}, addEventListener(_, fn) { this.click = fn; } };
  const status = {};
  const location = { hash, hostname, pathname: '/analytics/', search: '', replace(url) { this.reloaded = url; } };
  vm.runInNewContext(script, {
    location,
    localStorage: {
      getItem(k) { if (blocked) throw Error('blocked'); return store.get(k); },
      setItem(k, v) { if (blocked) throw Error('blocked'); store.set(k, v); },
      removeItem(k) { if (blocked) throw Error('blocked'); store.delete(k); },
    },
    document: { currentScript: { dataset: { token: 'test-site' } },
      getElementById(id) { return id === 'analytics-exclude' ? button : status; },
      createElement() { return { dataset: {} }; }, body: { append(n) { appended.push(n); } } },
  });
  return { store, appended, button, status, location };
}
test('ordinary production visits load one beacon', () => {
  const r = run(); assert.equal(r.appended.length, 1);
  assert.equal(JSON.parse(r.appended[0].dataset.cfBeacon).token, 'test-site');
});
test('saved exclusion prevents requesting the beacon', () => {
  const r = run({ saved: true }); assert.equal(r.appended.length, 0);
  assert.match(r.status.textContent, /are excluded/);
});
test('opt-out link saves exclusion before the first beacon', () => {
  const r = run({ hash: '#exclude-self' }); assert.equal(r.appended.length, 0);
  assert.equal(r.store.get('blog.analytics.excluded'), '1');
});
test('opt-out link also suppresses this page when storage is blocked', () => {
  const r = run({ hash: '#exclude-self', blocked: true });
  assert.equal(r.appended.length, 0); assert.equal(r.button.disabled, true);
  assert.match(r.status.textContent, /cannot be saved/);
});
test('button persists exclusion and reloads; preference survives later pages', () => {
  const r = run(); r.button.click();
  assert.equal(r.store.get('blog.analytics.excluded'), '1');
  assert.equal(r.location.reloaded, '/analytics/');
  assert.equal(run({ saved: true }).appended.length, 0);
});
test('including visits removes both saved exclusion and opt-out fragment', () => {
  const r = run({ saved: true, hash: '#exclude-self' }); r.button.click();
  assert.equal(r.store.has('blog.analytics.excluded'), false);
  assert.equal(r.location.reloaded, '/analytics/');
});
test('local previews never send tracking', () => {
  assert.equal(run({ hostname: '127.0.0.1' }).appended.length, 0);
});
