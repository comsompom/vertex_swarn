# FoxMQ (Vertex-backed MQTT) for Serve and Protect Bastion

For the **Vertex Swarm Challenge**, coordination must use **Vertex 2.0 or FoxMQ**. FoxMQ is a decentralized, Byzantine fault-tolerant MQTT broker powered by the Tashi Consensus Engine. Our Python nodes connect to it with standard MQTT (paho-mqtt); the broker layer is Vertex/FoxMQ instead of plain Mosquitto.

## Quick start

1. **Download FoxMQ** (one-time)  
   Get the binary for your OS from [GitHub Releases](https://github.com/tashigg/foxmq/releases).  
   Extract `foxmq` (or `foxmq.exe` on Windows) into `track1_serve_and_protect/foxmq_broker/` (or any folder you prefer).

2. **Start FoxMQ and the swarm**  
   From `track1_serve_and_protect/`:

   ```bash
   python run_swarm.py --sentries 2 --drones 2 --start-broker-foxmq
   ```

   If the FoxMQ binary is in a different directory:

   ```bash
   python run_swarm.py --sentries 2 --drones 2 --start-broker-foxmq --foxmq-dir C:\path\to\foxmq_broker
   ```

   The first run creates `foxmq_broker/foxmq.d/` (address-book and keys for a single-node cluster) and starts FoxMQ on `127.0.0.1:1883`. The swarm then connects to it.

3. **Or start FoxMQ manually**  
   In one terminal:

   ```bash
   python scripts/start_foxmq.py --background
   ```

   In another:

   ```bash
   python run_swarm.py --sentries 2 --drones 2
   ```

## What gets created

- `foxmq_broker/foxmq.d/` — generated on first run:
  - `address-book.toml` — single-node cluster (127.0.0.1:19793)
  - `key_0.pem` — node key
  - `users.toml` — allow-anonymous-login so our clients need no credentials

## Docs

- [FoxMQ overview](https://docs.tashi.network/resources/foxmq)
- [Quick start (direct binary)](https://docs.tashi.network/resources/foxmq/quick-start-direct)
- [FoxMQ GitHub](https://github.com/tashigg/foxmq)

## Compliance

Using FoxMQ as the broker satisfies the requirement that **core coordination is a new, meaningful implementation of Vertex 2.0 and/or FoxMQ**: all pub/sub (state, E-Stop, AI suggestions) goes through FoxMQ, which uses Vertex for consensus and transport.
