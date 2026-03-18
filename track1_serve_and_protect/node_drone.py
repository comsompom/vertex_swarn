"""
Drone node — recon, handoff to sentry when battery low; obeys P2P E-Stop.
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
    parser = argparse.ArgumentParser(description="Bastion drone node")
    parser.add_argument("--id", default="drone-1", help="Node ID")
    parser.add_argument("--broker", default=config.MQTT_BROKER, help="Broker host")
    parser.add_argument("--port", type=int, default=config.MQTT_PORT, help="Broker port")
    parser.add_argument("--battery-drain", type=float, default=2.0, help="Battery % lost per heartbeat")
    args = parser.parse_args()

    node_id = args.id
    battery = [100.0]  # mutable for simulated drain
    frozen = [False]

    def on_connect(client, userdata, flags, reason_code, properties=None):
        if reason_code != 0:
            print(f"[{node_id}] Connect failed: {reason_code}")
            return
        client.subscribe(config.STATE_TOPIC_SUBSCRIBE)
        client.subscribe(config.E_STOP_TOPIC)
        print(f"[{node_id}] Connected (drone)")

    def on_message(client, userdata, msg):
        if msg.topic == config.E_STOP_TOPIC:
            frozen[0] = True
            try:
                payload = json.loads(msg.payload.decode())
                print(f"[{node_id}] E-STOP received from {payload.get('source', '?')} — FROZEN")
            except Exception:
                print(f"[{node_id}] E-STOP received — FROZEN")
            return
        if msg.topic.startswith(f"{config.TOPIC_PREFIX}/state/"):
            try:
                s = json.loads(msg.payload.decode())
                if s.get("node_id") != node_id:
                    pass  # Peer state for handoff logic
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
            bat = max(0, battery[0])
            status = config.STATUS_PATROL if bat > 15 else "low_battery_handoff"
            payload = state.make_state(
                node_id=node_id,
                role=config.ROLE_DRONE,
                status=status,
                sector_id=None,
                battery=int(bat),
            )
            client.publish(
                config.STATE_TOPIC_TEMPLATE.format(node_id=node_id),
                state.state_to_json(payload),
                qos=1,
            )
            if bat <= 0:
                print(f"[{node_id}] Battery depleted — would hand off sector to sentry in full impl")
            else:
                battery[0] -= args.battery_drain
            time.sleep(config.HEARTBEAT_INTERVAL)
    except KeyboardInterrupt:
        pass
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
