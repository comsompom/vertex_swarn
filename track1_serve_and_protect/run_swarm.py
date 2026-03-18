"""
Launch Serve and Protect Bastion swarm: N sentries + M drones + 1 spectator.
Use FoxMQ (Vertex-backed MQTT) via --start-broker-foxmq for hackathon submission; or any MQTT broker (e.g. Mosquitto) for local demo.
"""

import argparse
import socket
import subprocess
import sys
import time

# Add this dir so subprocess finds modules
import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)

import config


def broker_reachable(host: str, port: int, timeout: float = 2.0) -> bool:
    """Return True if a TCP connection to host:port succeeds (e.g. MQTT broker)."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.error, OSError):
        return False


BROKER_CONTAINER_NAME = "bastion-mqtt"


def _print_broker_help(broker: str, port: int) -> None:
    print("Error: MQTT broker is not reachable at {}:{}.".format(broker, port), file=sys.stderr)
    print("Start a broker first, for example:", file=sys.stderr)
    print("  mosquitto -v", file=sys.stderr)
    print("  or: docker run -p 1883:1883 eclipse-mosquitto", file=sys.stderr)
    print("  or (Vertex/FoxMQ): python scripts/start_foxmq.py --background", file=sys.stderr)
    print("Then run this script again. Use --skip-broker-check to start nodes anyway.", file=sys.stderr)


def start_broker_foxmq(port: int, foxmq_dir: str | None = None) -> bool:
    """Start FoxMQ (Vertex-backed MQTT) via scripts/start_foxmq.py. Return True if broker becomes reachable."""
    if foxmq_dir is None:
        foxmq_dir = os.path.join(SCRIPT_DIR, "foxmq_broker")
    start_script = os.path.join(SCRIPT_DIR, "scripts", "start_foxmq.py")
    if not os.path.isfile(start_script):
        return False

    def wait_for_broker():
        for _ in range(15):
            time.sleep(1)
            if broker_reachable("127.0.0.1", port, timeout=1.0):
                return True
        return False

    try:
        proc = subprocess.Popen(
            [sys.executable, start_script, "--foxmq-dir", foxmq_dir, "--mqtt-port", str(port), "--background"],
            cwd=SCRIPT_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        proc.wait(timeout=30)
        return wait_for_broker()
    except Exception:
        return False


def start_broker_docker(port: int) -> bool:
    """Try to start eclipse-mosquitto in Docker. Return True if broker becomes reachable."""
    def wait_for_broker():
        for _ in range(10):
            time.sleep(1)
            if broker_reachable("127.0.0.1", port, timeout=1.0):
                return True
        return False
    try:
        r = subprocess.run(
            [
                "docker", "run", "-d",
                "-p", "{}:1883".format(port),
                "--name", BROKER_CONTAINER_NAME,
                "eclipse-mosquitto",
            ],
            capture_output=True,
            timeout=30,
            check=False,
        )
        if r.returncode != 0 and b"already in use" in (r.stderr or b""):
            subprocess.run(["docker", "start", BROKER_CONTAINER_NAME], capture_output=True, timeout=10, check=False)
        return wait_for_broker()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def main():
    parser = argparse.ArgumentParser(description="Run Bastion swarm")
    parser.add_argument("--sentries", type=int, default=config.DEFAULT_SENTRIES)
    parser.add_argument("--drones", type=int, default=config.DEFAULT_DRONES)
    parser.add_argument("--broker", default=config.MQTT_BROKER)
    parser.add_argument("--port", type=int, default=config.MQTT_PORT)
    parser.add_argument("--skip-broker-check", action="store_true", help="Do not check if MQTT broker is reachable before starting nodes")
    parser.add_argument("--start-broker-docker", action="store_true", dest="start_broker_docker",
                        help="If broker is not running, try to start it with Docker (eclipse-mosquitto)")
    parser.add_argument("--start-broker-foxmq", action="store_true", dest="start_broker_foxmq",
                        help="If broker is not running, try to start FoxMQ (Vertex-backed MQTT). Requires FoxMQ binary.")
    parser.add_argument("--foxmq-dir", default=None, help="Directory for FoxMQ binary and foxmq.d/ (with --start-broker-foxmq)")
    args = parser.parse_args()

    if not args.skip_broker_check and not broker_reachable(args.broker, args.port):
        started = False
        if args.broker in ("127.0.0.1", "localhost") and args.port == 1883:
            if args.start_broker_foxmq:
                print("Broker not reachable. Trying to start FoxMQ (Vertex-backed MQTT)...")
                started = start_broker_foxmq(args.port, args.foxmq_dir)
                if started:
                    print("FoxMQ started. Launching swarm...")
            if not started and args.start_broker_docker:
                print("Broker not reachable. Trying to start MQTT broker with Docker...")
                started = start_broker_docker(args.port)
                if started:
                    print("Broker started. Launching swarm...")
        if not started:
            _print_broker_help(args.broker, args.port)
            if not args.start_broker_foxmq and not args.start_broker_docker:
                print("Tip: use --start-broker-foxmq for Vertex/FoxMQ or --start-broker-docker for Mosquitto.", file=sys.stderr)
            sys.exit(1)

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
