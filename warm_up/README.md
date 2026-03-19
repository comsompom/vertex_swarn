# Warm Up: The Stateful Handshake — Serve and Protect Bastion

**Vertex Swarm Challenge 2026** · **Python + Drones** · Aligned with the [AirSim + Vertex starter kit](https://github.com/tashigit/airsim-vertex-starter-kit).

Two drones (Drone1, Drone2) discover each other, sync state (`peer_id`, `last_seen_ms`, `role`, `status`), send heartbeats, toggle role (Drone1 → "scout", Drone2 mirrors in &lt;1s), and support failure recovery. Meets the [Warm Up](https://github.com/tashigit/airsim-vertex-starter-kit) and track acceptance criteria.

**Recommended (no AirSim):** Run the standalone demo — no simulator or broker required:
```bash
cd warm_up
python handshake_demo.py
```
For MQTT or AirSim + Tashi Vertex, see below.

---

## Hackathon participation (pre-flight)

Before hacking:

1. **Join Discord** — [Vertex Swarm](https://discord.gg/r8YphnA8) and [Tashi](https://discord.com/invite/SJge5pTwkb) (required for bounty).
2. **Run the handshake** — Use the standalone demo, AirSim mission, or MQTT option below.
3. **Record proof** — Short video or log showing discovery, state sync, heartbeats, and role mirror.
4. **Submit for the $50 Daily Bounty** — Post your proof in the [Vertex Swarm handshake channel](https://discord.com/channels/1011889557526032464/1483341393052176526). This also unlocks the main tracks.

**Video demo (Stateful Handshake):** [Watch on YouTube](https://www.youtube.com/watch?v=L9qMzjdvfI0)

Track details: [DoraHacks Warm-Up](https://dorahacks.io/hackathon/global-vertex-swarm-challenge/tracks#-warm-up-the-stateful-handshake).

---

## Prerequisites (for AirSim path only)

The **standalone demo** (`handshake_demo.py`) and **MQTT path** need no AirSim. The script `stateful_handshake_mission.py` is optional and requires:

1. **AirSim** — Installed and running (Unreal Engine environment). The `airsim` Python package can be difficult to install on Windows; if you get `ModuleNotFoundError: airsim`, use `handshake_demo.py` instead.  
   - [AirSim docs](https://github.com/Microsoft/AirSim)
2. **Tashi Vertex RS** — Local clone of [tashi-vertex-rs](https://github.com/tashigit/tashi-vertex-rs), built with examples:
   ```bash
   git clone https://github.com/tashigit/tashi-vertex-rs
   cd tashi-vertex-rs
   cargo build
   ```
   Ensure the repo contains `target/debug/examples/drone-comm` and `target/debug/examples/key-generate` (and `lib/` if required by the build).
3. **OS** — **macOS / Linux**: run directly. **Windows**: use **WSL** (Windows Subsystem for Linux); the script will invoke Tashi via WSL.

---

## AirSim setup

### 1. Settings file

- **Windows**: `Documents\AirSim\settings.json`  
- **Linux/Mac**: `~/Documents/AirSim/settings.json`

### 2. Swarm configuration

Use two vehicles so the warm up controls two drones:

```json
{
  "SeeDocsAt": "https://github.com/Microsoft/AirSim/blob/master/docs/settings.md",
  "SettingsVersion": 1.2,
  "SimMode": "Multirotor",
  "ClockType": "SteppableClock",
  "Vehicles": {
    "Drone1": {
      "VehicleType": "SimpleFlight",
      "X": 0, "Y": 0, "Z": 0
    },
    "Drone2": {
      "VehicleType": "SimpleFlight",
      "X": 2, "Y": 0, "Z": 0
    }
  }
}
```

### 3. Launch environment

Start an AirSim-compatible Unreal environment (e.g. **Blocks**, **Africa**, **CityEnviron**). When prompted, choose **Multirotor**.

---

## Code setup

### 1. Install Python dependencies

```bash
cd warm_up
pip install -r requirements.txt
```

### 2. Point to Tashi Vertex

Set the path to your built `tashi-vertex-rs` clone (default in code is `../tashi-vertex-rs`):

- **Option A** — Edit `config.py`: set `TASHI_VERTEX_PATH` to your path (e.g. `"C:/Users/you/tashi-vertex-rs"` on Windows; the manager converts it for WSL if needed).
- **Option B** — Environment variable:
  ```bash
  export TASHI_VERTEX_PATH=/path/to/tashi-vertex-rs   # Linux/macOS
  set TASHI_VERTEX_PATH=C:\path\to\tashi-vertex-rs    # Windows cmd
  ```

### 3. Run the mission (optional — AirSim path)

With AirSim and the Unreal environment running, and `airsim` installed:

```bash
python stateful_handshake_mission.py
```

If you get `ModuleNotFoundError: No module named 'airsim'`, use **`python handshake_demo.py`** instead for the warm-up (no AirSim required).

---

## What happens (acceptance criteria)

1. **Consensus boot** — Ports are cleared; two Tashi P2P nodes (Drone1, Drone2) start and form the mesh.
2. **Discovery & handshake** — Both nodes run and discover each other via Vertex; you see `[Drone1] P2P Ready.` and `[Drone2] P2P Ready.`
3. **State sync & heartbeats** — Each drone periodically broadcasts state: `peer_id`, `last_seen_ms`, `role`, `status`. The other receives and prints it (state replication from Agent A to Agent B and vice versa).
4. **Trigger: role toggle** — After 15 seconds, Drone1 (Agent A) sets its role to `"scout"`. Drone2 (Agent B) receives it and mirrors the role, printing: `[Drone2] Mirrored role from Drone1: role=scout (acknowledged in <1s)`.
5. **Takeoff & land** — Both drones take off, the handshake/heartbeats/role toggle run, then both land.
6. **Failure injection (optional)** — To show “peer marked stale” and “connection resuming”, you can stop one Tashi node (e.g. kill one `drone-comm` process), wait ~5s for the other to log “Peer marked stale… Peer lost, returning to idle”, then restart the mission or the node so the other logs “Connection and state automatically resuming.” (Exact steps depend on how you run the nodes; the mission code supports detecting stale and recovery in the callback.)

**Proof artifact:** Record a short screen capture or terminal log showing discovery, state replication, heartbeats, and role mirror in &lt;1s (and optionally failure/recovery). Submit to Discord **#shipping-log** for the Stateful Handshake badge.

---

## Configuration

| Item | Default | Description |
|------|--------|-------------|
| `TASHI_VERTEX_PATH` | `../tashi-vertex-rs` | Path to built tashi-vertex-rs repo. |
| `TASHI_BASE_PORT` | `9500` | Base port for P2P nodes (Drone1=9500, Drone2=9501). |
| `HEARTBEAT_INTERVAL` | `2.0` | Seconds between state broadcasts. |
| `PEER_STALE_SECONDS` | `5.0` | No message from peer for this long → “peer marked stale”. |
| `ROLE_TOGGLE_AFTER_SECONDS` | `15.0` | Drone1 toggles role to `"scout"` after this many seconds. |

---

## Standalone handshake demo (no AirSim, no broker)

To verify the handshake logic without AirSim or an MQTT broker:

```bash
python handshake_demo.py
```

This runs two logical drones in-process: state sync, heartbeats every 2s, and after 15s Drone1 toggles to `"scout"` and Drone2 mirrors. You should see `[Drone2] Mirrored role from Drone1: role=scout (acknowledged in <1s)` and `Mission complete.`

---

## Optional: MQTT-only path (no AirSim)

If you don’t have AirSim or Tashi Vertex built yet, you can still run the **stateful handshake logic** over MQTT (e.g. FoxMQ or Mosquitto) with two scripts that only do discovery, state sync, heartbeats, and role mirror:

1. Start an MQTT broker (FoxMQ or Mosquitto) on `127.0.0.1:1883`.
2. In two terminals:
   - `python drone_a.py`  (Agent A; toggles to "scout" after 15s)
   - `python drone_b.py`  (Agent B; mirrors A’s role)

See `config.py` for `MQTT_BROKER`, `MQTT_PORT`, and topic settings. This path does **not** run simulated drones—use it for quick local testing of the handshake and state schema.

---

## Project layout

```
warm_up/
├── README.md                      # This file
├── requirements.txt               # airsim, paho-mqtt
├── config.py                      # Tashi path, ports, timing, MQTT options
├── state_schema.py                # State: peer_id, last_seen_ms, role, status
├── tashi_manager.py               # Tashi Vertex P2P manager (from AirSim starter kit)
├── stateful_handshake_mission.py  # Main mission: AirSim + Vertex (Python + Drones)
├── drone_a.py                     # Optional: Agent A over MQTT only
└── drone_b.py                     # Optional: Agent B over MQTT only
```

---

## References

- [Track: Warm Up](https://dorahacks.io/hackathon/global-vertex-swarm-challenge/tracks#-warm-up-the-stateful-handshake) — Stateful Handshake acceptance criteria.
- [AirSim + Vertex starter kit](https://github.com/tashigit/airsim-vertex-starter-kit) — Base for this warm up.
- [Tashi Vertex RS](https://github.com/tashigit/tashi-vertex-rs) — P2P consensus engine (build and point `TASHI_VERTEX_PATH` here).
- [Tashi docs](https://www.tashi.dev/) — Vertex coordination layer.
