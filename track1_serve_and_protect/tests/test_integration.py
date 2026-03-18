"""Integration tests: require MQTT broker on 127.0.0.1:1883. Skip if unavailable."""
import sys
import os
import socket

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def broker_available():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect(("127.0.0.1", 1883))
        s.close()
        return True
    except (socket.error, OSError):
        return False


@pytest.mark.skipif(not broker_available(), reason="MQTT broker not running on 127.0.0.1:1883")
class TestWithBroker:
    """Run only when a broker is available (e.g. mosquitto -v)."""

    def test_connect_and_publish_e_stop(self):
        import paho.mqtt.client as mqtt
        import config
        import state
        import json

        received = []

        def on_connect(client, userdata, flags, reason_code, properties=None):
            client.subscribe(config.E_STOP_TOPIC)

        def on_message(client, userdata, msg):
            received.append(msg)

        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="test-integration")
        client.on_connect = on_connect
        client.on_message = on_message
        client.connect(config.MQTT_BROKER, config.MQTT_PORT, 60)
        client.loop_start()
        try:
            payload = state.make_e_stop_payload("test", "hold_fire")
            client.publish(config.E_STOP_TOPIC, json.dumps(payload), qos=1)
            import time
            time.sleep(1)
        finally:
            client.loop_stop()
            client.disconnect()
        assert len(received) == 1
        data = json.loads(received[0].payload.decode())
        assert data["source"] == "test"
        assert data["reason"] == "hold_fire"
