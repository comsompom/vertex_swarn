"""
Tashi Vertex P2P manager for drone swarm coordination.
Based on: https://github.com/tashigit/airsim-vertex-starter-kit
Manages multiple Tashi Vertex nodes (drone-comm binaries) for peer-to-peer state sync.
"""

import json
import os
import re
import platform
import subprocess
import threading
import time


class TashiDroneNode:
    """Manages a single Tashi Vertex node (one process per drone)."""

    def __init__(self, node_id, bind_addr, secret_key, peer_list, lib_path, bin_path, is_windows):
        self.node_id = node_id
        self.bind_addr = bind_addr
        self.secret_key = secret_key
        self.peer_list = peer_list
        self.lib_path = lib_path
        self.bin_path = bin_path
        self.is_windows = is_windows
        self.process = None
        self.is_running = False
        self.on_message_callback = None

    def start(self):
        peer_args = " ".join([f"-P {p}" for p in self.peer_list])

        if self.is_windows:
            cmd = f'wsl bash -l -c "export LD_LIBRARY_PATH={self.lib_path}:$LD_LIBRARY_PATH && {self.bin_path} -B {self.bind_addr} -K {self.secret_key} {peer_args}"'
        else:
            cmd = f'export LD_LIBRARY_PATH={self.lib_path}:$LD_LIBRARY_PATH && {self.bin_path} -B {self.bind_addr} -K {self.secret_key} {peer_args}'

        self.process = subprocess.Popen(
            cmd,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        self.is_running = True
        threading.Thread(target=self._read_stdout, daemon=True).start()

    def _read_stdout(self):
        while self.is_running and self.process:
            line = self.process.stdout.readline()
            if not line:
                break
            line = line.strip()
            if line.startswith("RX_TX:"):
                msg = line.replace("RX_TX:", "").strip().strip("\x00")
                if self.on_message_callback:
                    self.on_message_callback(self.node_id, msg)
            elif "DRONE_COMM_NODE_READY" in line:
                print(f"[{self.node_id}] P2P Ready.")

    def send(self, message):
        if self.process and self.process.poll() is None:
            try:
                self.process.stdin.write(message + "\n")
                self.process.stdin.flush()
                return True
            except Exception:
                pass
        return False

    def stop(self):
        self.is_running = False
        if self.process:
            try:
                self.process.kill()
            except Exception:
                pass
            self.process = None


class TashiStarterManager:
    """
    Simplified P2P manager for the warm up (Stateful Handshake).
    Expects tashi-vertex-rs built with examples: drone-comm, key-generate.
    """

    def __init__(self, node_ids, base_port=9500, tashi_path=None):
        if tashi_path is None:
            tashi_path = os.environ.get("TASHI_VERTEX_PATH", "../tashi-vertex-rs")
        self.node_ids = node_ids
        self.base_port = base_port
        self.tashi_path = os.path.abspath(tashi_path)
        self.nodes = {}
        self.keys = {}
        self.peers = []
        self.is_windows = platform.system() == "Windows"

        # Path conversion for WSL if on Windows
        if self.is_windows:
            drive_match = re.match(r"^([A-Za-z]):", self.tashi_path)
            if drive_match:
                wsl_root = f"/mnt/{drive_match.group(1).lower()}{self.tashi_path[2:].replace(os.sep, '/')}"
            else:
                wsl_root = self.tashi_path.replace(os.sep, "/")
            self.lib_path = f"{wsl_root}/lib"
            self.bin_path = f"{wsl_root}/target/debug/examples/drone-comm"
            self.key_gen_path = f"{wsl_root}/target/debug/examples/key-generate"
        else:
            self.lib_path = os.path.join(self.tashi_path, "lib")
            self.bin_path = os.path.join(self.tashi_path, "target/debug/examples/drone-comm")
            self.key_gen_path = os.path.join(self.tashi_path, "target/debug/examples/key-generate")

    def setup(self):
        """Clean ports and generate keys for each node."""
        print(f"Cleaning ports {self.base_port}...")
        if self.is_windows:
            ports = " ".join([f"{self.base_port + i}/tcp" for i in range(len(self.node_ids))])
            subprocess.run(f'wsl bash -l -c "fuser -k {ports} || true"', shell=True, capture_output=True)
        else:
            for port in range(self.base_port, self.base_port + len(self.node_ids)):
                subprocess.run(f"lsof -ti:{port} | xargs kill -9 || true", shell=True, capture_output=True)

        for i, name in enumerate(self.node_ids):
            if self.is_windows:
                cmd = f'wsl bash -l -c "export LD_LIBRARY_PATH={self.lib_path}:$LD_LIBRARY_PATH && {self.key_gen_path}"'
            else:
                cmd = f'export LD_LIBRARY_PATH={self.lib_path}:$LD_LIBRARY_PATH && {self.key_gen_path}'
            res = subprocess.check_output(cmd, shell=True, text=True)
            sec = re.search(r"Secret:\s+(\S+)", res).group(1)
            pub = re.search(r"Public:\s+(\S+)", res).group(1)
            self.keys[name] = (sec, pub)
            self.peers.append(f"{pub}@127.0.0.1:{self.base_port + i}")

    def start(self, callback):
        """Start all nodes; callback(node_id, msg) is invoked when a node receives a message."""
        for i, name in enumerate(self.node_ids):
            node = TashiDroneNode(
                name,
                f"127.0.0.1:{self.base_port + i}",
                self.keys[name][0],
                self.peers,
                self.lib_path,
                self.bin_path,
                self.is_windows,
            )
            node.on_message_callback = callback
            node.start()
            self.nodes[name] = node
        time.sleep(1)

    def broadcast(self, from_node, msg):
        """Send a message from the given node (broadcasts to P2P mesh)."""
        if from_node in self.nodes:
            return self.nodes[from_node].send(msg)
        return False

    def shutdown(self):
        """Stop all nodes."""
        for node in self.nodes.values():
            node.stop()
