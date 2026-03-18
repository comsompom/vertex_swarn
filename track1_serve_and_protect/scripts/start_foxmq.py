"""
Start a single-node FoxMQ broker (Vertex-backed MQTT) for Serve and Protect Bastion.
FoxMQ is a decentralized, Byzantine fault-tolerant MQTT broker using Tashi Vertex.
See: https://docs.tashi.network/resources/foxmq and https://github.com/tashigg/foxmq

Usage:
  python scripts/start_foxmq.py [--foxmq-dir DIR] [--background]
  Or from run_swarm.py with --start-broker-foxmq.

Requires: FoxMQ binary in PATH or in --foxmq-dir. Download from:
  https://github.com/tashigg/foxmq/releases
"""

import argparse
import os
import platform
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TRACK_DIR = os.path.dirname(SCRIPT_DIR)
DEFAULT_FOXMQ_DIR = os.path.join(TRACK_DIR, "foxmq_broker")
FOXMQ_D = "foxmq.d"
ADDRESS_BOOK_TOML = "address-book.toml"
USERS_TOML = "users.toml"
KEY_0 = "key_0.pem"


def find_foxmq_binary(foxmq_dir: str) -> str | None:
    """Return path to foxmq executable, or None."""
    name = "foxmq.exe" if platform.system() == "Windows" else "foxmq"
    # In given dir
    path = os.path.join(foxmq_dir, name)
    if os.path.isfile(path):
        return path
    # In PATH
    which = "where" if platform.system() == "Windows" else "which"
    try:
        r = subprocess.run([which, name], capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip().split("\n")[0].strip()
    except Exception:
        pass
    return None


def ensure_foxmq_d(foxmq_dir: str, foxmq_bin: str) -> bool:
    """Create foxmq.d/ with address-book and allow-anonymous if missing. Return True on success."""
    foxmq_d = os.path.join(foxmq_dir, FOXMQ_D)
    os.makedirs(foxmq_d, exist_ok=True)
    address_book = os.path.join(foxmq_d, ADDRESS_BOOK_TOML)
    if not os.path.isfile(address_book):
        # Single node: 127.0.0.1:19793
        cmd = [
            foxmq_bin, "address-book", "from-range",
            "127.0.0.1", "19793", "19793",
        ]
        try:
            subprocess.run(cmd, cwd=foxmq_dir, check=True, capture_output=True, timeout=30)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            print("Failed to create FoxMQ address-book:", e, file=sys.stderr)
            return False
    users_path = os.path.join(foxmq_d, USERS_TOML)
    if not os.path.isfile(users_path):
        with open(users_path, "w") as f:
            f.write("[auth]\nallow-anonymous-login = true\n")
    return True


def run_foxmq(foxmq_dir: str, foxmq_bin: str, mqtt_port: int = 1883, background: bool = False) -> subprocess.Popen | None:
    """Start FoxMQ. On Windows use 127.0.0.1 for loopback. Return process handle if background."""
    key_path = os.path.join(FOXMQ_D, KEY_0)
    if platform.system() == "Windows":
        key_path = key_path.replace("/", "\\")
    args = [
        foxmq_bin, "run",
        "--secret-key-file=" + key_path,
        "--allow-anonymous-login",
        "--mqtt-addr=127.0.0.1:{}".format(mqtt_port),
        "--cluster-addr=127.0.0.1:19793",
    ]
    try:
        if background:
            kwargs = {
                "cwd": foxmq_dir,
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
            }
            if platform.system() == "Windows":
                kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
            else:
                kwargs["start_new_session"] = True
            proc = subprocess.Popen(args, **kwargs)
            return proc
        subprocess.run(args, cwd=foxmq_dir, check=True)
    except Exception as e:
        print("Failed to start FoxMQ:", e, file=sys.stderr)
        return None
    return None


def main():
    parser = argparse.ArgumentParser(description="Start FoxMQ broker (Vertex-backed MQTT)")
    parser.add_argument("--foxmq-dir", default=DEFAULT_FOXMQ_DIR, help="Directory containing foxmq binary and foxmq.d/")
    parser.add_argument("--mqtt-port", type=int, default=1883)
    parser.add_argument("--background", action="store_true", help="Run broker in background")
    parser.add_argument("--prepare-only", action="store_true", help="Only create foxmq.d/ and exit")
    args = parser.parse_args()
    foxmq_dir = os.path.abspath(args.foxmq_dir)
    os.makedirs(foxmq_dir, exist_ok=True)
    foxmq_bin = find_foxmq_binary(foxmq_dir)
    if not foxmq_bin:
        print("FoxMQ binary not found. Download from https://github.com/tashigg/foxmq/releases", file=sys.stderr)
        print("Extract foxmq (or foxmq.exe on Windows) into:", foxmq_dir, file=sys.stderr)
        sys.exit(1)
    if not ensure_foxmq_d(foxmq_dir, foxmq_bin):
        sys.exit(1)
    if args.prepare_only:
        print("FoxMQ config ready in", os.path.join(foxmq_dir, FOXMQ_D))
        return
    if args.background:
        proc = run_foxmq(foxmq_dir, foxmq_bin, args.mqtt_port, background=True)
        if proc:
            print("FoxMQ broker started in background (PID={}), MQTT on 127.0.0.1:{}".format(proc.pid, args.mqtt_port))
        else:
            sys.exit(1)
    else:
        print("Starting FoxMQ (Vertex-backed MQTT) on 127.0.0.1:{} ... Ctrl+C to stop.".format(args.mqtt_port))
        run_foxmq(foxmq_dir, foxmq_bin, args.mqtt_port, background=False)


if __name__ == "__main__":
    main()
