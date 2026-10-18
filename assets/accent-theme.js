(() => {
  const root = document.documentElement;
  const colors = ['teal', 'blue', 'purple', 'rose', 'orange'];
  const storageKey = 'accent-color';
  let selected = 'teal';

  // Apply the saved color before the page is painted, alongside the light/dark theme.
  try {
    const saved = localStorage.getItem(storageKey);
    if (colors.includes(saved)) selected = saved;
  } catch (_) {
    // Color switching still works when browser storage is unavailable.
  }
  root.dataset.accent = selected;

  document.addEventListener('DOMContentLoaded', () => {
    const picker = document.querySelector('.accent-picker');
    const toggle = picker.querySelector('.accent-toggle');
    const options = picker.querySelector('.accent-options');
    const choices = picker.querySelectorAll('.accent-choice');

    const showOptions = (open) => {
      toggle.setAttribute('aria-expanded', String(open));
      options.hidden = !open;
    };
    const updateChoices = () => {
      choices.forEach((choice) => {
        choice.setAttribute('aria-pressed', String(choice.dataset.accent === selected));
      });
    };
    updateChoices();

    toggle.addEventListener('click', () => showOptions(options.hidden));
    choices.forEach((choice) => {
      choice.addEventListener('click', () => {
        selected = choice.dataset.accent;
        root.dataset.accent = selected;
        try {
          localStorage.setItem(storageKey, selected);
        } catch (_) {
          // Keep the selection for this page when persistence is blocked.
        }
        updateChoices();
        showOptions(false);
        toggle.focus();
      });
    });
    document.addEventListener('click', (event) => {
      if (!picker.contains(event.target)) showOptions(false);
    });
    picker.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && !options.hidden) {
        showOptions(false);
        toggle.focus();
      }
    });
    picker.addEventListener('focusout', (event) => {
      if (!picker.contains(event.relatedTarget)) showOptions(false);
    });
  });
})();
