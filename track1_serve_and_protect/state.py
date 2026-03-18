"""
Shared state schema for Serve and Protect Bastion.
Replicated via Vertex/FoxMQ; use CRDT for threat_map in full implementation.
"""

import json
import time

# ---- Node state (per-node payload) ----
def make_state(
    node_id: str,
    role: str,
    status: str = "idle",
    sector_id: str | None = None,
    battery: int = 100,
    last_threat: str | None = None,
) -> dict:
    """Build replicated state payload for this node."""
    return {
        "node_id": node_id,
        "last_seen_ms": int(time.time() * 1000),
        "role": role,
        "status": status,
        "sector_id": sector_id,
        "battery": battery,
        "last_threat": last_threat,
    }


def state_to_json(state: dict) -> str:
    return json.dumps(state)


def json_to_state(payload: str) -> dict | None:
    try:
        return json.loads(payload)
    except (json.JSONDecodeError, TypeError):
        return None


# ---- E-Stop (high-priority; one message freezes fleet) ----
def make_e_stop_payload(source_node_id: str, reason: str = "hold_fire") -> dict:
    return {
        "source": source_node_id,
        "reason": reason,
        "ts_ms": int(time.time() * 1000),
    }


def parse_e_stop(payload: str) -> dict | None:
    try:
        return json.loads(payload)
    except (json.JSONDecodeError, TypeError):
        return None


# ---- Threat map (CRDT in full impl: merge by position/severity) ----
def make_threat_entry(sector_id: str, severity: int, claimed_by: str | None = None) -> dict:
    return {"sector_id": sector_id, "severity": severity, "claimed_by": claimed_by}
