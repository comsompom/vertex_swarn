"""
Spectator node — subscribes to state and E-Stop; feeds dashboard (or logs).
Part of Serve and Protect Bastion (Track 1). No coordination role; observability only.
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


def main():
    parser = argparse.ArgumentParser(description="Bastion spectator (dashboard feed)")
    parser.add_argument("--broker", default=config.MQTT_BROKER, help="Broker host")
    parser.add_argument("--port", type=int, default=config.MQTT_PORT, help="Broker port")
    args = parser.parse_args()

    nodes = {}
    e_stop_at = [None]  # timestamp of last E-Stop

    def on_connect(client, userdata, flags, reason_code, properties=None):
        if reason_code != 0:
            print("[spectator] Connect failed:", reason_code)
            return
        client.subscribe(config.STATE_TOPIC_SUBSCRIBE)
        client.subscribe(config.E_STOP_TOPIC)
        print("[spectator] Connected; listening for state and E-Stop")

    def on_message(client, userdata, msg):
        if msg.topic == config.E_STOP_TOPIC:
            e_stop_at[0] = time.time()
            try:
                payload = json.loads(msg.payload.decode())
                print(f"[spectator] E-STOP from {payload.get('source', '?')} — FLEET FROZEN")
            except Exception:
                print("[spectator] E-STOP — FLEET FROZEN")
            return
        if msg.topic.startswith(f"{config.TOPIC_PREFIX}/state/"):
            try:
                s = json.loads(msg.payload.decode())
                node_id = s.get("node_id", "?")
                nodes[node_id] = {**s, "last_seen": time.time()}
            except Exception:
                pass

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="spectator")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(args.broker, args.port, 60)
    client.loop_start()

    try:
        while True:
            time.sleep(3)
            if nodes:
                print("\n--- Swarm state ---")
                for nid, d in sorted(nodes.items()):
                    age = time.time() - d.get("last_seen", 0)
                    print(f"  {nid}: role={d.get('role')} status={d.get('status')} sector={d.get('sector_id')} battery={d.get('battery')} age={age:.1f}s")
                if e_stop_at[0]:
                    print("  *** FLEET FROZEN (E-Stop active) ***")
                print("---\n")
    except KeyboardInterrupt:
        pass
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
