(function () {
  'use strict';

  const POLL_MS = 2000;
  const STALE_SEC = 10;

  function render(data) {
    const tbody = document.getElementById('tbody');
    const eStopEl = document.getElementById('e-stop');
    const aiEl = document.getElementById('ai-suggestion');

    if (data.e_stop_active) {
      eStopEl.classList.add('active');
    } else {
      eStopEl.classList.remove('active');
    }

    if (data.last_ai_suggestion && data.last_ai_suggestion.suggestion) {
      aiEl.textContent = 'AI suggestion: ' + data.last_ai_suggestion.suggestion;
      aiEl.style.display = 'block';
    } else {
      aiEl.textContent = '';
      aiEl.style.display = 'none';
    }

    const nodes = data.nodes || [];
    if (nodes.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6">No nodes yet — start the swarm.</td></tr>';
      return;
    }

    const now = Date.now() / 1000;
    tbody.innerHTML = nodes.map(function (n) {
      const age = now - (n.last_seen || 0);
      const stale = age > STALE_SEC;
      const bat = n.battery != null ? n.battery : 100;
      const batClass = bat <= 15 ? 'battery-low' : bat <= 40 ? 'battery-mid' : 'battery-ok';
      const roleClass = n.role === 'sentry' ? 'role-sentry' : n.role === 'drone' ? 'role-drone' : '';
      return (
        '<tr>' +
        '<td>' + (n.node_id || '?') + '</td>' +
        '<td class="' + roleClass + '">' + (n.role || '—') + '</td>' +
        '<td class="' + (stale ? 'status-stale' : '') + '">' + (n.status || '—') + '</td>' +
        '<td>' + (n.sector_id != null ? n.sector_id : '—') + '</td>' +
        '<td class="' + batClass + '">' + (n.battery != null ? n.battery + '%' : '—') + '</td>' +
        '<td class="age">' + (stale ? 'stale ' : '') + age.toFixed(1) + 's ago</td>' +
        '</tr>'
      );
    }).join('');
  }

  function fetchState() {
    fetch('/api/state')
      .then(function (r) { return r.json(); })
      .then(render)
      .catch(function () {});
  }

  fetchState();
  setInterval(fetchState, POLL_MS);
})();
