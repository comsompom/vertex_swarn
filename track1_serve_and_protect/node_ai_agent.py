"""
AI agent node — participates in the swarm as a peer, subscribes to state,
and publishes short suggestions (e.g. handoff or threat assessment) via OpenAI.
Uses OPENAI_API_KEY from environment; no key in code.
Part of Serve and Protect Bastion (Track 1). Coordination via MQTT/Vertex.
"""

import argparse
import json
import os
import sys
import time

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("Install: pip install paho-mqtt", file=sys.stderr)
    sys.exit(1)

import config

# Optional: OpenAI for suggestions (graceful if missing or key not set)
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

NODE_ID = "ai-agent"
SUGGESTION_INTERVAL = 30.0  # seconds between LLM suggestions
frozen = [False]
nodes_snapshot = {}


def get_openai_client():
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None
    if OpenAI is None:
        return None
    return OpenAI(api_key=api_key)


def build_swarm_summary(nodes: dict) -> str:
    if not nodes:
        return "No nodes in the swarm yet."
    lines = []
    for nid, data in sorted(nodes.items()):
        role = data.get("role", "?")
        status = data.get("status", "?")
        sector = data.get("sector_id") or "—"
        battery = data.get("battery", "?")
        lines.append(f"- {nid}: role={role}, status={status}, sector={sector}, battery={battery}%")
    return "Current swarm state:\n" + "\n".join(lines)


def get_suggestion_from_llm(summary: str, model: str = "gpt-4o-mini") -> str | None:
    client = get_openai_client()
    if not client:
        return None
    try:
        r = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a tactical advisor for a perimeter defence swarm. Reply in 1-2 short sentences. Suggest one action or observation (e.g. handoff, sector priority, or threat assessment) based only on the swarm state given.",
                },
                {"role": "user", "content": summary},
            ],
            max_tokens=150,
        )
        if r.choices and r.choices[0].message.content:
            return r.choices[0].message.content.strip()
    except Exception as e:
        return f"[AI error: {e!s}]"
    return None


def main():
    parser = argparse.ArgumentParser(description="Bastion AI agent (OpenAI suggestions)")
    parser.add_argument("--broker", default=config.MQTT_BROKER)
    parser.add_argument("--port", type=int, default=config.MQTT_PORT)
    parser.add_argument("--interval", type=float, default=SUGGESTION_INTERVAL)
    parser.add_argument("--model", default="gpt-4o-mini")
    args = parser.parse_args()

    if not os.environ.get("OPENAI_API_KEY", "").strip():
        print("[ai-agent] OPENAI_API_KEY not set; will publish placeholder only. Set it to enable LLM suggestions.", file=sys.stderr)
    if OpenAI is None:
        print("[ai-agent] openai package not installed; pip install openai. Will publish placeholder only.", file=sys.stderr)

    def on_connect(client, userdata, flags, reason_code, properties=None):
        if reason_code != 0:
            print(f"[{NODE_ID}] Connect failed: {reason_code}")
            return
        client.subscribe(config.STATE_TOPIC_SUBSCRIBE)
        client.subscribe(config.E_STOP_TOPIC)
        print(f"[{NODE_ID}] Connected; will publish suggestions to {config.AI_SUGGESTIONS_TOPIC}")

    def on_message(client, userdata, msg):
        if msg.topic == config.E_STOP_TOPIC:
            frozen[0] = True
            print(f"[{NODE_ID}] E-STOP received — FROZEN")
            return
        if msg.topic.startswith(f"{config.TOPIC_PREFIX}/state/"):
            try:
                s = json.loads(msg.payload.decode())
                nodes_snapshot[s.get("node_id", "?")] = {**s, "last_seen": time.time()}
            except Exception:
                pass

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=NODE_ID)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(args.broker, args.port, 60)
    client.loop_start()

    last_suggestion_time = [0.0]

    try:
        while True:
            if frozen[0]:
                time.sleep(0.5)
                continue
            now = time.time()
            if now - last_suggestion_time[0] >= args.interval:
                summary = build_swarm_summary(nodes_snapshot)
                suggestion = get_suggestion_from_llm(summary, model=args.model)
                if suggestion is None:
                    suggestion = "No suggestion (set OPENAI_API_KEY and install openai for LLM suggestions)."
                payload = {
                    "node_id": NODE_ID,
                    "ts_ms": int(now * 1000),
                    "suggestion": suggestion,
                }
                client.publish(config.AI_SUGGESTIONS_TOPIC, json.dumps(payload), qos=1)
                print(f"[{NODE_ID}] Published: {suggestion[:80]}...")
                last_suggestion_time[0] = now
            time.sleep(5)
    except KeyboardInterrupt:
        pass
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
