"""Tests for Flask dashboard (API shape, no broker required)."""
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


class TestDashboardAPI:
    """Test dashboard app and /api/state response shape."""

    def test_app_exists(self):
        from web.dashboard import app
        assert app is not None

    def test_api_state_returns_json(self):
        from web.dashboard import app
        with app.test_client() as client:
            r = client.get("/api/state")
        assert r.status_code == 200
        assert r.content_type == "application/json"
        data = r.get_json()
        assert "nodes" in data
        assert "e_stop_active" in data
        assert "last_ai_suggestion" in data
        assert isinstance(data["nodes"], list)
        assert isinstance(data["e_stop_active"], bool)

    def test_index_returns_html(self):
        from web.dashboard import app
        with app.test_client() as client:
            r = client.get("/")
        assert r.status_code == 200
        assert "text/html" in r.content_type
        assert b"Serve and Protect Bastion" in r.data
        assert b"Swarm" in r.data or b"dashboard" in r.data.lower()

    def test_api_nodes_add_requires_post(self):
        from web.dashboard import app
        with app.test_client() as client:
            r = client.get("/api/nodes/add")
        assert r.status_code == 405

    def test_api_nodes_add_rejects_invalid_role(self):
        from web.dashboard import app
        with app.test_client() as client:
            r = client.post("/api/nodes/add", json={"role": "invalid"}, content_type="application/json")
        assert r.status_code == 400
        data = r.get_json()
        assert data.get("ok") is False
        assert "error" in data

    @patch("web.dashboard._spawn_node")
    def test_api_nodes_add_spawns_drone(self, mock_spawn):
        mock_spawn.return_value = MagicMock(pid=99999)
        from web.dashboard import app
        with app.test_client() as client:
            r = client.post("/api/nodes/add", json={"role": "drone", "count": 1}, content_type="application/json")
        assert r.status_code == 200
        data = r.get_json()
        assert data.get("ok") is True
        assert "added" in data
        assert len(data["added"]) == 1
        assert data["added"][0]["role"] == "drone"
        assert "node_id" in data["added"][0]

    def test_api_ai_control_list_strategies(self):
        from web.dashboard import app
        with app.test_client() as client:
            r = client.get("/api/ai-control")
        assert r.status_code == 200
        data = r.get_json()
        assert data.get("ok") is True
        assert "strategies" in data
        assert any(s["id"] == "handoff" for s in data["strategies"])

    @patch("web.dashboard.mqtt")
    def test_api_ai_control_run_handoff(self, mock_mqtt):
        mock_mqtt.Client.return_value.connect = MagicMock()
        mock_mqtt.Client.return_value.publish = MagicMock()
        mock_mqtt.Client.return_value.disconnect = MagicMock()
        from web.dashboard import app
        with app.test_client() as client:
            r = client.post("/api/ai-control", json={"strategy": "handoff"}, content_type="application/json")
        assert r.status_code == 200
        data = r.get_json()
        assert data.get("ok") is True
        assert "recommendation" in data
        assert data.get("strategy") == "handoff"

    @patch("web.dashboard.mqtt")
    def test_api_fleet_e_stop(self, mock_mqtt):
        mock_mqtt.Client.return_value.connect = MagicMock()
        mock_mqtt.Client.return_value.publish = MagicMock()
        mock_mqtt.Client.return_value.disconnect = MagicMock()
        from web.dashboard import app
        with app.test_client() as client:
            r = client.post("/api/fleet/e-stop")
        assert r.status_code == 200
        data = r.get_json()
        assert data.get("ok") is True
        assert "message" in data

    @patch("web.dashboard.mqtt")
    def test_api_fleet_unstop(self, mock_mqtt):
        mock_mqtt.Client.return_value.connect = MagicMock()
        mock_mqtt.Client.return_value.publish = MagicMock()
        mock_mqtt.Client.return_value.disconnect = MagicMock()
        from web.dashboard import app
        with app.test_client() as client:
            r = client.post("/api/fleet/unstop")
        assert r.status_code == 200
        data = r.get_json()
        assert data.get("ok") is True
        assert "message" in data

    @patch("web.dashboard.subprocess.run")
    def test_api_fleet_chaos_monkey(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="Killed PID 123\n", stderr="")
        from web.dashboard import app
        with app.test_client() as client:
            r = client.post("/api/fleet/chaos-monkey", json={"kill": 2}, content_type="application/json")
        assert r.status_code == 200
        data = r.get_json()
        assert data.get("ok") is True
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "--kill" in call_args
        assert "2" in call_args
