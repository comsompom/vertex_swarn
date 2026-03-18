"""Tests for e_stop_trigger: payload construction and topic."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import state


class TestEStopTriggerPayload:
    def test_uses_make_e_stop_payload(self):
        payload = state.make_e_stop_payload("human-operator", "hold_fire")
        assert payload["source"] == "human-operator"
        assert payload["reason"] == "hold_fire"
        assert "ts_ms" in payload

    def test_e_stop_topic_defined(self):
        assert config.E_STOP_TOPIC == "bastion/serve_and_protect/e_stop"
