// The active-section behavior used by MaskRay's side table of contents.
(() => {
  const links = new Map([...document.querySelectorAll('article > .toc-container a')]
    .map(a => [decodeURIComponent(a.hash.slice(1)), a]));
  if (!links.size) return;
  const heads = [...document.querySelectorAll('.e-content :is(h1,h2,h3,h4)[id]')]
    .filter(h => links.has(h.id));
  let current;
  const update = () => {
    let h = heads[0];
    for (const x of heads) if (x.getBoundingClientRect().top < 120) h = x;
    if (h === current) return;
    links.get(current?.id)?.classList.remove('active');
    links.get(h.id).classList.add('active');
    current = h;
  };
  addEventListener('scroll', update, {passive: true});
  update();
})();
