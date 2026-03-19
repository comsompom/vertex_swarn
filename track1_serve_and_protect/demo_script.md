# Demo script — Serve and Protect Bastion (Track 1)

Use this for the live pitch or video submission.

---

## Prerequisites

- MQTT broker running (e.g. `mosquitto -v` on 1883), or FoxMQ/Vertex for real submission: `python run_swarm.py --start-broker-foxmq`.
- Python: `pip install -r requirements.txt`

---

## Step 1: Start the swarm (30 s)

```bash
cd track1_serve_and_protect
python run_swarm.py --start-broker-foxmq
# Or: python run_swarm.py --sentries 2 --drones 2  (if broker already running)
```

You should see: "Started sentry-1 ...", "Started drone-1 ...", "Started spectator ...". Spectator prints swarm state every few seconds.

**Optional:** In another terminal run the Flask dashboard: `python -m web.dashboard` (from `track1_serve_and_protect`), then open http://127.0.0.1:5000. The dashboard has **Add nodes**, **Fleet control** (E-Stop, Unstop, Chaos monkey), and **AI Control**.

---

## Step 2: Show coordination (30 s)

Point out:

- **No central server** — only MQTT pub/sub (replace with Vertex for BUIDL).
- **Heterogeneous roles** — sentries (sectors A1, A2) and drones (recon, battery drain).
- **State sharing** — spectator (or the Flask dashboard) shows all nodes' status, sector, battery.

---

## Step 3: Chaos monkey (45 s)

In a second terminal:

```bash
cd track1_serve_and_protect
python chaos_monkey.py --kill 2
```

(If chaos_monkey doesn't find PIDs: `pip install psutil` or pass PIDs manually: `python chaos_monkey.py --pids 1234 1235 --kill 2`.)

**Narrative:** "We kill two nodes. The remaining nodes keep publishing; in a full implementation they reallocate sectors and tasks. No master to crash — the swarm degrades gracefully."

---

## Step 4: E-Stop and Unstop (30 s)

**Option A — from dashboard:** Open the **Fleet control** tab. Click **E-Stop** (fleet freezes). Then click **Unstop** (fleet resumes). Same effect as the CLI.

**Option B — from terminal:**

```bash
cd track1_serve_and_protect
python e_stop_trigger.py    # freeze fleet
python unstop_trigger.py   # resume fleet
```

**Narrative:** "One E-Stop message and every node freezes in under 50 ms. Unstop resumes them. No central controller — pure P2P safety."

Check the first terminal (run_swarm): nodes log "E-STOP received — FROZEN" then "UNSTOP received — RESUMED". If the Flask dashboard is running, it shows "FLEET FROZEN" then clears when Unstop is sent.

---

## Step 5: Wrap-up (15 s)

- "Serve and Protect Bastion: P2P military defence swarm. Coordinate, automate, secure — no middleman."
- Point to README for project overview and how to run the demo.

---

## For BUIDL submission

- Use **FoxMQ (Vertex)** for coordination: `python run_swarm.py --start-broker-foxmq`.
- Add **CRDT** for threat map in `state.py` and merge logic in nodes (optional).
- Optionally add **Toxiproxy** or **tc** to simulate packet loss and show robustness.
- Record a short video of: swarm → dashboard (Add nodes, Fleet control, AI Control) → E-Stop / Unstop → chaos, and submit link + repo to Discord.
