# Serve and Protect Bastion — Track 1 Solution

**Vertex Swarm Challenge 2026** · **Track 1 | Ghost in the Machine (Open Track)**

A peer-to-peer **military defence swarm**: perimeter sensors, sentry rovers, and drones coordinate without a central command. One node detects a fault → entire fleet freezes in milliseconds (P2P E-Stop). Nodes self-heal when peers drop or the network degrades.

---

## Project overview

**Serve and Protect Bastion** demonstrates decentralized coordination for a perimeter-defence scenario: heterogeneous nodes discover each other, share state, negotiate sectors and handoffs, and obey a fleet-wide emergency stop—all over Vertex 2.0 / FoxMQ (or MQTT for local runs), with no central orchestrator, database, or cloud.

### Features

- **Heterogeneous nodes:** Sentries (sector patrol), drones (recon, handoff to sentry when battery low), and an optional spectator (observability only).
- **Shared state:** Each node publishes `node_id`, `role`, `status`, `sector_id`, `battery`; a CRDT-backed threat map can be added for full implementation. State is synced via Vertex/FoxMQ.
- **P2P E-Stop:** A high-priority fault channel; one trigger freezes all nodes in under 50 ms (“hold fire”).
- **Self-healing:** Heartbeats and stale-peer detection; when a node drops, sectors and tasks can be reallocated; relay chains can re-form when comms degrade.
- **Chaos testing:** A chaos-monkey script kills random nodes so you can verify rebalance and E-Stop behavior under failure.
- **Multi-drone swarm:** Default 3 sentries + 3 drones + 1 spectator; add more from the dashboard (Add nodes, 1–20) so they join via FoxMQ/MQTT.
- **Web dashboard:** Flask app at http://127.0.0.1:5000: live swarm state, E-Stop banner, **Add nodes** (drone/sentry), **Fleet control** (E-Stop, Unstop, Chaos monkey), **AI Control** (Low-battery handoff, Sector rebalance, Stale recovery, OpenAI tactical).
- **Optional AI agent:** Peer node `node_ai_agent.py` publishes OpenAI tactical suggestions to the mesh; set `OPENAI_API_KEY` to enable.

---

## How to work with it

### Prerequisites

