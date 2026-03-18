"""
Flask dashboard for Serve and Protect Bastion — visualizes swarm state and E-Stop.
Subscribes to MQTT state and E-Stop topics; serves a web UI that polls /api/state.
"""

import json
import os
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

from flask import Flask, jsonify, render_template

import config

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


def run_mqtt(broker: str, port: int):
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="bastion-dashboard")
    def on_connect(c, u, flags, rc, props=None):
        if rc == 0:
            c.subscribe(config.STATE_TOPIC_SUBSCRIBE)
            c.subscribe(config.E_STOP_TOPIC)
            c.subscribe(config.AI_SUGGESTIONS_TOPIC)
    client.on_connect = on_connect

    def on_message(client, userdata, msg):
        if msg.topic == config.E_STOP_TOPIC:
            e_stop_at[0] = time.time()
            try:
                e_stop_source[0] = json.loads(msg.payload.decode()).get("source", "?")
            except Exception:
                e_stop_source[0] = "?"
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
