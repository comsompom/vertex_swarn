"""Tests for chaos_monkey (find_swarm_pids, kill selection)."""
import sys
import os

# Import chaos_monkey from parent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chaos_monkey


class TestFindSwarmPids:
    def test_returns_list(self):
        result = chaos_monkey.find_swarm_pids()
        assert isinstance(result, list)

    def test_excludes_self(self):
        # When psutil is available, our own PID might appear in process list but we exclude it
        result = chaos_monkey.find_swarm_pids()
        my_pid = os.getpid()
        assert my_pid not in result or not result  # either we're not in list or list is empty

    def test_with_mocked_psutil(self, monkeypatch):
        # Simulate psutil not installed
        monkeypatch.setattr(chaos_monkey, "psutil", None)
        assert chaos_monkey.find_swarm_pids() == []
