"""
Launch Serve and Protect Bastion swarm: N sentries + M drones + 1 spectator.
For BUIDL submission, wire to Vertex 2.0; here we use MQTT (FoxMQ-compatible) for local demo.
"""

import argparse
import subprocess
import sys
import time

# Add this dir so subprocess finds modules
import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)

import config


def main():
    parser = argparse.ArgumentParser(description="Run Bastion swarm")
    parser.add_argument("--sentries", type=int, default=config.DEFAULT_SENTRIES)
    parser.add_argument("--drones", type=int, default=config.DEFAULT_DRONES)
    parser.add_argument("--broker", default=config.MQTT_BROKER)
    parser.add_argument("--port", type=int, default=config.MQTT_PORT)
    args = parser.parse_args()

    procs = []
    sectors = ["A1", "A2", "A3", "B1", "B2"]

    for i in range(args.sentries):
        node_id = f"sentry-{i+1}"
        sector = sectors[i % len(sectors)]
        p = subprocess.Popen(
            [sys.executable, "node_sentry.py", "--id", node_id, "--sector", sector, "--broker", args.broker, "--port", str(args.port)],
            cwd=SCRIPT_DIR,
        )
        procs.append(("sentry", node_id, p))
        print(f"Started {node_id} (sector {sector}) PID={p.pid}")

    for i in range(args.drones):
        node_id = f"drone-{i+1}"
        p = subprocess.Popen(
            [sys.executable, "node_drone.py", "--id", node_id, "--broker", args.broker, "--port", str(args.port)],
            cwd=SCRIPT_DIR,
        )
        procs.append(("drone", node_id, p))
        print(f"Started {node_id} PID={p.pid}")

    p = subprocess.Popen(
        [sys.executable, "node_spectator.py", "--broker", args.broker, "--port", str(args.port)],
        cwd=SCRIPT_DIR,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    procs.append(("spectator", "spectator", p))
    print(f"Started spectator PID={p.pid}")

    print("\nSwarm running. Use chaos_monkey.py to kill nodes, or e_stop_trigger.py to trigger E-Stop. Ctrl+C to stop.\n")
    try:
        while True:
            time.sleep(5)
            for role, name, proc in procs:
                if proc.poll() is not None:
                    print(f"[{name}] exited with {proc.returncode}")
    except KeyboardInterrupt:
        for _, name, proc in procs:
            proc.terminate()
            print(f"Stopped {name}")


if __name__ == "__main__":
    main()
