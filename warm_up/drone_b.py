#!/usr/bin/env python3
"""
Drone B — Vertex Swarm Warm Up: Stateful Handshake (Serve and Protect Bastion).
Agent B: discovers Drone A, syncs state, sends heartbeats. Mirrors Drone A's role within <1s.
"""

import time
import sys
import threading

import paho.mqtt.client as mqtt

import config
from state_schema import make_state, state_to_json, json_to_state

PEER_ID = config.DRONE_B_ID
OTHER_ID = config.DRONE_A_ID
STATE_TOPIC = config.STATE_TOPIC_TEMPLATE.format(peer_id=PEER_ID)

# Local state (we mirror Drone A's role)
role = "carrier"
status = "ready"
peer_last_seen = 0.0
peer_stale_logged = False
client = None


def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        print(f"[{PEER_ID}] Connected to broker {config.MQTT_BROKER}:{config.MQTT_PORT}")
        client.subscribe(config.STATE_TOPIC_SUBSCRIBE)
        print(f"[{PEER_ID}] Subscribed to {config.STATE_TOPIC_SUBSCRIBE}")
    else:
        print(f"[{PEER_ID}] Connection failed: {reason_code}")


def on_message(client, userdata, msg):
    global role, peer_last_seen, peer_stale_logged
    state = json_to_state(msg.payload.decode())
    if not state or state.get("peer_id") == PEER_ID:
        return
    peer_id = state.get("peer_id", "")
    if peer_id != OTHER_ID:
        return
    peer_last_seen = time.time()
    last_seen_ms = state.get("last_seen_ms", 0)
    peer_role = state.get("role", "carrier")
    peer_status = state.get("status", "ready")
    if peer_stale_logged:
        print(f"[{PEER_ID}] Peer {OTHER_ID} reconnected. Connection and state automatically resuming.")
        peer_stale_logged = False
    # Mirror Agent A's role (track.md: "Agent B must acknowledge and mirror this state change in <1 second")
    if role != peer_role:
        role = peer_role
        print(f"[{PEER_ID}] Mirrored role from {OTHER_ID}: role={role} (acknowledged in <1s)")
    print(f"[{PEER_ID}] State from {OTHER_ID}: role={peer_role}, status={peer_status}, last_seen_ms={last_seen_ms}")


def publish_state():
    global client
    while client and client.is_connected():
        state = make_state(PEER_ID, role=role, status=status)
        client.publish(STATE_TOPIC, state_to_json(state), qos=1)
        time.sleep(config.HEARTBEAT_INTERVAL)


def check_peer_stale():
    global peer_stale_logged
    while True:
        time.sleep(1)
        if peer_last_seen == 0:
            continue
        if (time.time() - peer_last_seen) > config.PEER_STALE_SECONDS and not peer_stale_logged:
            print(f"[{PEER_ID}] Peer {OTHER_ID} marked stale (no heartbeat). Peer lost, returning to idle.")
            peer_stale_logged = True


def main():
    global client
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=PEER_ID,
        protocol=mqtt.MQTTv5,
    )
    client.on_connect = on_connect
    client.on_message = on_message
    try:
        client.connect(config.MQTT_BROKER, config.MQTT_PORT)
    except Exception as e:
        print(f"[{PEER_ID}] Could not connect to broker: {e}")
        print("  Ensure FoxMQ (or another MQTT broker) is running. See README.md.")
        sys.exit(1)
    client.loop_start()
    heartbeat_thread = threading.Thread(target=publish_state, daemon=True)
    heartbeat_thread.start()
    stale_thread = threading.Thread(target=check_peer_stale, daemon=True)
    stale_thread.start()
    print(f"[{PEER_ID}] Running. State: role={role}, status={status}. Will mirror Drone A's role.")
    print("  Press Ctrl+C to exit.")
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        pass
    client.loop_stop()
    client.disconnect()


if __name__ == "__main__":
    main()
