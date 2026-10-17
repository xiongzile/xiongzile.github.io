(() => {
  const root = document.getElementById('analytics');
  const status = document.getElementById('analytics-status');
  const number = new Intl.NumberFormat('en');
  const articles = JSON.parse(document.getElementById('analytics-articles').textContent);
  const svgNS = 'http://www.w3.org/2000/svg';
  const set = (id, value) => { document.getElementById(id).textContent = value; };
  const sum = days => days.reduce((total, day) => total + day.views, 0);
  const svg = (tag, attrs, text) => {
    const node = document.createElementNS(svgNS, tag);
    Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value));
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const cell = (row, text) => {
    const node = document.createElement('td');
    node.textContent = text;
    row.append(node);
    return node;
  };

  function render(days, range) {
    const visible = range ? days.slice(-range) : days;
    const chart = document.getElementById('analytics-chart');
    chart.querySelectorAll('g').forEach(node => node.remove());
    const group = svg('g', {});
    const max = Math.max(1, ...visible.map(day => day.views));
    const width = 820 / visible.length;
    group.append(svg('line', { x1: 45, y1: 205, x2: 875, y2: 205, class: 'axis' }));
    group.append(svg('text', { x: 5, y: 22 }, number.format(max)));
    group.append(svg('text', { x: 25, y: 205 }, '0'));
    visible.forEach((day, i) => {
      const height = day.views / max * 180;
      const bar = svg('rect', { x: 50 + i * width, y: 205 - height, width: Math.max(0.5, width * 0.75), height, class: 'bar' });
      bar.append(svg('title', {}, `${day.date}: ${number.format(day.views)} page views`));
      group.append(bar);
    });
    group.append(svg('text', { x: 50, y: 233 }, visible[0].date));
    group.append(svg('text', { x: 870, y: 233, 'text-anchor': 'end' }, visible[visible.length - 1].date));
    chart.append(group);
    set('analytics-chart-desc', `${number.format(sum(visible))} page views over ${visible.length} ${visible.length === 1 ? 'day' : 'days'}. Daily values are available in the table below.`);
    set('analytics-chart-caption', `${number.format(sum(visible))} page views in this period. Hover over a bar for its daily count.`);
    const daily = document.getElementById('analytics-days');
    daily.replaceChildren();
    visible.slice().reverse().forEach(day => {
      const row = document.createElement('tr');
      cell(row, day.date); cell(row, number.format(day.views)); daily.append(row);
    });
    const popular = new Map();
    visible.forEach(day => day.pages.forEach(page => {
      if (Object.hasOwn(articles, page.path)) popular.set(page.path, (popular.get(page.path) || 0) + page.views);
    }));
    const rows = [...popular].filter(([, views]) => views > 0).sort((a, b) => b[1] - a[1]).slice(0, 10);
    const table = document.getElementById('analytics-popular');
    table.replaceChildren();
    rows.forEach(([path, views]) => {
      const row = document.createElement('tr');
      const link = document.createElement('a');
      link.href = path; link.textContent = articles[path];
      cell(row, '').append(link); cell(row, number.format(views)); table.append(row);
    });
    document.getElementById('analytics-popular-empty').hidden = rows.length > 0;
    document.getElementById('analytics-popular-table').hidden = rows.length === 0;
  }

  fetch(root.dataset.source, { cache: 'no-cache' }).then(response => {
    if (!response.ok) throw new Error('Unable to load statistics');
    return response.json();
  }).then(data => {
    if (!data.updatedAt || !data.days.length) {
      status.textContent = 'Tracking has just started. Statistics will appear after the first update.';
      return;
    }
    const today = new Date().toISOString().slice(0, 10);
    const cutoff = new Date(`${today}T00:00:00Z`); cutoff.setUTCDate(cutoff.getUTCDate() - 29);
    const month = cutoff.toISOString().slice(0, 10);
    const days = data.days.slice().sort((a, b) => a.date.localeCompare(b.date));
    set('analytics-start', data.startedAt);
    set('analytics-total', number.format(sum(days)));
    set('analytics-month', number.format(sum(days.filter(day => day.date >= month))));
    set('analytics-today', number.format(sum(days.filter(day => day.date === today))));
    const updated = new Date(data.updatedAt);
    const stale = Date.now() - updated.getTime() > 24 * 60 * 60 * 1000;
    status.textContent = `${stale ? 'Update delayed. Last successful update' : 'Last updated'}: ${updated.toLocaleString('en', { timeZone: 'UTC' })} UTC.`;
    document.getElementById('analytics-results').hidden = false;
    const selector = document.getElementById('analytics-range');
    render(days, Number(selector.value));
    selector.addEventListener('change', () => render(days, Number(selector.value)));
  }).catch(() => {
    status.textContent = 'Statistics are temporarily unavailable. Please try again later.';
  });
})();
