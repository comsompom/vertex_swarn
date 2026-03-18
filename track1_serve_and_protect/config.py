"""
Serve and Protect Bastion — Track 1 solution config.
Wire to Vertex 2.0 / FoxMQ for BUIDL; MQTT broker used here as transport stand-in.
"""

import os

# ---- Transport: FoxMQ (Vertex) or MQTT ----
# For hackathon submission use FoxMQ (Vertex-backed MQTT): run scripts/start_foxmq.py or run_swarm.py --start-broker-foxmq.
# For local demo without FoxMQ: any MQTT broker (e.g. Mosquitto).
MQTT_BROKER = os.environ.get("BASTION_BROKER", "127.0.0.1")
MQTT_PORT = int(os.environ.get("BASTION_MQTT_PORT", "1883"))

# ---- Topics (no central DB; all P2P over pub/sub) ----
TOPIC_PREFIX = "bastion/serve_and_protect"
STATE_TOPIC_TEMPLATE = f"{TOPIC_PREFIX}/state/{{node_id}}"
STATE_TOPIC_SUBSCRIBE = f"{TOPIC_PREFIX}/state/+"
E_STOP_TOPIC = f"{TOPIC_PREFIX}/e_stop"
THREAT_MAP_TOPIC = f"{TOPIC_PREFIX}/threat_map"
AI_SUGGESTIONS_TOPIC = f"{TOPIC_PREFIX}/ai_suggestions"

# ---- Timing ----
HEARTBEAT_INTERVAL = 2.0
PEER_STALE_SECONDS = 6.0
E_STOP_TIMEOUT_MS = 50  # Target: fleet freeze in < 50 ms

# ---- Roles (heterogeneous nodes) ----
ROLE_SENTRY = "sentry"
ROLE_DRONE = "drone"
ROLE_SPECTATOR = "spectator"
STATUS_PATROL = "patrol"
STATUS_RESPONDING = "responding"
STATUS_IDLE = "idle"
STATUS_FROZEN = "frozen"  # E-Stop active

# ---- Default swarm size (run_swarm.py) ----
DEFAULT_SENTRIES = 2
DEFAULT_DRONES = 2

# ---- Flask dashboard ----
DASHBOARD_PORT = int(os.environ.get("BASTION_DASHBOARD_PORT", "5000"))
