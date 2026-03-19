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

  function formatActionsForUser(actions) {
    if (!actions || !actions.length) return '';
    var lines = [];
    actions.forEach(function (a) {
      if (a.type === 'handoff' && a.from && a.to) {
        lines.push('• Hand off ' + a.from + ' to ' + a.to + (a.sector ? ' (sector ' + a.sector + ')' : ''));
      } else if (a.type === 'rebalance' && a.sectors && a.sectors.length) {
        lines.push('• Rebalance sectors: ' + a.sectors.join(', ') + ' — consider moving one sentry to another sector.');
      } else if (a.type === 'add_sentry' && a.sectors && a.sectors.length) {
        lines.push('• Add or assign a sentry to cover: ' + a.sectors.join(', '));
      } else if (a.type === 'check_node' && a.node_id) {
        lines.push('• Check or restart node: ' + a.node_id + ' (no recent heartbeat).');
      } else {
        lines.push('• ' + (a.type || 'Action') + (a.sectors ? ': ' + a.sectors.join(', ') : ''));
      }
    });
    return lines.join('\n');
  }

  function strategyLabel(name) {
    var labels = { auto: 'Auto', handoff: 'Low-battery handoff', rebalance: 'Sector rebalance', stale: 'Stale node recovery', openai: 'OpenAI tactical' };
    return labels[name] || name;
  }

  function runAiControl() {
    var strategyEl = document.getElementById('ai-strategy');
    var resultEl = document.getElementById('ai-control-result');
    var btn = document.getElementById('btn-ai-control');
    if (!resultEl || !btn) return;
    var strategy = strategyEl && strategyEl.value ? strategyEl.value : 'auto';
    resultEl.innerHTML = '<span class="result-label">Running…</span>';
    resultEl.className = 'ai-control-result loading';
    resultEl.style.display = 'block';
    btn.disabled = true;
    fetch('/api/ai-control', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ strategy: strategy })
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.ok && data.recommendation != null) {
          var strategyUsed = data.strategy_used || data.strategy || '';
          var parts = [];
          parts.push('<span class="result-label">Strategy used</span> ' + strategyLabel(strategyUsed));
          parts.push('<span class="result-label">What it means</span> ' + escapeHtml(data.recommendation));
          var actionsText = formatActionsForUser(data.actions);
          if (actionsText) {
            parts.push('<span class="result-label">Suggested actions</span>\n' + escapeHtml(actionsText));
          }
          resultEl.innerHTML = parts.join('\n');
          resultEl.className = 'ai-control-result';
        } else {
          resultEl.textContent = data.error || 'Failed to run strategy';
          resultEl.className = 'ai-control-result error';
        }
      })
      .catch(function () {
        resultEl.textContent = 'Request failed';
        resultEl.className = 'ai-control-result error';
      })
      .finally(function () {
        btn.disabled = false;
      });
  }

  function escapeHtml(text) {
    var div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function showFleetMessage(text, isError) {
    var el = document.getElementById('fleet-message');
    if (!el) return;
    el.textContent = text;
    el.classList.toggle('error', !!isError);
    if (text) {
      setTimeout(function () { el.textContent = ''; }, 5000);
    }
  }

  function triggerEStop() {
    var btn = document.getElementById('btn-e-stop');
    if (btn) btn.disabled = true;
    fetch('/api/fleet/e-stop', { method: 'POST' })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.ok) {
          showFleetMessage('E-Stop sent; fleet frozen.', false);
          fetchState();
        } else {
          showFleetMessage(data.error || 'E-Stop failed', true);
        }
      })
      .catch(function () { showFleetMessage('Request failed', true); })
      .finally(function () { if (btn) btn.disabled = false; });
  }

  function triggerUnstop() {
    var btn = document.getElementById('btn-unstop');
    if (btn) btn.disabled = true;
    fetch('/api/fleet/unstop', { method: 'POST' })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.ok) {
          showFleetMessage('Unstop sent; fleet resumed.', false);
          fetchState();
        } else {
          showFleetMessage(data.error || 'Unstop failed', true);
        }
      })
      .catch(function () { showFleetMessage('Request failed', true); })
      .finally(function () { if (btn) btn.disabled = false; });
  }

  function triggerChaosMonkey() {
    var btn = document.getElementById('btn-chaos');
    if (btn) btn.disabled = true;
    fetch('/api/fleet/chaos-monkey', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ kill: 2 })
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.ok) {
          var msg = data.message || 'Chaos monkey ran (kill 2).';
          if (data.output) msg += ' ' + data.output;
          showFleetMessage(msg, false);
          fetchState();
        } else {
          showFleetMessage(data.error || 'Chaos monkey failed', true);
        }
      })
      .catch(function () { showFleetMessage('Request failed', true); })
      .finally(function () { if (btn) btn.disabled = false; });
  }

  (function bindControls() {
    var btnDrone = document.getElementById('btn-add-drone');
    var btnSentry = document.getElementById('btn-add-sentry');
    if (btnDrone) btnDrone.addEventListener('click', function () { addNodes('drone'); });
    if (btnSentry) btnSentry.addEventListener('click', function () { addNodes('sentry'); });
    var btnAi = document.getElementById('btn-ai-control');
    if (btnAi) btnAi.addEventListener('click', runAiControl);
    var btnEStop = document.getElementById('btn-e-stop');
    if (btnEStop) btnEStop.addEventListener('click', triggerEStop);
    var btnUnstop = document.getElementById('btn-unstop');
    if (btnUnstop) btnUnstop.addEventListener('click', triggerUnstop);
    var btnChaos = document.getElementById('btn-chaos');
    if (btnChaos) btnChaos.addEventListener('click', triggerChaosMonkey);
  })();

  fetchState();
  setInterval(fetchState, POLL_MS);
})();
