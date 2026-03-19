"""
Trigger P2P Unstop (resume) for Bastion: one message unfreezes the entire fleet.
Run after e_stop_trigger.py to resume normal operation.
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
    parser = argparse.ArgumentParser(description="Trigger Bastion Unstop (resume fleet)")
    parser.add_argument("--source", default="human-operator")
    parser.add_argument("--reason", default="resume")
    parser.add_argument("--broker", default=config.MQTT_BROKER)
    parser.add_argument("--port", type=int, default=config.MQTT_PORT)
    args = parser.parse_args()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="unstop_trigger")
    client.connect(args.broker, args.port, 60)
    payload = state.make_unstop_payload(args.source, args.reason)
    t0 = time.perf_counter()
    client.publish(config.UNSTOP_TOPIC, json.dumps(payload), qos=1)
    client.disconnect()
    elapsed_ms = (time.perf_counter() - t0) * 1000
    print(f"Unstop sent from {args.source} (reason={args.reason}) in {elapsed_ms:.1f} ms")
    print("All nodes should now be RESUMED.")


if __name__ == "__main__":
    main()
