(() => {
  const root = document.getElementById('analytics');
  const status = document.getElementById('analytics-status');
  const number = new Intl.NumberFormat('en');
  const articles = JSON.parse(document.getElementById('analytics-articles').textContent);
  const svgNS = 'http://www.w3.org/2000/svg';
  const set = (id, value) => { document.getElementById(id).textContent = value; };
  const sum = days => days.reduce((total, day) => total + day.views, 0);
  const shortDate = value => new Date(`${value}T00:00:00Z`).toLocaleDateString('en', { month: 'short', day: 'numeric', timeZone: 'UTC' });
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

  function drawChart(visible) {
    const chart = document.getElementById('analytics-chart');
    const width = Math.max(260, chart.clientWidth);
    const height = chart.clientHeight;
    const left = 32, right = width - 10, top = 12, bottom = height - 27;
    chart.setAttribute('viewBox', `0 0 ${width} ${height}`);
    chart.querySelectorAll('g').forEach(node => node.remove());
    const group = svg('g', {});
    const maximum = Math.max(2, ...visible.map(day => day.views));
    const max = maximum <= 10 ? Math.ceil(maximum / 2) * 2 : Math.ceil(maximum / 10) * 10;
    [0, max / 2, max].forEach(value => {
      const y = bottom - value / max * (bottom - top);
      group.append(svg('line', { x1: left, y1: y, x2: right, y2: y, class: 'grid' }));
      group.append(svg('text', { x: left - 10, y: y + 4, 'text-anchor': 'end' }, number.format(value)));
    });
    const points = visible.map((day, i) => ({
      x: visible.length === 1 ? (left + right) / 2 : left + i / (visible.length - 1) * (right - left),
      y: bottom - day.views / max * (bottom - top), day
    }));
    if (points.length > 1) {
      const line = points.map((point, i) => `${i ? 'L' : 'M'} ${point.x} ${point.y}`).join(' ');
      group.append(svg('path', { d: `${line} L ${right} ${bottom} L ${left} ${bottom} Z`, class: 'area' }));
      group.append(svg('path', { d: line, class: 'trend' }));
    }
    points.forEach(point => {
      const hit = svg('circle', { cx: point.x, cy: point.y, r: visible.length > 60 ? 4 : 7, fill: 'transparent' });
      hit.append(svg('title', {}, `${point.day.date}: ${number.format(point.day.views)} page views`));
      group.append(hit);
      if (visible.length <= 30) group.append(svg('circle', { cx: point.x, cy: point.y, r: visible.length === 1 ? 3.5 : 2.5, class: 'point', 'pointer-events': 'none' }));
    });
    if (visible.length === 1) {
      group.append(svg('text', { x: points[0].x, y: height - 4, 'text-anchor': 'middle' }, shortDate(visible[0].date)));
    } else {
      group.append(svg('text', { x: left, y: height - 4 }, shortDate(visible[0].date)));
      group.append(svg('text', { x: right, y: height - 4, 'text-anchor': 'end' }, shortDate(visible[visible.length - 1].date)));
    }
    chart.append(group);
  }

  function render(days, range) {
    const visible = range ? days.slice(-range) : days;
    const description = `${number.format(sum(visible))} page views over ${visible.length} ${visible.length === 1 ? 'day' : 'days'}.`;
    set('analytics-chart-desc', `${description} Daily values are available in the table below.`);
    set('analytics-chart-caption', description);
    set('analytics-period', range ? `Last ${range} days` : 'All time');
    drawChart(visible);
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
    return visible;
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
    set('analytics-start-note', data.startedAt);
    set('analytics-total', number.format(sum(days)));
    set('analytics-month', number.format(sum(days.filter(day => day.date >= month))));
    set('analytics-today', number.format(sum(days.filter(day => day.date === today))));
    const updated = new Date(data.updatedAt);
    const stale = Date.now() - updated.getTime() > 24 * 60 * 60 * 1000;
    const stamp = updated.toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'UTC' });
    status.textContent = `${stale ? 'Update delayed · Last updated' : 'Updated'} ${stamp} UTC`;
    document.getElementById('analytics-results').hidden = false;
    let visible = render(days, 30);
    const buttons = root.querySelectorAll('[data-range]');
    buttons.forEach(button => button.addEventListener('click', () => {
      buttons.forEach(item => item.setAttribute('aria-pressed', String(item === button)));
      visible = render(days, Number(button.dataset.range));
    }));
    new ResizeObserver(() => drawChart(visible)).observe(document.getElementById('analytics-chart'));
  }).catch(() => {
    status.textContent = 'Statistics are temporarily unavailable. Please try again later.';
  });
})();
