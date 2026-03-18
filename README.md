# Serve and Protect Bastion

**Vertex Swarm Challenge 2026** — Peer-to-peer military defence swarm: coordinate, automate, secure. No central orchestrator; machines talk directly to machines.

This repository is our challenge entry. It includes the **Warm Up** (Stateful Handshake) and the **Track 1** solution (**Ghost in the Machine**): a perimeter-defence swarm of sentries and drones that discover each other, share state, and obey a fleet-wide E-Stop, with a Flask dashboard for visualization.

---

## What this repo contains

| Part | Description |
|------|--------------|
| **Warm Up** | Two agents discover each other, sync state (`peer_id`, `role`, `status`), send heartbeats, mirror roles, and recover from failure. Implemented in `warm_up/` (standalone demo, MQTT, or AirSim + Tashi Vertex). |
| **Track 1 — Serve and Protect Bastion** | Heterogeneous swarm: sentries (sector patrol), drones (recon, handoff when battery low), spectator, optional **AI agent** (OpenAI suggestions), and a **Flask web dashboard**. All nodes use MQTT (or Vertex/FoxMQ) for pub/sub; one E-Stop message freezes the whole fleet in under 50 ms. A chaos-monkey script kills random nodes to demonstrate self-healing. Implemented in `track1_serve_and_protect/`. |
| **Docs** | Challenge description, tracks, rules, execution plan, and pre-flight checklist in the repo root. |

We follow the challenge pillars: **Coordinate** (discover, share state, cooperate), **Automate** (hand off, self-heal), **Secure** (P2P E-Stop, fault → fleet freeze).

---

## Repository structure

```
vertex_swarn/
├── README.md                 # This file — project overview and how to run
├── PLAN.md                   # Step-by-step execution plan and track choice
├── description.md            # Official challenge description
├── track.md                  # Warm Up + Track 1–3 specs and judging
├── rules.md                  # Submission rules (one Warm-Up, one main track)
├── HACKATHON_PREFLIGHT.md    # Pre-flight checklist (Discord, handshake, bounty)
├── VIDEO_RECORDING_GUIDE.md  # How to record the presentation video
├── pre_flight.md             # Pre-flight email content
├── warm_up.md                # Warm-up letter / goals
├── suggeestion.md            # Strategy and project ideas
│
├── warm_up/                  # Warm Up: Stateful Handshake (Python + Drones)
│   ├── README.md
│   ├── handshake_demo.py     # Standalone in-process demo (no broker)
│   ├── stateful_handshake_mission.py  # AirSim + Tashi Vertex
│   ├── drone_a.py, drone_b.py # Optional MQTT-only handshake
│   ├── config.py, state_schema.py, tashi_manager.py
│   └── requirements.txt
│
└── track1_serve_and_protect/ # Track 1: Serve and Protect Bastion
    ├── README.md
    ├── demo_script.md        # Step-by-step demo for pitch/video
    ├── web/                  # Flask web dashboard (templates + static)
    │   ├── dashboard.py      # App and MQTT (run: python -m web.dashboard)
    │   ├── templates/dashboard.html
    │   └── static/css/dashboard.css, static/js/dashboard.js
    ├── run_swarm.py          # Launch sentries + drones + spectator
    ├── node_sentry.py        # Sentry node (sector patrol)
    ├── node_drone.py         # Drone node (recon, battery, handoff)
    ├── node_spectator.py     # Console view of swarm state
    ├── e_stop_trigger.py     # Send E-Stop to fleet
    ├── chaos_monkey.py       # Kill random nodes (resilience demo)
    ├── config.py, state.py
    ├── requirements.txt
    └── tests/                # Pytest: state, config, nodes, dashboard, run_swarm, integration
```

---

## Implementation summary

### Warm Up (Stateful Handshake)

