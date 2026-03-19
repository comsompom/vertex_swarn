"""Tests for state schema and E-Stop payload (state.py)."""
import json
import time
import pytest

import state


class TestMakeState:
    def test_required_fields(self):
        s = state.make_state("node-1", "sentry")
        assert s["node_id"] == "node-1"
        assert s["role"] == "sentry"
        assert "last_seen_ms" in s
        assert isinstance(s["last_seen_ms"], int)
        assert s["last_seen_ms"] <= int(time.time() * 1000) + 1000

    def test_defaults(self):
        s = state.make_state("n", "drone")
        assert s["status"] == "idle"
        assert s["sector_id"] is None
        assert s["battery"] == 100
        assert s["last_threat"] is None

    def test_full_args(self):
        s = state.make_state(
            node_id="sentry-2",
            role="sentry",
            status="patrol",
            sector_id="A3",
            battery=72,
            last_threat="sector-A3",
        )
        assert s["node_id"] == "sentry-2"
        assert s["role"] == "sentry"
        assert s["status"] == "patrol"
        assert s["sector_id"] == "A3"
        assert s["battery"] == 72
        assert s["last_threat"] == "sector-A3"


class TestStateJsonRoundtrip:
    def test_roundtrip(self):
        s = state.make_state("x", "sentry", "patrol", "A1", 80)
        js = state.state_to_json(s)
        back = state.json_to_state(js)
        assert back is not None
        assert back["node_id"] == s["node_id"]
        assert back["role"] == s["role"]
        assert back["battery"] == s["battery"]

    def test_json_to_state_invalid(self):
        assert state.json_to_state("not json") is None
        assert state.json_to_state("") is None
        assert state.json_to_state(None) is None


class TestEStopPayload:
    def test_make_e_stop_payload(self):
        p = state.make_e_stop_payload("sentry-1", "hold_fire")
        assert p["source"] == "sentry-1"
        assert p["reason"] == "hold_fire"
        assert "ts_ms" in p
        assert isinstance(p["ts_ms"], int)

    def test_parse_e_stop_valid(self):
        p = state.make_e_stop_payload("op", "cease")
        js = json.dumps(p)
        back = state.parse_e_stop(js)
        assert back is not None
        assert back["source"] == "op"
        assert back["reason"] == "cease"

    def test_parse_e_stop_invalid(self):
        assert state.parse_e_stop("invalid") is None
        assert state.parse_e_stop(None) is None


class TestUnstopPayload:
    def test_make_unstop_payload(self):
        p = state.make_unstop_payload("dashboard", "resume")
        assert p["source"] == "dashboard"
        assert p["reason"] == "resume"
        assert "ts_ms" in p
        assert isinstance(p["ts_ms"], int)

    def test_parse_unstop_valid(self):
        p = state.make_unstop_payload("op", "resume")
        js = json.dumps(p)
        back = state.parse_unstop(js)
        assert back is not None
        assert back["source"] == "op"
        assert back["reason"] == "resume"

    def test_parse_unstop_invalid(self):
        assert state.parse_unstop("invalid") is None
        assert state.parse_unstop(None) is None


class TestThreatEntry:
    def test_make_threat_entry(self):
        t = state.make_threat_entry("B2", 3, "drone-1")
        assert t["sector_id"] == "B2"
        assert t["severity"] == 3
        assert t["claimed_by"] == "drone-1"

    def test_make_threat_entry_no_claimant(self):
        t = state.make_threat_entry("A1", 1, None)
        assert t["claimed_by"] is None
