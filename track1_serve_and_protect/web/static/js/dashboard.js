(function () {
  'use strict';

  const POLL_MS = 2000;
  const STALE_SEC = 10;

  function render(data) {
    const tbody = document.getElementById('tbody');
    const eStopModal = document.getElementById('e-stop-modal');
    const aiEl = document.getElementById('ai-suggestion');

    if (data.e_stop_active && eStopModal) {
      eStopModal.removeAttribute('hidden');
    } else if (eStopModal) {
      eStopModal.setAttribute('hidden', '');
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

  function formatLogTime(ts) {
    if (ts == null) return '—';
    var d = new Date(ts * 1000);
    return d.toLocaleTimeString() + ' ' + d.toLocaleDateString();
  }

  function openLogsModal() {
    var modal = document.getElementById('logs-modal');
    var listEl = document.getElementById('logs-list');
    if (!modal || !listEl) return;
    fetch('/api/logs')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var logs = (data.logs || []);
        if (logs.length === 0) {
          listEl.innerHTML = '<p class="log-entry">No log entries yet.</p>';
        } else {
          listEl.innerHTML = logs.map(function (e) {
            return '<div class="log-entry"><span class="log-ts">' + escapeHtml(formatLogTime(e.ts)) + '</span> <span class="log-msg">' + escapeHtml(e.message || '') + '</span></div>';
          }).join('');
        }
        modal.removeAttribute('hidden');
      })
      .catch(function () {
        listEl.innerHTML = '<p class="log-entry">Failed to load logs.</p>';
        modal.removeAttribute('hidden');
      });
  }

  function closeLogsModal() {
    var modal = document.getElementById('logs-modal');
    if (modal) modal.setAttribute('hidden', '');
  }

  (function bindControls() {
    var btnDrone = document.getElementById('btn-add-drone');
    var btnSentry = document.getElementById('btn-add-sentry');
    if (btnDrone) btnDrone.addEventListener('click', function () { addNodes('drone'); });
    if (btnSentry) btnSentry.addEventListener('click', function () { addNodes('sentry'); });
    var btnAi = document.getElementById('btn-ai-control');
    if (btnAi) btnAi.addEventListener('click', runAiControl);
    var btnLogs = document.getElementById('btn-logs');
    if (btnLogs) btnLogs.addEventListener('click', openLogsModal);
    var logsClose = document.getElementById('logs-modal-close');
    if (logsClose) logsClose.addEventListener('click', closeLogsModal);
    var logsOverlay = document.getElementById('logs-modal');
    if (logsOverlay) logsOverlay.addEventListener('click', function (e) {
      if (e.target === logsOverlay) closeLogsModal();
    });
  })();

  fetchState();
  setInterval(fetchState, POLL_MS);
})();
