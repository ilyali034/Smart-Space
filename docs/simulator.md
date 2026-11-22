# Device and Gateway Simulator

For system testing without physical hardware: virtual devices plus a gateway that connects MQTT to the backend.

```
device_simulator ──MQTT──► broker ──MQTT──► device_gateway ──HTTP──► backend (FastAPI)
(virtual                     ▲                                          │
devices)                    └────────── MqttCommandDispatcher ◄────────┘  (commands)
```

| MQTT Topic (`{prefix}/{device_id}/…`) | Direction | Gateway Action |
|---|---|---|
| `commands` | backend → device | — (read only by the device) |
| `status` (retained, + Last Will) | device → | `PUT /devices/{slug}/availability` |
| `telemetry` (`readings`) | device → | `PUT /devices/{slug}/state` (triggered on change or once every `GATEWAY_HEARTBEAT_SECONDS`) |
| `ack` (`command_id`, `ok`) | device → | `POST /commands/{id}/ack`; duplicates are discarded | ## Quick Start

```bash
pip install -r requirements.txt            # from the repository root
docker compose up -d                       # postgres + mosquitto
alembic upgrade head
python scripts/create_token.py --name gateway --role gateway     # -> GATEWAY_API_TOKEN
python scripts/create_token.py --name admin   --role admin       # -> SIM_API_TOKEN
python scripts/create_token.py --name user    --role user        # for manual requests

uvicorn backend_engine.app:create_app --factory                  # 1. backend
GATEWAY_API_TOKEN=ss_... python -m device_gateway                # 2. gateway
SIM_API_URL=http://localhost:8000 SIM_API_TOKEN=ss_... python -m device_simulator   # 3. simulator
```
The simulator automatically registers devices with the backend (`POST /devices`) and retrieves the assigned `id`s.
Without `SIM_API_URL`/`SIM_API_TOKEN`, the IDs will be arbitrary, and the backend will not recognize them (the gateway will ignore them).
All scripts should be run from the repository root.

Verification:
```bash
curl -H "Authorization: Bearer $USER_TOKEN" localhost:8000/api/v1/devices            # availability: online
curl -X POST -H "Authorization: Bearer $USER_TOKEN" -H 'content-type: application/json' \
localhost:8000/api/v1/devices/living_lamp/command \
-d '{"command_id":"<uuid4>","action":"turn_on","parameters":{}}'                    # -> dispatched -> acknowledged
```

## Devices (`SIM_FLEET`)

| Fleet | Device | Type | Commands |
|---|---|---|---|
| living_room | `living_lamp` | smart_light | `turn_on`, `turn_off`, `set_brightness` (0–100) |
| living_room | `living_relay` | smart_relay | `turn_on`/`turn_off`; `turn_on` requires human confirmation |
| living_room | `living_temp`, `living_humidity` | sensors | telemetry only |
| kitchen | `kitchen_light`, `kitchen_plug`, `kitchen_temp` | light, plug, sensor | same as above |

The set of commands matches the Safety Engine action table (the test monitors for any discrepancies).
Each device is a separate MQTT connection with its own "Last Will" (just like a real device).

## Control and Failures

```bash
python -m device_simulator.control offline living_lamp      # device goes offline: status becomes 'offline', commands are ignored
python -m device_simulator.control online  living_lamp
python -m device_simulator.control crash   living_lamp      # abrupt disconnection (no DISCONNECT packet) -> broker publishes 'Will', device "reboots"
python -m device_simulator.control faults  living_lamp ack_delay=2 fail_next=1 drop_next=1 duplicate_ack=true
python -m device_simulator.control reset   living_lamp      # clear all faults
python -m device_simulator.control set     living_temp temperature=31.5
```
Use `*` in place of the slug to target all devices.

| Failure | Effect | What it tests |
|---|---|---|
| `ack_delay=N` | Device executes immediately, but the acknowledgment (ACK) is sent after N seconds | Verifies that the state updates before the command status changes (`dispatched` → `acknowledged`) |
| `fail_next=N` | For N commands, the ACK returns `ok=false` and the state remains unchanged | Verifies the `failed` status |
| `drop_next=N` | For N commands, the action is performed, but the ACK is lost | The command remains in the `dispatched` state, then transitions to `timed_out`. |
| `duplicate_ack=true` | Each acknowledgment (ACK) is sent twice | Deduplication is handled at the gateway level |
| `offline` / `crash` | Device is unreachable | The safety layer rejects commands (`device_offline`), and the availability status is updated |

Command redelivery (QoS 1) does not result in a second execution: the device remembers the `command_id` and re-sends the acknowledgment.

## Tests

```bash
export TEST_DATABASE_URL=postgresql+asyncpg://user:pw@localhost:5432/test   # Database is cleared
pytest tests/test_simulator.py tests/test_gateway.py          # Runs without a database or broker
pytest                                                          # Includes backend and E2E tests (requires PostgreSQL and a broker on localhost:1883)
```
E2E tests (`tests/test_e2e_mqtt.py`) launch the backend, gateway, and simulator within a single process, using a real broker.
Scenarios covered include: commands, relay acknowledgments, `failed` states, delayed or lost acknowledgments, duplicates, offline/crash events, and "Last Will" messages.
Broker configuration: `MQTT_TEST_HOST` / `MQTT_TEST_PORT`; if no broker is available, E2E tests are skipped.

## Limitations

- The gateway processes messages sequentially; if the backend is unreachable, a message is dropped after 3 attempts (approx. 3.5 seconds), with the event logged.
- TLS and MQTT authorization are not used in the tests (though they are supported via `M...`)