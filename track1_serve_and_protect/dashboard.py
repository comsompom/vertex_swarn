"""
Flask dashboard for Serve and Protect Bastion — visualizes swarm state and E-Stop.
Subscribes to MQTT state and E-Stop topics; serves a web UI that polls /api/state.
"""

import json
import threading
import time

try:
    import paho.mqtt.client as mqtt
except ImportError:
    raise SystemExit("Install paho-mqtt: pip install paho-mqtt")

from flask import Flask, jsonify, render_template_string

import config

app = Flask(__name__)

# Shared state (updated by MQTT callback)
nodes = {}
e_stop_at = [None]  # timestamp or None
e_stop_source = [None]

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Serve and Protect Bastion — Swarm Dashboard</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: system-ui, sans-serif; margin: 0; padding: 1rem; background: #0f1419; color: #e6edf3; }
    h1 { margin: 0 0 0.5rem; font-size: 1.5rem; }
    .subtitle { color: #8b949e; font-size: 0.9rem; margin-bottom: 1rem; }
    .e-stop-banner {
      display: none;
      background: #da3636; color: #fff; padding: 0.75rem 1rem; border-radius: 6px;
      font-weight: 600; margin-bottom: 1rem; text-align: center;
    }
    .e-stop-banner.active { display: block; }
    table { width: 100%; border-collapse: collapse; background: #161b22; border-radius: 8px; overflow: hidden; }
    th, td { padding: 0.6rem 1rem; text-align: left; border-bottom: 1px solid #21262d; }
    th { background: #21262d; color: #8b949e; font-weight: 600; font-size: 0.85rem; }
    tr:last-child td { border-bottom: none; }
    .role-sentry { color: #7ee787; }
    .role-drone { color: #79c0ff; }
    .status-stale { color: #f85149; }
    .battery-low { color: #f85149; }
    .battery-mid { color: #d29922; }
    .battery-ok { color: #7ee787; }
    .age { font-size: 0.85rem; color: #8b949e; }
    footer { margin-top: 1.5rem; font-size: 0.8rem; color: #8b949e; }
  </style>
</head>
<body>
  <h1>Serve and Protect Bastion</h1>
  <p class="subtitle">Track 1 — Swarm coordination dashboard (live from MQTT)</p>
  <div id="e-stop" class="e-stop-banner">FLEET FROZEN — E-Stop active</div>
  <table>
    <thead>
      <tr>
        <th>Node</th>
        <th>Role</th>
        <th>Status</th>
        <th>Sector</th>
        <th>Battery</th>
        <th>Last seen</th>
      </tr>
    </thead>
    <tbody id="tbody"></tbody>
  </table>
  <footer>Data refreshes every 2s from MQTT. Broker: {{ broker }}:{{ port }}</footer>
  <script>
    const POLL_MS = 2000;
    const STALE_SEC = 10;
    function render(data) {
      const tbody = document.getElementById('tbody');
      const eStopEl = document.getElementById('e-stop');
      if (data.e_stop_active) eStopEl.classList.add('active'); else eStopEl.classList.remove('active');
      const nodes = data.nodes || [];
      if (nodes.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6">No nodes yet — start the swarm.</td></tr>';
        return;
      }
      const now = Date.now() / 1000;
      tbody.innerHTML = nodes.map(n => {
        const age = now - (n.last_seen || 0);
        const stale = age > STALE_SEC;
        const bat = n.battery != null ? n.battery : 100;
        const batClass = bat <= 15 ? 'battery-low' : bat <= 40 ? 'battery-mid' : 'battery-ok';
        const roleClass = n.role === 'sentry' ? 'role-sentry' : n.role === 'drone' ? 'role-drone' : '';
        return '<tr>' +
          '<td>' + (n.node_id || '?') + '</td>' +
          '<td class="' + roleClass + '">' + (n.role || '—') + '</td>' +
          '<td class="' + (stale ? 'status-stale' : '') + '">' + (n.status || '—') + '</td>' +
          '<td>' + (n.sector_id != null ? n.sector_id : '—') + '</td>' +
          '<td class="' + batClass + '">' + (n.battery != null ? n.battery + '%' : '—') + '</td>' +
          '<td class="age">' + (stale ? 'stale ' : '') + age.toFixed(1) + 's ago</td>' +
          '</tr>';
      }).join('');
    }
    function fetchState() {
      fetch('/api/state').then(r => r.json()).then(render).catch(() => {});
    }
    fetchState();
    setInterval(fetchState, POLL_MS);
  </script>
</body>
</html>
"""


def run_mqtt(broker: str, port: int):
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="bastion-dashboard")
    client.on_connect = lambda c, u, flags, rc, props: (
        c.subscribe(config.STATE_TOPIC_SUBSCRIBE),
        c.subscribe(config.E_STOP_TOPIC),
    ) if rc == 0 else None

    def on_message(client, userdata, msg):
        if msg.topic == config.E_STOP_TOPIC:
            e_stop_at[0] = time.time()
            try:
                e_stop_source[0] = json.loads(msg.payload.decode()).get("source", "?")
            except Exception:
                e_stop_source[0] = "?"
            return
        if msg.topic.startswith(f"{config.TOPIC_PREFIX}/state/"):
            try:
                s = json.loads(msg.payload.decode())
                node_id = s.get("node_id", "?")
                nodes[node_id] = {**s, "last_seen": time.time()}
            except Exception:
                pass

    client.on_message = on_message
    client.connect(broker, port, 60)
    client.loop_forever()


@app.route("/")
def index():
    return render_template_string(
        HTML_TEMPLATE,
        broker=config.MQTT_BROKER,
        port=config.MQTT_PORT,
    )


@app.route("/api/state")
def api_state():
    now = time.time()
    node_list = [
        {**data, "last_seen": data.get("last_seen", 0)}
        for _, data in sorted(nodes.items())
    ]
    return jsonify({
        "nodes": node_list,
        "e_stop_active": e_stop_at[0] is not None,
        "e_stop_source": e_stop_source[0],
    })


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Bastion Flask dashboard")
    parser.add_argument("--broker", default=config.MQTT_BROKER)
    parser.add_argument("--port", type=int, default=getattr(config, "DASHBOARD_PORT", 5000))
    parser.add_argument("--mqtt-port", type=int, default=config.MQTT_PORT)
    args = parser.parse_args()

    thread = threading.Thread(target=run_mqtt, args=(args.broker, args.mqtt_port), daemon=True)
    thread.start()
    time.sleep(0.5)  # allow first connect

    print(f"Dashboard: http://127.0.0.1:{args.port}")
    print(f"MQTT: {args.broker}:{args.mqtt_port}")
    app.run(host="0.0.0.0", port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
