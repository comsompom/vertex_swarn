"""Tests for FoxMQ startup script (scripts/start_foxmq.py)."""
import os
import subprocess
import sys
import tempfile

import pytest

# Package root (track1_serve_and_protect)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestStartFoxMQ:
    def test_script_exits_nonzero_when_binary_missing(self):
        """start_foxmq.py exits with 1 when FoxMQ binary is not found."""
        script = os.path.join(ROOT, "scripts", "start_foxmq.py")
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run(
                [sys.executable, script, "--foxmq-dir", d, "--prepare-only"],
                capture_output=True,
                text=True,
                cwd=ROOT,
                timeout=10,
            )
            assert r.returncode != 0
            assert "not found" in (r.stderr or "") or "FoxMQ" in (r.stderr or "")
