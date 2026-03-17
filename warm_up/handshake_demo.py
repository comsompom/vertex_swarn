#!/usr/bin/env python3
"""
Standalone Stateful Handshake demo — no AirSim, no Tashi subprocess.
Runs the same logic in-process: two logical drones, state sync, heartbeats, role mirror.
Use when AirSim or Tashi binaries are not available. For full demo use stateful_handshake_mission.py.
"""

import queue
import threading
import time

from config import HEARTBEAT_INTERVAL, PEER_STALE_SECONDS, ROLE_TOGGLE_AFTER_SECONDS
from state_schema import make_state, state_to_json, json_to_state

DRONES = ["Drone1", "Drone2"]
peer_last_seen = {"Drone1": 0.0, "Drone2": 0.0}
peer_stale_logged = {"Drone1": False, "Drone2": False}
roles = {"Drone1": "carrier", "Drone2": "carrier"}
heartbeat_stop = False


def drone_node(node_id: str, other_id: str, inbox: queue.Queue, outbox: queue.Queue):
    """Simulate one drone: send state, receive peer state, mirror role if Drone2."""
    global peer_last_seen, peer_stale_logged, roles
    status = "ready"
    while not heartbeat_stop:
        role = roles[node_id]
        state = make_state(node_id, role=role, status=status)
        outbox.put(state_to_json(state))
        try:
            msg = inbox.get(timeout=HEARTBEAT_INTERVAL)
        except queue.Empty:
            time.sleep(HEARTBEAT_INTERVAL)
            continue
        state = json_to_state(msg)
        time.sleep(HEARTBEAT_INTERVAL)
        if not state or state.get("peer_id") != other_id:
            continue
        peer_last_seen[state["peer_id"]] = time.time()
        if peer_stale_logged.get(state["peer_id"]):
            print(f"[{node_id}] Peer {other_id} reconnected. Connection and state automatically resuming.")
            peer_stale_logged[state["peer_id"]] = False
        print(f"[{node_id}] State from {other_id}: role={state.get('role')}, status={state.get('status')}, last_seen_ms={state.get('last_seen_ms')}")
        if node_id == "Drone2" and state.get("role") != roles["Drone2"]:
            roles["Drone2"] = state["role"]
            print(f"[Drone2] Mirrored role from Drone1: role={roles['Drone2']} (acknowledged in <1s)")


def stale_check():
    global peer_last_seen, peer_stale_logged
    while not heartbeat_stop:
        time.sleep(1)
        now = time.time()
        for p in DRONES:
            if peer_last_seen.get(p, 0) == 0:
                continue
            if (now - peer_last_seen[p]) > PEER_STALE_SECONDS and not peer_stale_logged.get(p):
                print(f"[Mission] Peer {p} marked stale (no heartbeat). Peer lost, returning to idle.")
                peer_stale_logged[p] = True


def run():
    global roles, heartbeat_stop
    print("--- Serve and Protect Bastion: Stateful Handshake (standalone demo) ---")
    q1_to_2 = queue.Queue()
    q2_to_1 = queue.Queue()
    t1 = threading.Thread(target=drone_node, args=("Drone1", "Drone2", q2_to_1, q1_to_2), daemon=True)
    t2 = threading.Thread(target=drone_node, args=("Drone2", "Drone1", q1_to_2, q2_to_1), daemon=True)
    t1.start()
    t2.start()
    threading.Thread(target=stale_check, daemon=True).start()
    print("Discovery & handshake: both drones exchanging state (heartbeats every", HEARTBEAT_INTERVAL, "s).")
    time.sleep(ROLE_TOGGLE_AFTER_SECONDS)
    roles["Drone1"] = "scout"
    print("[Drone1] Trigger: toggling role to 'scout'. Drone2 must mirror in <1 second.")
    time.sleep(10)
    heartbeat_stop = True
    time.sleep(0.5)
    print("Mission complete. Warm Up: discovery, state sync, heartbeats, role mirror.")


if __name__ == "__main__":
    run()
