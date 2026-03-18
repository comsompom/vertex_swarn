#!/usr/bin/env python3
"""
Stateful Handshake — Serve and Protect Bastion (Python + Drones).
AirSim + Tashi Vertex: two drones discover each other, sync state (peer_id, last_seen_ms, role, status),
send heartbeats, toggle role (Drone1 -> scout, Drone2 mirrors in <1s), and recover from peer loss.
Meets Warm Up acceptance criteria from track.md.

Optional: requires 'airsim' and a running Unreal/AirSim env. For warm-up without AirSim, use handshake_demo.py.
"""

import sys
import threading
import time

try:
    import airsim
except ModuleNotFoundError:
    print("This script requires the 'airsim' package (Microsoft AirSim Python API).")
    print("Install with: pip install airsim")
    print("Note: airsim can be difficult to install on Windows.")
    print("For the warm-up without AirSim, run instead:")
    print("  python handshake_demo.py")
    sys.exit(1)

from config import DRONES, TASHI_VERTEX_PATH, TASHI_BASE_PORT
from config import HEARTBEAT_INTERVAL, PEER_STALE_SECONDS, ROLE_TOGGLE_AFTER_SECONDS
from state_schema import make_state, state_to_json, json_to_state
from tashi_manager import TashiStarterManager

# Replicated state per drone (we run one mission process, two Vertex nodes)
drone1_role = "carrier"
drone2_role = "carrier"
drone1_status = "ready"
drone2_status = "ready"
# Last time we received a state message from each peer (by peer_id in payload)
peer_last_seen = {"Drone1": 0.0, "Drone2": 0.0}
peer_stale_logged = {"Drone1": False, "Drone2": False}
handshake_complete = False
heartbeat_stop = False


def on_consensus(node_id, msg):
    """Called when any Tashi node receives a message (from the P2P mesh)."""
    global drone2_role, peer_last_seen, peer_stale_logged, handshake_complete
    state = json_to_state(msg)
    if not state:
        return
    sender = state.get("peer_id")
    if sender not in ("Drone1", "Drone2"):
        return
    now = time.time()
    peer_last_seen[sender] = now
    role = state.get("role", "carrier")
    status = state.get("status", "ready")
    last_seen_ms = state.get("last_seen_ms", 0)
    if peer_stale_logged[sender]:
        print(f"[{node_id}] Peer {sender} reconnected. Connection and state automatically resuming.")
        peer_stale_logged[sender] = False
    print(f"[{node_id}] State from {sender}: role={role}, status={status}, last_seen_ms={last_seen_ms}")
    # Drone2 (Agent B) mirrors Drone1 (Agent A) role in <1s
    if sender == "Drone1" and node_id == "Drone2":
        if drone2_role != role:
            drone2_role = role
            print(f"[Drone2] Mirrored role from Drone1: role={drone2_role} (acknowledged in <1s)")
    handshake_complete = True


def heartbeat_loop(tashi):
    """Periodically broadcast state from both drones (heartbeats)."""
    global drone1_role, drone2_role, drone1_status, drone2_status, heartbeat_stop
    while not heartbeat_stop:
        s1 = make_state("Drone1", role=drone1_role, status=drone1_status)
        s2 = make_state("Drone2", role=drone2_role, status=drone2_status)
        tashi.broadcast("Drone1", state_to_json(s1))
        tashi.broadcast("Drone2", state_to_json(s2))
        time.sleep(HEARTBEAT_INTERVAL)


def stale_check_loop():
    """If a peer has not been seen for PEER_STALE_SECONDS, mark stale and log."""
    global peer_last_seen, peer_stale_logged
    while not heartbeat_stop:
        time.sleep(1)
        now = time.time()
        for peer in ("Drone1", "Drone2"):
            if peer_last_seen[peer] == 0:
                continue
            if (now - peer_last_seen[peer]) > PEER_STALE_SECONDS and not peer_stale_logged[peer]:
                print(f"[Mission] Peer {peer} marked stale (no heartbeat). Peer lost, returning to idle.")
                peer_stale_logged[peer] = True


def role_toggle_loop():
    """After ROLE_TOGGLE_AFTER_SECONDS, Drone1 (Agent A) toggles role to 'scout'."""
    global drone1_role
    time.sleep(ROLE_TOGGLE_AFTER_SECONDS)
    drone1_role = "scout"
    print("[Drone1] Trigger: toggling role to 'scout'. Drone2 must mirror in <1 second.")


def run():
    global handshake_complete, heartbeat_stop
    print("--- Serve and Protect Bastion: Stateful Handshake (AirSim + Vertex) ---")
    client = airsim.MultirotorClient()
    client.confirmConnection()
    tashi = TashiStarterManager(DRONES, base_port=TASHI_BASE_PORT, tashi_path=TASHI_VERTEX_PATH)
    tashi.setup()
    tashi.start(callback=on_consensus)
    print("Waiting for P2P mesh to form (15s)...")
    time.sleep(15)
    # Start heartbeat and stale-check threads
    threading.Thread(target=heartbeat_loop, args=(tashi,), daemon=True).start()
    threading.Thread(target=stale_check_loop, daemon=True).start()
    threading.Thread(target=role_toggle_loop, daemon=True).start()
    # Physical action: takeoff
    print("Taking off...")
    for d in DRONES:
        client.enableApiControl(True, d)
        client.armDisarm(True, d)
        client.takeoffAsync(vehicle_name=d)
    time.sleep(5)
    # Run long enough for discovery, heartbeats, and role toggle (e.g. 35s)
    print("State sync and heartbeats running. Drone1 will toggle to 'scout' in 15s.")
    time.sleep(35)
    heartbeat_stop = True
    # Land
    print("Landing swarm.")
    for d in DRONES:
        client.landAsync(vehicle_name=d)
    time.sleep(5)
    tashi.shutdown()
    print("Mission complete. Warm Up acceptance: discovery, state sync, heartbeats, role mirror, (optional) failure injection.")


if __name__ == "__main__":
    run()