- **Goal:** Two agents discover, sync state, heartbeat, toggle role (e.g. Drone1 → `"scout"`), and mirror in &lt;1 s; demonstrate failure recovery.
- **Options:**
  1. **Standalone** — `warm_up/handshake_demo.py`: in-process, no MQTT or AirSim.
  2. **MQTT** — `drone_a.py` + `drone_b.py` with a broker (e.g. Mosquitto) on port 1883.
  3. **AirSim + Tashi Vertex** — `stateful_handshake_mission.py` with AirSim and [tashi-vertex-rs](https://github.com/tashigit/tashi-vertex-rs) built; uses P2P consensus and simulated drones.
- **State schema:** `peer_id`, `last_seen_ms`, `role`, `status` (see `warm_up/state_schema.py`).

### Track 1 (Serve and Protect Bastion)

- **Goal:** Perimeter-defence swarm with no central server: sentries patrol sectors, drones do recon and hand off when battery is low; one E-Stop freezes the fleet; chaos monkey proves resilience.
- **Transport:** FoxMQ (Vertex-backed MQTT) for hackathon submission (`--start-broker-foxmq` or run `scripts/start_foxmq.py`); or Mosquitto/Docker for local demo.
- **Nodes:**
  - **Sentry** — Publishes state (role, status, sector_id, battery); subscribes to state + E-Stop; stops normal loop when E-Stop received.
  - **Drone** — Same pattern; simulates battery drain; status becomes `low_battery_handoff` when battery ≤ 15%.
  - **Spectator** — Subscribes only; prints swarm state to console.
  - **Dashboard** — Flask app: MQTT client in background thread, serves HTML table + E-Stop banner; `/api/state` returns JSON; front end polls every 2 s.
- **Topics:** `bastion/serve_and_protect/state/<node_id>`, `.../state/+`, `.../e_stop`.
- **State schema:** `node_id`, `last_seen_ms`, `role`, `status`, `sector_id`, `battery`, `last_threat` (see `track1_serve_and_protect/state.py`).

---

## Prerequisites

- **Python 3.10+**
- **Warm Up:** For standalone demo, nothing else. For MQTT: an MQTT broker. For AirSim path: [AirSim](https://github.com/Microsoft/AirSim), Unreal environment, and [tashi-vertex-rs](https://github.com/tashigit/tashi-vertex-rs) built.
- **Track 1:** FoxMQ binary in `track1_serve_and_protect/foxmq_broker/` (Vertex-backed MQTT). Optional: [Mosquitto](https://mosquitto.org/) or Docker for a plain MQTT broker.

---

## How to run

### 1. Warm Up (Stateful Handshake)

**Option A — Standalone (no broker, no AirSim):**

```bash
cd warm_up
pip install -r requirements.txt
python handshake_demo.py
```

You should see two logical drones syncing state, heartbeats, and role mirror after ~15 s.

**Option B — MQTT:**

Start a broker (e.g. `mosquitto -v`), then in two terminals:

```bash
cd warm_up
pip install -r requirements.txt
python drone_a.py    # Terminal 1
python drone_b.py   # Terminal 2
```

**Option C — AirSim + Tashi Vertex:**

See [warm_up/README.md](warm_up/README.md): set `TASHI_VERTEX_PATH`, run AirSim and the Unreal env, then:

```bash
cd warm_up
pip install -r requirements.txt
python stateful_handshake_mission.py
```

---

### 2. Track 1 (Serve and Protect Bastion)

**FoxMQ (Vertex)** is set up: the binary lives in `track1_serve_and_protect/foxmq_broker/` and is used for coordination. To run the swarm:

```bash
cd track1_serve_and_protect
pip install -r requirements.txt
python run_swarm.py --start-broker-foxmq
```

This starts the FoxMQ broker (Vertex-backed MQTT) and launches **three sentries, three drones, and one spectator** by default (7 agents). Use `--sentries N --drones M` to override. You can also add more drones or sentries from the **Flask dashboard** (“Add nodes” controls). The spectator prints swarm state to the console.

**Alternatives:** Use `--start-broker-docker` for Mosquitto in Docker, or start a broker (e.g. `mosquitto -v`) in another terminal and run `python run_swarm.py` without `--start-broker-foxmq`.

**Step 3 — (Optional) Start the Flask dashboard:**

In another terminal (from `track1_serve_and_protect`):

```bash
cd track1_serve_and_protect
python -m web.dashboard
```

Open **http://127.0.0.1:5000** in your browser. The dashboard shows all nodes (role, status, sector, battery) and a “FLEET FROZEN” banner when E-Stop is active. Data refreshes every 2 seconds.

**Step 4 — Trigger E-Stop (optional):**

In a third terminal:

```bash
cd track1_serve_and_protect
python e_stop_trigger.py
```

All nodes log “FROZEN”; the dashboard shows the E-Stop banner.

**Step 5 — Chaos monkey (optional):**

To simulate node failures while the swarm is running:

```bash
cd track1_serve_and_protect
python chaos_monkey.py --kill 2
```

Install `psutil` for automatic PID discovery, or pass `--pids PID1 PID2`.

---

### 3. Tests

**Track 1 tests** (state, config, nodes, dashboard, run_swarm, chaos_monkey, integration):

```bash
cd track1_serve_and_protect
pip install -r requirements.txt
python -m pytest tests/ -v
```

An integration test that needs a real broker is skipped unless one is running on `127.0.0.1:1883`.

---

## Configuration (Track 1)

Environment variables (or edit `track1_serve_and_protect/config.py`):

| Variable | Default | Description |
|----------|---------|-------------|
| `BASTION_BROKER` | `127.0.0.1` | MQTT broker host. |
| `BASTION_MQTT_PORT` | `1883` | MQTT broker port. |
| `BASTION_DASHBOARD_PORT` | `5000` | Flask dashboard HTTP port. |

---

## Documentation

| Document | Description |
|----------|-------------|
| [PLAN.md](PLAN.md) | Full execution plan, track choice, phases, checklist. |
| [HACKATHON_COMPLIANCE.md](HACKATHON_COMPLIANCE.md) | Checklist vs Warm Up, Track 1, and rules. |
| [IMPROVEMENTS.md](IMPROVEMENTS.md) | Suggestions to make the project more professional. |
| [VIDEO_RECORDING_GUIDE.md](VIDEO_RECORDING_GUIDE.md) | How to record the presentation video (tools, steps, tips, submission). |
| [description.md](description.md) | Official challenge: pillars, tracks, prizes. |
| [track.md](track.md) | Warm Up + Track 1–3 specs and judging. |
| [rules.md](rules.md) | Submission rules (one Warm-Up, one main track; team ≤5). |
| [HACKATHON_PREFLIGHT.md](HACKATHON_PREFLIGHT.md) | Discord, handshake proof, $50 daily bounty, track unlock. |
| [warm_up/README.md](warm_up/README.md) | Warm Up: setup, AirSim, MQTT, standalone demo. |
| [track1_serve_and_protect/README.md](track1_serve_and_protect/README.md) | Track 1: features, run, dashboard, tests. |
| [track1_serve_and_protect/demo_script.md](track1_serve_and_protect/demo_script.md) | Step-by-step demo for pitch or video. |

---

## References

- **Challenge:** [Vertex Swarm Challenge 2026](https://dorahacks.io/hackathon/global-vertex-swarm-challenge/) (DoraHacks)
- **Discord (BUIDL / handshake):** [Vertex Swarm](https://discord.com/channels/1011889557526032464/1483341393052176526)
- **Warm Up video:** [Stateful Handshake on YouTube](https://www.youtube.com/watch?v=L9qMzjdvfI0)
- **Tashi / Vertex:** [tashi.dev](https://www.tashi.dev/), [tashi-vertex-rs](https://github.com/tashigit/tashi-vertex-rs), [AirSim + Vertex starter kit](https://github.com/tashigit/airsim-vertex-starter-kit)
