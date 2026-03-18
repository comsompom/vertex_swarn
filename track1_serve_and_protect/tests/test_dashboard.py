"""Tests for Flask dashboard (API shape, no broker required)."""
import sys
import os

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
