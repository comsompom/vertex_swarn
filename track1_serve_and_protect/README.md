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
- **Web dashboard:** A Flask app visualizes swarm state (nodes, roles, status, sector, battery) and E-Stop status in real time.

---

## How to work with it

### Prerequisites

- Python 3.10+
- An MQTT broker for local runs (e.g. [Eclipse Mosquitto](https://mosquitto.org/) on port 1883). For the challenge submission, use Vertex 2.0 or FoxMQ.

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

Topics, heartbeat interval, and roles are defined in `config.py`.

### Run the swarm

Start a mix of sentries and drones plus the spectator:

```bash
python run_swarm.py --sentries 2 --drones 2
```

This launches two sentry nodes (with sectors A1, A2), two drone nodes, and one spectator. The spectator prints the current swarm state every few seconds.

### Web dashboard (Flask)

To visualize the swarm in a browser, start the Flask dashboard (in a separate terminal). Run from the `track1_serve_and_protect` folder:

```bash
python -m web.dashboard
```

Then open **http://127.0.0.1:5000** in your browser. The dashboard lives in the `web/` folder and subscribes to the same MQTT topics as the spectator; it shows all nodes (role, status, sector, battery) and whether the fleet is in E-Stop (frozen). Data refreshes every 2 seconds. Optional: `--port 5001` for a different HTTP port, `--broker` and `--mqtt-port` to match your broker.

### Trigger E-Stop

From another terminal, send a fleet-wide emergency stop:

```bash
python e_stop_trigger.py
```

All nodes that subscribe to the E-Stop topic will freeze (stop normal operation and log “FROZEN”). This demonstrates the P2P safety mechanism.

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
├── web/                      # Flask web dashboard
│   ├── __init__.py
│   └── dashboard.py          # Swarm + E-Stop visualization (run: python -m web.dashboard)
├── tests/                    # Unit and integration tests (pytest)
├── requirements.txt
├── config.py                 # Broker, topics, timeouts, roles, dashboard port
├── state.py                  # Shared state schema, E-Stop payload
├── node_sentry.py            # Sentry: patrol sector, respond to intrusions, E-Stop
├── node_drone.py             # Drone: recon, handoff when battery low
├── node_spectator.py         # Spectator: console view of swarm state
├── run_swarm.py              # Launch N sentries + M drones + spectator
├── e_stop_trigger.py         # Send E-Stop message
└── chaos_monkey.py           # Kill random nodes for resilience testing
```

---

## References

- [PLAN.md](../PLAN.md) — Overall execution plan and warm-up status.
- [track.md](../track.md) — Track 1 description and examples.
- [rules.md](../rules.md) — Submission rules and terms.
- Discord (BUIDL submission): https://discord.com/channels/1011889557526032464/1483341393052176526
