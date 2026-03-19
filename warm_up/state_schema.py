"""
Replicated JSON state schema for the Warm Up (Stateful Handshake).
Each drone maintains: peer_id, last_seen_ms, role, status.
"""

import json
import time

def make_state(peer_id: str, role: str = "carrier", status: str = "ready") -> dict:
    """Build the tiny replicated state payload."""
    return {
        "peer_id": peer_id,
        "last_seen_ms": int(time.time() * 1000),
        "role": role,
        "status": status,
    }


def state_to_json(state: dict) -> str:
    return json.dumps(state)


def json_to_state(payload: str) -> dict | None:
    try:
        return json.loads(payload)
    except (json.JSONDecodeError, TypeError):
        return None