- Python 3.10+
- **FoxMQ (Vertex)** — The FoxMQ binary is in `foxmq_broker/` and is used for coordination (Vertex-backed MQTT). If you need to set it up again, download from [FoxMQ releases](https://github.com/tashigg/foxmq/releases) and place the binary in `foxmq_broker/`. See [scripts/README_FOXMQ.md](scripts/README_FOXMQ.md).
- **Alternative:** For local demo without FoxMQ, use an MQTT broker (e.g. [Eclipse Mosquitto](https://mosquitto.org/) on port 1883) and run without `--start-broker-foxmq`.

### Install

```bash
cd track1_serve_and_protect
pip install -r requirements.txt
```

### Configuration

Edit `config.py` or use environment variables:

- `BASTION_BROKER` — broker host (default `127.0.0.1`)
- `BASTION_MQTT_PORT` — broker port (default `1883`)
- `BASTION_DASHBOARD_PORT` — Flask dashboard HTTP port (default `5000`)
- `OPENAI_API_KEY` — Optional; enables the AI agent node for LLM-powered suggestions (see below). Never commit this key; use `.env` or environment.

See `.env.example` for a template. Topics, heartbeat interval, and roles are defined in `config.py`.

### Run the swarm (multi-drone solution)

**Quick start:** (1) Start swarm: `cd track1_serve_and_protect` then `python run_swarm.py --start-broker-foxmq`. (2) Start dashboard: in a second terminal, `python -m web.dashboard` from `track1_serve_and_protect`, then open **http://127.0.0.1:5000**.

**Terminal 1 — swarm:**

```bash
cd track1_serve_and_protect
pip install -r requirements.txt   # first time only
python run_swarm.py --start-broker-foxmq
```

This starts the FoxMQ broker (if not already running) and launches **3 sentries, 3 drones, and 1 spectator** by default (7 agents; use `--sentries N --drones M` to override). The first run creates `foxmq_broker/foxmq.d/` (address-book and keys) automatically. You can add more drones or sentries from the **Flask dashboard** (“Add nodes” section).

**Other options:**

- **Docker (Mosquitto):** `python run_swarm.py --start-broker-docker`
- **Broker already running:** `python run_swarm.py`

If no broker is reachable, the script prints instructions and exits.

The spectator prints the current swarm state to the console every few seconds.

### Web dashboard (Flask)

**Quick start:** In a second terminal, run `python -m web.dashboard` from `track1_serve_and_protect`, then open **http://127.0.0.1:5000**.

```bash
cd track1_serve_and_protect
python -m web.dashboard
```

Open **http://127.0.0.1:5000** in your browser. The dashboard:

- **Fleet control** tab: **E-Stop** (freeze all nodes), **Unstop** (resume all nodes), **Chaos monkey (kill 2)** — same as running `python chaos_monkey.py --kill 2`.
- Shows all nodes (role, status, sector, battery), E-Stop status, and the latest AI suggestion. Data refreshes every 2 seconds.
- **Add nodes:** Use “Add drone” or “Add sentry” to start more nodes; choose a count (1–20) and they join the swarm via FoxMQ/MQTT.

- **AI Control:** Run a strategy (Low-battery handoff, Sector rebalance, Stale node recovery, or OpenAI tactical); result is published to the mesh.

The dashboard lives in the `web/` folder. Optional: `--port 5001`, `--broker`, `--mqtt-port` to match your broker.

### Optional: AI agent (OpenAI)

To add an AI peer that publishes tactical suggestions (e.g. handoff or threat assessment) based on swarm state:

1. Set your OpenAI API key in the environment (never commit it):
   ```bash
   set OPENAI_API_KEY=sk-...   # Windows
   export OPENAI_API_KEY=sk-... # Linux/macOS
   ```
2. Install dependencies: `pip install -r requirements.txt` (includes `openai`).
3. In a separate terminal, run the AI agent (from `track1_serve_and_protect`):
   ```bash
   python node_ai_agent.py
   ```
   It subscribes to swarm state and every 30 seconds sends a summary to OpenAI and publishes the suggestion to the mesh. The dashboard shows the latest suggestion. If `OPENAI_API_KEY` is not set, the agent still runs and publishes a placeholder message.

### Trigger E-Stop and Unstop

From another terminal (or use the **Fleet control** tab in the dashboard):

**E-Stop (freeze fleet):**
```bash
python e_stop_trigger.py
```

**Unstop (resume fleet):**
```bash
python unstop_trigger.py
```

Nodes freeze on E-Stop and resume on Unstop (stop normal operation and log “FROZEN”). The **Fleet control** tab in the dashboard also provides E-Stop, Unstop, and Chaos monkey (kill 2) buttons.

### Run the chaos monkey

To simulate node failures and observe rebalance (and E-Stop under failure), run the chaos monkey while the swarm is running:

```bash
# Kill 2 random nodes (auto-detects PIDs if psutil is installed)
python chaos_monkey.py --kill 2

# Or pass PIDs explicitly
python chaos_monkey.py --pids 1234 5678 --kill 1
```

Install `psutil` for automatic discovery of node processes: `pip install psutil`.

### Running individual nodes

You can run nodes manually for debugging or custom topologies:

```bash
# Sentry with custom ID and sector
python node_sentry.py --id sentry-1 --sector A1 --broker 127.0.0.1 --port 1883

# Drone
python node_drone.py --id drone-1 --broker 127.0.0.1 --port 1883

# Spectator (read-only)
python node_spectator.py --broker 127.0.0.1 --port 1883

# Flask dashboard (visualization)
python -m web.dashboard --broker 127.0.0.1 --mqtt-port 1883

# Optional: AI agent (set OPENAI_API_KEY first)
python node_ai_agent.py --broker 127.0.0.1 --port 1883
```

### Tests

All logic is covered by unit and integration tests. Run from the track folder:

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```

Tests cover: state schema and E-Stop payload, config (topics, roles, timing, dashboard port), sentry/drone payload construction, chaos monkey PID discovery, run_swarm subprocess launch, and the Flask dashboard API (`/`, `/api/state`). An integration test that connects to a real broker is skipped unless an MQTT broker is running on `127.0.0.1:1883`.

---

## Repo layout

```
track1_serve_and_protect/
├── README.md                 # This file — project description and usage
├── demo_script.md            # Step-by-step demo script
├── web/                      # Flask web dashboard (HTML/CSS/JS separated)
│   ├── __init__.py
│   ├── dashboard.py          # App and MQTT logic (run: python -m web.dashboard)
│   ├── templates/
│   │   └── dashboard.html    # Main page structure
│   └── static/
│       ├── css/dashboard.css # Styles
│       └── js/dashboard.js   # Polling and table render
├── tests/                    # Unit and integration tests (pytest)
├── requirements.txt
├── config.py                 # Broker, topics, timeouts, roles, dashboard port
├── state.py                  # Shared state schema, E-Stop and Unstop payloads
├── node_sentry.py            # Sentry: patrol sector, E-Stop/Unstop
├── node_drone.py             # Drone: recon, handoff when battery low
├── node_spectator.py         # Spectator: console view of swarm state
├── node_ai_agent.py          # Optional: OpenAI-powered suggestion peer (env: OPENAI_API_KEY)
├── run_swarm.py              # Launch N sentries + M drones + spectator
├── e_stop_trigger.py         # Send E-Stop message (freeze fleet)
├── unstop_trigger.py          # Send Unstop message (resume fleet)
└── chaos_monkey.py           # Kill random nodes for resilience testing
```

---

## References

- [track.md](../track.md) — Track 1 description and examples.
- [rules.md](../rules.md) — Submission rules and terms.
- Discord (BUIDL submission): https://discord.com/channels/1011889557526032464/1483341393052176526
