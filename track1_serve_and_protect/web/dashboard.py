"""
Flask dashboard for Serve and Protect Bastion — visualizes swarm state and E-Stop.
Subscribes to MQTT state and E-Stop topics; serves a web UI that polls /api/state.
Supports adding drones and sentries from the UI (POST /api/nodes/add).
"""

import json
import os
import re
import subprocess
import sys
import threading
import time

# Ensure parent (track1_serve_and_protect) is on path for config
_web_dir = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_web_dir)
if _root not in sys.path:
    sys.path.insert(0, _root)

try:
    import paho.mqtt.client as mqtt
except ImportError:
    raise SystemExit("Install paho-mqtt: pip install paho-mqtt")

from flask import Flask, jsonify, render_template, request

import config
from web.strategies import run_strategy, STRATEGIES

# Sectors for sentries (cycle when adding from UI)
SECTORS = ["A1", "A2", "A3", "B1", "B2"]
# Spawned PIDs (for reference; optional future "stop" feature)
_spawned_pids = []

# Flask app: templates and static live under web/ for a clean separation
app = Flask(
    __name__,
    template_folder=os.path.join(_web_dir, "templates"),
    static_folder=os.path.join(_web_dir, "static"),
)

# Shared state (updated by MQTT callback)
nodes = {}
e_stop_at = [None]  # timestamp or None
e_stop_source = [None]
last_ai_suggestion = [None]  # { "node_id", "ts_ms", "suggestion" } or None

# Operation logs (add_node, ai_control, e_stop, unstop) — thread-safe
_operation_logs = []
_logs_lock = threading.Lock()
_MAX_LOGS = 200


def _log(op_type: str, message: str):
    """Append a log entry (thread-safe)."""
    with _logs_lock:
        _operation_logs.append({
            "ts": time.time(),
            "type": op_type,
            "message": message,
        })
        while len(_operation_logs) > _MAX_LOGS:
            _operation_logs.pop(0)


def run_mqtt(broker: str, port: int):
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="bastion-dashboard")
    def on_connect(c, u, flags, rc, props=None):
        if rc == 0:
            c.subscribe(config.STATE_TOPIC_SUBSCRIBE)
            c.subscribe(config.E_STOP_TOPIC)
            c.subscribe(config.UNSTOP_TOPIC)
            c.subscribe(config.AI_SUGGESTIONS_TOPIC)
    client.on_connect = on_connect

    def on_message(client, userdata, msg):
        if msg.topic == config.E_STOP_TOPIC:
            e_stop_at[0] = time.time()
            try:
                src = json.loads(msg.payload.decode()).get("source", "?")
                e_stop_source[0] = src
                _log("e_stop", f"E-Stop received from {src} — fleet frozen")
            except Exception:
                e_stop_source[0] = "?"
                _log("e_stop", "E-Stop received — fleet frozen")
            return
        if msg.topic == config.UNSTOP_TOPIC:
            e_stop_at[0] = None
            e_stop_source[0] = None
            _log("unstop", "Unstop received — fleet resumed")
            return
        if msg.topic == config.AI_SUGGESTIONS_TOPIC:
            try:
                last_ai_suggestion[0] = json.loads(msg.payload.decode())
            except Exception:
                pass
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
    return render_template(
        "dashboard.html",
        broker=config.MQTT_BROKER,
        port=config.MQTT_PORT,
    )


def _next_node_ids(role: str, count: int) -> list[tuple[str, str]]:
    """Compute next `count` node_ids (and sector for sentry). Returns [(node_id, sector), ...]."""
    prefix = "sentry" if role == "sentry" else "drone"
    indices = []
    for nid in nodes:
        m = re.match(rf"^{prefix}-(\d+)$", nid)
        if m:
            indices.append(int(m.group(1)))
    start = max(indices, default=0) + 1
    out = []
    for i in range(count):
        idx = start + i
        node_id = f"{prefix}-{idx}"
        sector = SECTORS[(idx - 1) % len(SECTORS)] if role == "sentry" else ""
        out.append((node_id, sector))
    return out


