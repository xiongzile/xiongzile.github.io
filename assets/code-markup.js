// Adapt Jekyll/Rouge markup to tabi's existing code-block selectors.
document.querySelectorAll('.highlighter-rouge pre').forEach(function (pre) {
  pre.classList.add('z-code');
  var wrapper = pre.closest('.highlighter-rouge');
  var language = Array.from(wrapper.classList).find(function (name) {
    return name.startsWith('language-');
  });
  if (language) pre.querySelector('code').setAttribute('data-lang', language.slice(9));
});
