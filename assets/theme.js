(function () {
  var root = document.documentElement;
  var systemTheme = window.matchMedia('(prefers-color-scheme: dark)');
  var preference;

  try {
    preference = localStorage.getItem('theme');
  } catch (_) {
    // The theme also works when browser storage is unavailable.
  }

  if (preference === 'light' || preference === 'dark') {
    root.dataset.theme = preference;
  }

  function isDark() {
    return root.dataset.theme ? root.dataset.theme === 'dark' : systemTheme.matches;
  }

  document.addEventListener('DOMContentLoaded', function () {
    var button = document.querySelector('.theme-toggle');
    if (!button) return;

    function updateButton() {
      button.setAttribute('aria-pressed', String(isDark()));
      button.setAttribute('aria-label', isDark() ? '切换到浅色主题' : '切换到深色主题');
    }

    button.hidden = false;
    updateButton();
    systemTheme.addEventListener('change', updateButton);
    button.addEventListener('click', function () {
      root.dataset.theme = isDark() ? 'light' : 'dark';
      try {
        localStorage.setItem('theme', root.dataset.theme);
      } catch (_) {}
      updateButton();
    });
  });
})();
