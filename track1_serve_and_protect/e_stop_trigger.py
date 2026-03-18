"""
Trigger P2P E-Stop for demo: one message freezes the entire fleet.
Run while swarm is running to demonstrate fleet freeze in under 50 ms.
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
    parser = argparse.ArgumentParser(description="Trigger Bastion E-Stop")
    parser.add_argument("--source", default="human-operator")
    parser.add_argument("--reason", default="hold_fire")
    parser.add_argument("--broker", default=config.MQTT_BROKER)
    parser.add_argument("--port", type=int, default=config.MQTT_PORT)
    args = parser.parse_args()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="e_stop_trigger")
    client.connect(args.broker, args.port, 60)
    payload = state.make_e_stop_payload(args.source, args.reason)
    t0 = time.perf_counter()
    client.publish(config.E_STOP_TOPIC, json.dumps(payload), qos=1)
    client.disconnect()
    elapsed_ms = (time.perf_counter() - t0) * 1000
    print(f"E-Stop sent from {args.source} (reason={args.reason}) in {elapsed_ms:.1f} ms")
    print("All nodes should now be FROZEN.")


if __name__ == "__main__":
    main()
