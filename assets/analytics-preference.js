(() => {
  const key = 'blog.analytics.excluded';
  const loader = document.currentScript;
  let excluded = false;
  let storageAvailable = true;
  try {
    if (location.hash === '#exclude-self') localStorage.setItem(key, '1');
    excluded = localStorage.getItem(key) === '1';
  } catch (_) {
    storageAvailable = false;
    excluded = location.hash === '#exclude-self';
  }
  const button = document.getElementById('analytics-exclude');
  const status = document.getElementById('analytics-preference-status');
  if (status) {
    status.textContent = storageAvailable
      ? (excluded ? 'Your visits in this browser are excluded.' : 'Your visits in this browser are currently included.')
      : 'Browser storage is unavailable. Your exclusion cannot be saved; allow site storage and try again.';
  }
  if (button) {
    button.disabled = !storageAvailable;
    button.textContent = excluded ? 'Include my visits again' : 'Ignore my visits';
    button.setAttribute('aria-pressed', String(excluded));
    button.addEventListener('click', () => {
      try {
        if (excluded) localStorage.removeItem(key);
        else localStorage.setItem(key, '1');
        // Reload unloads an already-running beacon before exclusion takes effect.
        location.replace(location.pathname + location.search);
      } catch (_) {
        status.textContent = 'Could not save this setting. Allow site storage and try again.';
      }
    });
  }
  // No beacon is requested on excluded browsers, local previews, or opt-out links.
  if (excluded || location.hash === '#exclude-self'
      || !['xiongzile.me', 'www.xiongzile.me', 'xiongzile.com', 'www.xiongzile.com'].includes(location.hostname)) return;
  const beacon = document.createElement('script');
  beacon.type = 'module';
  beacon.src = 'https://static.cloudflareinsights.com/beacon.min.js';
  beacon.dataset.cfBeacon = JSON.stringify({ token: loader.dataset.token });
  document.body.append(beacon);
})();
