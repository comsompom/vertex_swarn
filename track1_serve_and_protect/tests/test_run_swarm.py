"""Tests for run_swarm (subprocess args, sector assignment)."""
import sys
import os
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import run_swarm


class TestRunSwarmLogic:
    def test_sector_assignment(self):
        sectors = ["A1", "A2", "A3", "B1", "B2"]
        for i in range(5):
            sector = sectors[i % len(sectors)]
            assert sector in ("A1", "A2", "A3", "B1", "B2")
        assert sectors[0] == "A1"
        assert sectors[1] == "A2"

    def test_node_ids_generated(self):
        for i in range(3):
            node_id = f"sentry-{i+1}"
            assert node_id in ("sentry-1", "sentry-2", "sentry-3")
        for i in range(2):
            node_id = f"drone-{i+1}"
            assert node_id in ("drone-1", "drone-2")

    @patch("run_swarm.subprocess.Popen")
    def test_main_launches_sentries_drones_spectator(self, mock_popen):
        mock_proc = MagicMock(pid=12345)
        mock_proc.poll.return_value = None
        mock_proc.terminate = MagicMock()
        mock_popen.return_value = mock_proc
        with patch("run_swarm.time.sleep", side_effect=[None, KeyboardInterrupt]):
            with patch("run_swarm.sys.argv", ["run_swarm.py", "--sentries", "1", "--drones", "1"]):
                try:
                    run_swarm.main()
                except KeyboardInterrupt:
                    pass
        calls = mock_popen.call_args_list
        assert len(calls) == 3  # 1 sentry, 1 drone, 1 spectator
        cmd_sentry = calls[0][0][0]
        cmd_drone = calls[1][0][0]
        cmd_spectator = calls[2][0][0]
        assert "node_sentry.py" in cmd_sentry
        assert "sentry-1" in cmd_sentry
        assert "A1" in cmd_sentry
        assert "node_drone.py" in cmd_drone
        assert "drone-1" in cmd_drone
        assert "node_spectator.py" in cmd_spectator
