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

  function showAddMessage(text, isError) {
    var el = document.getElementById('add-message');
    if (!el) return;
    el.textContent = text;
    el.classList.toggle('error', !!isError);
    if (text) {
      setTimeout(function () { el.textContent = ''; }, 5000);
    }
  }

  function addNodes(role) {
    var countEl = document.getElementById('add-count');
    var count = 1;
    if (countEl) {
      var n = parseInt(countEl.value, 10);
      if (!isNaN(n) && n >= 1 && n <= 20) count = n;
    }
    var btn = role === 'drone' ? document.getElementById('btn-add-drone') : document.getElementById('btn-add-sentry');
    if (btn) btn.disabled = true;
    fetch('/api/nodes/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role: role, count: count })
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.ok && data.added && data.added.length) {
          var names = data.added.map(function (a) { return a.node_id; }).join(', ');
          showAddMessage('Added: ' + names, false);
          fetchState();
        } else {
          showAddMessage(data.error || 'Failed to add node', true);
        }
      })
      .catch(function () {
        showAddMessage('Request failed', true);
      })
      .finally(function () {
        if (btn) btn.disabled = false;
      });
  }

  (function bindControls() {
    var btnDrone = document.getElementById('btn-add-drone');
    var btnSentry = document.getElementById('btn-add-sentry');
    if (btnDrone) btnDrone.addEventListener('click', function () { addNodes('drone'); });
    if (btnSentry) btnSentry.addEventListener('click', function () { addNodes('sentry'); });
  })();

  fetchState();
  setInterval(fetchState, POLL_MS);
})();
