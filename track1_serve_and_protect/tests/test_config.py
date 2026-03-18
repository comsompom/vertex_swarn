"""Tests for config (topics, roles, timing)."""
import os

import config


class TestConfigTopics:
    def test_topic_prefix(self):
        assert config.TOPIC_PREFIX == "bastion/serve_and_protect"

    def test_state_topic_template(self):
        assert "node_id" in config.STATE_TOPIC_TEMPLATE
        assert config.STATE_TOPIC_TEMPLATE.format(node_id="sentry-1") == "bastion/serve_and_protect/state/sentry-1"

    def test_state_subscribe(self):
        assert config.STATE_TOPIC_SUBSCRIBE == "bastion/serve_and_protect/state/+"

    def test_e_stop_topic(self):
        assert config.E_STOP_TOPIC == "bastion/serve_and_protect/e_stop"

    def test_threat_map_topic(self):
        assert "threat_map" in config.THREAT_MAP_TOPIC


class TestConfigRoles:
    def test_roles_defined(self):
        assert config.ROLE_SENTRY == "sentry"
        assert config.ROLE_DRONE == "drone"
        assert config.ROLE_SPECTATOR == "spectator"

    def test_statuses_defined(self):
        assert config.STATUS_PATROL == "patrol"
        assert config.STATUS_RESPONDING == "responding"
        assert config.STATUS_IDLE == "idle"
        assert config.STATUS_FROZEN == "frozen"


class TestConfigTiming:
    def test_heartbeat_interval(self):
        assert config.HEARTBEAT_INTERVAL > 0

    def test_e_stop_timeout_ms(self):
        assert config.E_STOP_TIMEOUT_MS == 50

    def test_default_swarm_size(self):
        assert config.DEFAULT_SENTRIES >= 1
        assert config.DEFAULT_DRONES >= 1


class TestConfigBroker:
    def test_broker_default_or_env(self):
        # Broker is a non-empty string (default 127.0.0.1 or from BASTION_BROKER)
        assert isinstance(config.MQTT_BROKER, str)
        assert len(config.MQTT_BROKER) > 0

    def test_port_integer(self):
        assert isinstance(config.MQTT_PORT, int)
        assert 1 <= config.MQTT_PORT <= 65535