def _spawn_node(role: str, node_id: str, sector: str) -> subprocess.Popen | None:
    """Spawn node_drone.py or node_sentry.py as subprocess. Returns Popen or None on failure."""
    broker = config.MQTT_BROKER
    port = config.MQTT_PORT
    if role == "drone":
        cmd = [sys.executable, os.path.join(_root, "node_drone.py"), "--id", node_id, "--broker", broker, "--port", str(port)]
    else:
        cmd = [sys.executable, os.path.join(_root, "node_sentry.py"), "--id", node_id, "--sector", sector, "--broker", broker, "--port", str(port)]
    try:
        proc = subprocess.Popen(cmd, cwd=_root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        _spawned_pids.append(proc.pid)
        return proc
    except Exception:
        return None


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
        "last_ai_suggestion": last_ai_suggestion[0],
    })


@app.route("/api/nodes/add", methods=["POST"])
def api_nodes_add():
    """Add one or more drone/sentry nodes. Body: { "role": "drone"|"sentry", "count": 1 }."""
    if request.method != "POST":
        return jsonify({"ok": False, "error": "Method not allowed"}), 405
    try:
        data = request.get_json(force=True, silent=True) or {}
        role = (data.get("role") or "").strip().lower()
        if role not in ("drone", "sentry"):
            return jsonify({"ok": False, "error": "role must be 'drone' or 'sentry'"}), 400
        count = max(1, min(int(data.get("count", 1)), 20))
    except (ValueError, TypeError):
        return jsonify({"ok": False, "error": "count must be an integer 1–20"}), 400

    ids_and_sectors = _next_node_ids(role, count)
    added = []
    for node_id, sector in ids_and_sectors:
        proc = _spawn_node(role, node_id, sector)
        if proc is None:
            return jsonify({"ok": False, "error": f"Failed to spawn {node_id}", "added": added}), 500
        added.append({"node_id": node_id, "role": role, "pid": proc.pid})
    names = ", ".join(a["node_id"] for a in added)
    _log("add_node", f"Added {len(added)} {role}(s): {names}")
    return jsonify({"ok": True, "added": added})


@app.route("/api/ai-control", methods=["GET", "POST"])
def api_ai_control():
    """
    AI Control: run a drone/sentry control strategy on current swarm state.
    GET: list available strategies.
    POST: body { "strategy": "handoff"|"rebalance"|"stale"|"openai"|"auto" }; run and return recommendation.
    Optionally publishes result to AI_SUGGESTIONS_TOPIC so the mesh sees it.
    """
    if request.method == "GET":
        return jsonify({
            "ok": True,
            "strategies": [
                {"id": k, "label": v[0]} for k, v in STRATEGIES.items()
            ],
        })

    try:
        data = request.get_json(force=True, silent=True) or {}
        strategy_name = (data.get("strategy") or "auto").strip().lower()
    except Exception:
        strategy_name = "auto"

    result = run_strategy(strategy_name, nodes)
    if not result.get("ok"):
        return jsonify(result), 400

    rec = (result.get("recommendation") or "")[:80]
    _log("ai_control", f"AI Control: {strategy_name} — {rec or 'ok'}")

    # Publish to mesh so other nodes (and dashboard) can see this recommendation
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="bastion-dashboard-ai-control")
        client.connect(config.MQTT_BROKER, config.MQTT_PORT, 60)
        payload = {
            "node_id": "dashboard-ai-control",
            "ts_ms": int(time.time() * 1000),
            "suggestion": result.get("recommendation", ""),
            "strategy": strategy_name,
            "actions": result.get("actions", []),
        }
        client.publish(config.AI_SUGGESTIONS_TOPIC, json.dumps(payload), qos=1)
        client.disconnect()
    except Exception:
        pass  # don't fail the API if publish fails

    return jsonify(result)


@app.route("/api/logs")
def api_logs():
    """Return recent operation logs (newest first)."""
    with _logs_lock:
        entries = list(_operation_logs)
    # Newest last in list; reverse so newest first for display
    entries.reverse()
    return jsonify({
        "ok": True,
        "logs": [{"ts": e["ts"], "type": e["type"], "message": e["message"]} for e in entries],
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
