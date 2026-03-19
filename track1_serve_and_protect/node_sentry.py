"""
Sentry node — patrols a sector, responds to intrusions, obeys P2P E-Stop.
Part of Serve and Protect Bastion (Track 1). Coordination via Vertex/FoxMQ (here: MQTT).
"""

import argparse
import json
import sys
import time

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("Install: pip install paho-mqtt", file=sys.stderr)
    sys.exit(1)

import config
import state


def main():
    parser = argparse.ArgumentParser(description="Bastion sentry node")
    parser.add_argument("--id", default="sentry-1", help="Node ID")
    parser.add_argument("--sector", default="A1", help="Sector ID")
    parser.add_argument("--broker", default=config.MQTT_BROKER, help="Broker host")
    parser.add_argument("--port", type=int, default=config.MQTT_PORT, help="Broker port")
    args = parser.parse_args()

    node_id = args.id
    sector_id = args.sector
    frozen = [False]  # mutable so callback can set it

    def on_connect(client, userdata, flags, reason_code, properties=None):
        if reason_code != 0:
            print(f"[{node_id}] Connect failed: {reason_code}")
            return
        client.subscribe(config.STATE_TOPIC_SUBSCRIBE)
        client.subscribe(config.E_STOP_TOPIC)
        client.subscribe(config.UNSTOP_TOPIC)
        print(f"[{node_id}] Connected; sector={sector_id}")

    def on_message(client, userdata, msg):
        if msg.topic == config.E_STOP_TOPIC:
            frozen[0] = True
            try:
                payload = json.loads(msg.payload.decode())
                print(f"[{node_id}] E-STOP received from {payload.get('source', '?')} — FROZEN")
            except Exception:
                print(f"[{node_id}] E-STOP received — FROZEN")
            return
        if msg.topic == config.UNSTOP_TOPIC:
            frozen[0] = False
            try:
                payload = json.loads(msg.payload.decode())
                print(f"[{node_id}] UNSTOP received from {payload.get('source', '?')} — RESUMED")
            except Exception:
                print(f"[{node_id}] UNSTOP received — RESUMED")
            return
        # State from peers (optional: merge into local view)
        if msg.topic.startswith(f"{config.TOPIC_PREFIX}/state/"):
            try:
                s = json.loads(msg.payload.decode())
                if s.get("node_id") != node_id:
                    pass  # Could merge into CRDT threat map
            except Exception:
                pass

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=node_id)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(args.broker, args.port, 60)
    client.loop_start()

    try:
        while True:
            if frozen[0]:
                time.sleep(0.5)
                continue
            payload = state.make_state(
                node_id=node_id,
                role=config.ROLE_SENTRY,
                status=config.STATUS_PATROL,
                sector_id=sector_id,
                battery=100,
            )
            client.publish(
                config.STATE_TOPIC_TEMPLATE.format(node_id=node_id),
                state.state_to_json(payload),
                qos=1,
            )
            time.sleep(config.HEARTBEAT_INTERVAL)
    except KeyboardInterrupt:
        pass
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
