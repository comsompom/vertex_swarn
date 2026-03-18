"""Tests for node logic: state payloads and E-Stop handling (without real MQTT)."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import state


class TestSentryStatePayload:
    """Sentry nodes build state with role=sentry, status=patrol, sector_id set."""

    def test_sentry_payload_has_required_keys(self):
        payload = state.make_state(
            node_id="sentry-1",
            role=config.ROLE_SENTRY,
            status=config.STATUS_PATROL,
            sector_id="A1",
            battery=100,
        )
        assert payload["node_id"] == "sentry-1"
        assert payload["role"] == config.ROLE_SENTRY
        assert payload["status"] == config.STATUS_PATROL
        assert payload["sector_id"] == "A1"
        assert payload["battery"] == 100
        assert "last_seen_ms" in payload

    def test_sentry_state_serializable(self):
        payload = state.make_state("sentry-2", config.ROLE_SENTRY, config.STATUS_PATROL, "A2", 72)
        js = state.state_to_json(payload)
        back = state.json_to_state(js)
        assert back["role"] == config.ROLE_SENTRY
        assert back["sector_id"] == "A2"


class TestDroneStatePayload:
    """Drone nodes build state with role=drone; status changes when battery low."""

    def test_drone_payload_patrol_when_battery_high(self):
        payload = state.make_state(
            node_id="drone-1",
            role=config.ROLE_DRONE,
            status=config.STATUS_PATROL,
            sector_id=None,
            battery=80,
        )
        assert payload["role"] == config.ROLE_DRONE
        assert payload["status"] == config.STATUS_PATROL
        assert payload["sector_id"] is None
        assert payload["battery"] == 80

    def test_drone_low_battery_status(self):
        # In node_drone.py, status becomes "low_battery_handoff" when bat <= 15
        payload = state.make_state(
            node_id="drone-1",
            role=config.ROLE_DRONE,
            status="low_battery_handoff",
            sector_id=None,
            battery=10,
        )
        assert payload["battery"] == 10
        assert payload["status"] == "low_battery_handoff"


class TestEStopHandling:
    """E-Stop payload is parseable and contains source/reason."""

    def test_e_stop_parse_matches_sentry_expectation(self):
        # node_sentry and node_drone expect payload with "source" key
        p = state.make_e_stop_payload("sentry-1", "hold_fire")
        assert "source" in p
        assert p["source"] == "sentry-1"
        assert "reason" in p
        js = __import__("json").dumps(p)
        parsed = state.parse_e_stop(js)
        assert parsed is not None
        assert parsed["source"] == "sentry-1"

    def test_e_stop_parse(self):
        p = state.make_e_stop_payload("human-operator", "hold_fire")
        js = __import__("json").dumps(p)
        parsed = state.parse_e_stop(js)
        assert parsed is not None
        assert parsed["source"] == "human-operator"
        assert parsed["reason"] == "hold_fire"
