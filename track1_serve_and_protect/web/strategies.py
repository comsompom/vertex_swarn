"""
AI Control strategies for drone/sentry coordination in Serve and Protect Bastion.
Each strategy takes current swarm state (list of node dicts) and returns a recommendation
and optional actions. Used by the dashboard "AI Control" button.
"""

import os
import time

# Optional OpenAI (graceful if missing or no key)
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# Thresholds
LOW_BATTERY_PCT = 15
STALE_SECONDS = 10
SECTORS = ["A1", "A2", "A3", "B1", "B2"]


def _node_list_from_dict(nodes_dict: dict) -> list[dict]:
    """Convert dashboard nodes dict to list of state dicts (for strategy input)."""
    now = time.time()
    return [
        {**data, "last_seen": data.get("last_seen", now)}
        for _, data in sorted(nodes_dict.items())
    ]


def strategy_handoff(nodes: list[dict]) -> dict:
    """
    Low-battery handoff: recommend handing off a low-battery drone to a sentry.
    Drones with battery <= LOW_BATTERY_PCT should hand off to a sentry (same sector preferred).
    """
    drones_low = [n for n in nodes if n.get("role") == "drone" and (n.get("battery") or 100) <= LOW_BATTERY_PCT]
    sentries = [n for n in nodes if n.get("role") == "sentry"]
    if not drones_low:
        return {"recommendation": "No low-battery drones. All drones above {}%.".format(LOW_BATTERY_PCT), "actions": []}
    actions = []
    for d in drones_low:
        nid = d.get("node_id", "?")
        bat = d.get("battery", 0)
        sector = d.get("sector_id") or "—"
        # Prefer sentry in same sector; else first available
        best = next((s for s in sentries if s.get("sector_id") == sector), sentries[0] if sentries else None)
        if best:
            actions.append({"type": "handoff", "from": nid, "to": best.get("node_id"), "sector": sector})
    rec = "Low battery: " + "; ".join(
        "{} ({}%) → hand off to sentry in sector {}".format(d["node_id"], d.get("battery"), d.get("sector_id") or "?")
        for d in drones_low
    )
    return {"recommendation": rec, "actions": actions}


def strategy_rebalance(nodes: list[dict]) -> dict:
    """
    Sector rebalance: identify sectors with no sentry or overloaded, suggest reassignment.
    """
    sentries = [n for n in nodes if n.get("role") == "sentry"]
    covered = {s.get("sector_id") for s in sentries if s.get("sector_id")}
    uncovered = [sec for sec in SECTORS if sec not in covered]
    overloaded = []
    for sec in SECTORS:
        count = sum(1 for s in sentries if s.get("sector_id") == sec)
        if count > 1:
            overloaded.append(sec)
    if not uncovered and not overloaded:
        return {"recommendation": "Sectors A1, A2, A3, B1, B2 are each covered by at least one sentry.", "actions": []}
    actions = []
    if uncovered:
        actions.append({"type": "add_sentry", "sectors": uncovered})
    if overloaded:
        actions.append({"type": "rebalance", "sectors": overloaded})
    rec_parts = []
    if uncovered:
        rec_parts.append("Uncovered sectors: {} — add or assign a sentry.".format(", ".join(uncovered)))
    if overloaded:
        rec_parts.append("Multiple sentries in {} — consider reassigning one.".format(", ".join(overloaded)))
    return {"recommendation": " ".join(rec_parts) or "No rebalance needed.", "actions": actions}


def strategy_stale(nodes: list[dict], stale_sec: float = STALE_SECONDS) -> dict:
    """
    Stale node recovery: flag nodes that have not been seen for > stale_sec.
    """
    now = time.time()
    stale = [n for n in nodes if (now - (n.get("last_seen") or 0)) > stale_sec]
    if not stale:
        return {"recommendation": "All nodes reporting recently (within {}s).".format(int(stale_sec)), "actions": []}
    actions = [{"type": "check_node", "node_id": n.get("node_id")} for n in stale]
    rec = "Stale nodes (no update > {}s): {} — consider restarting or replacing.".format(
        int(stale_sec), ", ".join(n.get("node_id", "?") for n in stale)
    )
    return {"recommendation": rec, "actions": actions}


def strategy_openai(nodes: list[dict]) -> dict:
    """
    OpenAI tactical suggestion: summarize swarm state and ask for one short recommendation.
    Requires OPENAI_API_KEY. Falls back to a generic message if unavailable.
    """
    if not nodes:
        return {"recommendation": "No swarm state yet. Start nodes and try again.", "actions": []}
    summary_lines = []
    for n in nodes:
        summary_lines.append(
            "{}: role={}, status={}, sector={}, battery={}%".format(
                n.get("node_id", "?"),
                n.get("role", "?"),
                n.get("status", "?"),
                n.get("sector_id") or "—",
                n.get("battery", "?"),
            )
        )
    summary = "Current swarm state:\n" + "\n".join(summary_lines)
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key or OpenAI is None:
        return {
            "recommendation": "OpenAI not configured (set OPENAI_API_KEY and install openai). Using rule-based fallback: run Handoff or Rebalance for tactical advice.",
            "actions": [],
        }
    try:
        client = OpenAI(api_key=api_key)
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a tactical advisor for a perimeter defence swarm. Reply in 1-2 short sentences. Suggest one concrete action (e.g. handoff, sector rebalance, or E-Stop) based only on the swarm state.",
                },
                {"role": "user", "content": summary},
            ],
            max_tokens=150,
        )
        if r.choices and r.choices[0].message.content:
            return {"recommendation": r.choices[0].message.content.strip(), "actions": []}
    except Exception as e:
        return {"recommendation": "AI error: {}".format(e), "actions": []}
    return {"recommendation": "No AI response.", "actions": []}


def strategy_auto(nodes: list[dict]) -> dict:
    """
    Auto: run handoff, rebalance, stale in order; return first with actions; else OpenAI.
    """
    for name, fn in [
        ("handoff", strategy_handoff),
        ("rebalance", strategy_rebalance),
        ("stale", strategy_stale),
    ]:
        result = fn(nodes)
        if result.get("actions"):
            result["strategy_used"] = name
            return result
    result = strategy_openai(nodes)
    result["strategy_used"] = "openai"
    return result


STRATEGIES = {
    "handoff": ("Low-battery handoff", strategy_handoff),
    "rebalance": ("Sector rebalance", strategy_rebalance),
    "stale": ("Stale node recovery", strategy_stale),
    "openai": ("OpenAI tactical", strategy_openai),
    "auto": ("Auto (pick best)", strategy_auto),
}


def run_strategy(strategy_name: str, nodes_dict: dict) -> dict:
    """Run a named strategy on current nodes dict. Returns { strategy, recommendation, actions }."""
    nodes_list = _node_list_from_dict(nodes_dict)
    if strategy_name not in STRATEGIES:
        return {"ok": False, "error": "Unknown strategy: {}".format(strategy_name), "strategies": list(STRATEGIES.keys())}
    _, fn = STRATEGIES[strategy_name]
    result = fn(nodes_list)
    result["strategy"] = strategy_name
    result["ok"] = True
    return result
