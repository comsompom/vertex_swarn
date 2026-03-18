"""
Chaos monkey for Serve and Protect Bastion: kill random swarm nodes to prove self-healing.
Run while run_swarm.py is active; optionally pass PIDs or let it discover from process list.
"""

import argparse
import os
import random
import signal
import sys
import time

# On Windows we may not have psutil; fallback to manual PIDs
try:
    import psutil
except ImportError:
    psutil = None


def find_swarm_pids():
    """Find PIDs of running node_*.py and run_swarm.py (children)."""
    if not psutil:
        return []
    my_pid = os.getpid()
    pids = []
    for p in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmd = p.info.get("cmdline") or []
            if not cmd:
                continue
            cmd_str = " ".join(cmd).lower()
            if "run_swarm" in cmd_str and "node_sentry" not in cmd_str and "node_drone" not in cmd_str:
                continue  # skip the launcher itself
            if ("node_sentry" in cmd_str or "node_drone" in cmd_str) and "python" in cmd_str:
                if p.pid != my_pid:
                    pids.append(p.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return pids


def main():
    parser = argparse.ArgumentParser(description="Chaos monkey: kill random Bastion nodes")
    parser.add_argument("--pids", nargs="+", type=int, help="PIDs to choose from (otherwise auto-detect)")
    parser.add_argument("--kill", type=int, default=1, help="Number of random nodes to kill")
    parser.add_argument("--interval", type=float, default=0, help="Loop and kill every N seconds (0 = once)")
    args = parser.parse_args()

    if args.pids:
        pids = args.pids
    else:
        pids = find_swarm_pids()
        if not pids:
            print("No swarm node PIDs found. Start run_swarm.py first, or pass --pids PID1 PID2 ...", file=sys.stderr)
            sys.exit(1)
        print(f"Found {len(pids)} node(s): {pids}")

    k = min(args.kill, len(pids))
    to_kill = random.sample(pids, k)
    for pid in to_kill:
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"Killed PID {pid}")
        except ProcessLookupError:
            print(f"PID {pid} already gone")
        except PermissionError:
            print(f"No permission to kill {pid}")

    if args.interval > 0:
        while True:
            time.sleep(args.interval)
            pids = args.pids or find_swarm_pids()
            if not pids:
                break
            to_kill = random.sample(pids, min(1, len(pids)))
            for pid in to_kill:
                try:
                    os.kill(pid, signal.SIGTERM)
                    print(f"Killed PID {pid}")
                except (ProcessLookupError, PermissionError):
                    pass


if __name__ == "__main__":
    main()
