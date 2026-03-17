"""
Configuration for the Warm Up: Stateful Handshake — Serve and Protect Bastion.
Supports: (1) AirSim + Tashi Vertex (primary), (2) MQTT/FoxMQ (optional, no simulator).
"""

import os

# ---- AirSim + Vertex (primary for Python + Drones) ----
# Drone names must match AirSim settings.json "Vehicles" keys
DRONES = ["Drone1", "Drone2"]
# Path to tashi-vertex-rs repo (must be built: cargo build, with examples drone-comm, key-generate)
TASHI_VERTEX_PATH = os.environ.get("TASHI_VERTEX_PATH", "../tashi-vertex-rs")
TASHI_BASE_PORT = 9500

# ---- Stateful handshake timing ----
HEARTBEAT_INTERVAL = 2.0
PEER_STALE_SECONDS = 5.0
# After this many seconds, Drone1 (Agent A) toggles role to "scout"
ROLE_TOGGLE_AFTER_SECONDS = 15.0

# ---- MQTT (optional path: no AirSim) ----
MQTT_BROKER = os.environ.get("MQTT_BROKER", "127.0.0.1")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
TOPIC_PREFIX = "vertex_warmup/serve_and_protect"
STATE_TOPIC_TEMPLATE = f"{TOPIC_PREFIX}/state/{{peer_id}}"
STATE_TOPIC_SUBSCRIBE = f"{TOPIC_PREFIX}/state/+"

# Drone IDs for MQTT-only scripts (drone_a.py, drone_b.py)
DRONE_A_ID = "drone_a"
DRONE_B_ID = "drone_b"

ROLES = ("scout", "carrier")
STATUSES = ("ready", "busy")
