# Smart Space

A smart-home platform built around a safety-first command pipeline: every command to a device is validated by a
**Safety Engine**, may require **human confirmation**, is delivered over **MQTT**, and is only considered done when the
**device acknowledges** it.

This repository contains:

| Part | What it is |
|---|---|
| **Backend** (`src/backend_engine`) | FastAPI modular monolith: devices, commands, Safety Engine, audit log, token auth |
| **Device gateway** (`device_gateway/`) | Separate process that turns device MQTT traffic into backend HTTP calls |
| **Device simulator** (`device_simulator/`) | Virtual devices with fault injection, for testing the whole system without hardware |
| **Desktop client** (`apps/smart_space_desktop`) | Windows desktop UI (PySide6), foundation in progress (see [docs/desktop](docs/desktop)) |
| **Infrastructure** (`docker-compose.yml`, `deploy/`) | PostgreSQL 16 and an Eclipse Mosquitto broker for local development |

## Table of contents

- [Architecture](#architecture)
- [Repository layout](#repository-layout)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [API overview](#api-overview)
- [Command lifecycle and the Safety Engine](#command-lifecycle-and-the-safety-engine)
- [MQTT contract](#mqtt-contract)
- [Device simulator](#device-simulator)
- [Testing](#testing)
- [Development rules](#development-rules)
- [Security notes](#security-notes)
- [Known gaps](#known-gaps)
- [Documentation index](#documentation-index)

## Architecture

```
   Desktop client ──┐   HTTP (Bearer token)
   curl / others  ──┼──────────────────────────┐
                    │                          ▼
                    │              ┌───────────────────────┐        ┌────────────┐
                    │              │   Backend (FastAPI)   │◄──────►│ PostgreSQL │
                    │              │ devices · commands ·  │        └────────────┘
                    │              │ safety · audit · auth │
                    │              └───────┬───────▲───────┘
                    │      publish commands│       │ PUT availability / state
                    │      (QoS 1)         │       │ POST command ack  (HTTP, role "gateway")
                    │                      ▼       │
                    │              ┌───────────────┴───────┐
                    │              │      MQTT broker      │
                    │              └───────┬───────▲───────┘
                    │      commands        │       │ status · telemetry · ack
                    │                      ▼       │
                    │      ┌───────────────────────┴────────────┐
                    │      │ Real devices  or  device_simulator │
                    │      └────────────────────────────────────┘
                    └─ device_gateway sits between the broker and the backend
```

Key principles:

- **The backend is the single source of truth** for devices, state, commands, safety decisions and audit.
  Clients never talk to PostgreSQL or the MQTT broker directly.
- **Accepted is not executed.** A command moves to `dispatched` when it is published to MQTT. Only a device
  acknowledgement (reported through the gateway) makes it `acknowledged` (or `failed`).
- **Modular monolith** with enforced import boundaries (see [Development rules](#development-rules) and
  [ADR 0001](docs/adr/0001-modular-monolith.md)).

## Repository layout

```
src/backend_engine/
  app.py              create_app(), lifespan, wiring
  api/                HTTP only: routers (health, devices, commands) and error mapping
  shared/             config, events (in-process bus), auth (tokens, roles), storage (Base, unit of work)
  modules/
    audit/            audit log entity + writer
    devices/          dto, entity, repository, uow, service, events, exceptions
    commands/         command lifecycle, MQTT dispatcher, service
    safety/           rules, action table, evaluation
device_gateway/       MQTT -> backend HTTP bridge (separate process)
device_simulator/     virtual devices, fault injection, control CLI
migrations/           Alembic migrations
scripts/              create_token.py
deploy/mosquitto/     broker configuration (development)
docs/                 ADRs, MQTT contract, simulator guide, desktop docs
tests/                unit, integration and end-to-end tests
apps/                 desktop client
```

## Quick start

### Prerequisites

- Python 3.11+
- Docker (for PostgreSQL and the MQTT broker), or your own PostgreSQL 16 and Mosquitto instances

All commands below run from the repository root. On Windows PowerShell, replace `export NAME=value` with
`$env:NAME = "value"`.

### 1. Infrastructure and backend

```bash
cp .env.example .env                       # set real passwords
docker compose up -d postgres mqtt         # PostgreSQL 16 + Mosquitto

pip install -e ".[dev]"                    # or: pip install -r requirements.txt

export DATABASE_URL=postgresql+asyncpg://smartspace:<password>@localhost:5432/smartspace
export MQTT_HOST=localhost
export MQTT_PORT=1883

alembic upgrade head
uvicorn backend_engine.app:create_app --factory
```

Interactive API docs: <http://localhost:8000/docs> (authorize with `Authorization: Bearer <token>`).

### 2. API tokens

The API has no login endpoint. Tokens are created with a script; the raw token is printed **once** and only its
hash is stored.

```bash
python scripts/create_token.py --name admin   --role admin
python scripts/create_token.py --name user    --role user
python scripts/create_token.py --name gateway --role gateway
# optional: --days 90 for an expiring token
```

### 3. Gateway and simulator (test the whole system without hardware)

In two more terminals (with the same `MQTT_*` variables set):

```bash
# terminal 2: the gateway (role "gateway")
export GATEWAY_API_URL=http://localhost:8000
export GATEWAY_API_TOKEN=ss_...
python -m device_gateway

# terminal 3: virtual devices; the admin/user token lets them register themselves in the backend
export SIM_API_URL=http://localhost:8000
export SIM_API_TOKEN=ss_...
python -m device_simulator
```

### 4. Try it

```bash
# the simulated devices appear as online
curl -H "Authorization: Bearer $USER_TOKEN" http://localhost:8000/api/v1/devices

# turn the lamp on (command_id is a UUID you generate; it is the idempotency key)
curl -X POST http://localhost:8000/api/v1/devices/living_lamp/command \
  -H "Authorization: Bearer $USER_TOKEN" -H "Content-Type: application/json" \
  -d '{"command_id": "'"$(python -c 'import uuid; print(uuid.uuid4())')"'", "action": "turn_on", "parameters": {}}'
# -> status "dispatched", then "acknowledged" once the simulated lamp answers

# inject a failure: the next command ends as "failed"
python -m device_simulator.control faults living_lamp fail_next=1
```

More scenarios (slow or lost acknowledgements, going offline, crash with MQTT Last Will):
[docs/simulator.md](docs/simulator.md).

## Configuration

All configuration is through environment variables (see `.env.example`).

### Backend

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | (required) | `postgresql+asyncpg://user:password@host:port/db` |
| `DB_ECHO` | `false` | Log SQL statements |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` | `10` / `20` | Connection pool |
| `MQTT_HOST` / `MQTT_PORT` | `localhost` / `1883` | Broker |
| `MQTT_USERNAME` / `MQTT_PASSWORD` | unset | Broker credentials |
| `MQTT_TLS` | `false` | Use TLS |
| `MQTT_KEEPALIVE` | `30` | Seconds |
| `MQTT_TOPIC_PREFIX` | `smart-space/devices` | Prefix for all device topics |

### Device gateway

| Variable | Default | Description |
|---|---|---|
| `GATEWAY_API_URL` | `http://localhost:8000` | Backend base URL |
| `GATEWAY_API_TOKEN` | (required) | Token with role `gateway` |
| `GATEWAY_HEARTBEAT_SECONDS` | `10` | Re-send unchanged state at most this often (keeps `last_seen_at` fresh) |
| `MQTT_*` | as above | Same broker settings and topic prefix as the backend |

### Device simulator

| Variable | Default | Description |
|---|---|---|
| `SIM_FLEET` | `living_room` | Comma-separated fleets: `living_room`, `kitchen` |
| `SIM_INTERVAL` | `3.0` | Seconds between telemetry messages |
| `SIM_API_URL` / `SIM_API_TOKEN` | unset | Register the devices in the backend and use the ids it assigns (token role: `admin` or `user`) |
| `SIM_DEVICE_IDS` | unset | JSON map `{"slug": "uuid"}` to fix device ids manually |
| `MQTT_*` | as above | Broker settings and topic prefix |

## API overview

Base path: `/api/v1`. Authentication: `Authorization: Bearer <token>`. Errors are `{"detail": "..."}`.

| Method | Path | Permission | Purpose |
|---|---|---|---|
| GET | `/health` | none | Liveness and database check |
| POST | `/devices` | `device:write` | Register a device (`slug`, `name`, `type`, `capabilities`) |
| GET | `/devices` | `device:read` | List devices (`room_id`, `type`, `availability`, `limit`, `offset`) |
| GET | `/devices/{device_id}` | `device:read` | Get one device |
| DELETE | `/devices/{device_id}` | `device:delete` | Delete a device |
| PUT | `/devices/{slug}/availability` | `device:report` | Gateway: device went online or offline |
| PUT | `/devices/{slug}/state` | `device:report` | Gateway: merge partial device state (implies online) |
| POST | `/devices/{slug}/command` | `command:create` | Submit a command (idempotent by `command_id`) |
| GET | `/commands/{command_id}` | `command:read` | Command status and decision reasons |
| POST | `/commands/{command_id}/confirm` | `command:confirm` | Human confirmation of a risky command |
| POST | `/commands/{command_id}/reject` | `command:confirm` | Human rejection |
| POST | `/commands/{command_id}/ack` | `device:report` | Gateway: device acknowledged (`{"ok": true}` or `{"ok": false}`) |
| POST | `/system/emergency-stop` | `system:emergency` | Block all commands |
| POST | `/system/emergency-stop/clear` | `system:emergency` | Resume |

### Roles

| Role | Permissions |
|---|---|
| `admin` | everything |
| `user` | read and write devices, create, read and confirm commands |
| `viewer` | read devices |
| `gateway` | read devices, report state, availability and acknowledgements |

Status codes: `401` missing, invalid, expired or revoked token; `403` missing permission; `404` unknown device or
command; `409` conflict (duplicate slug, `command_id` reused with different content, invalid state transition);
`422` validation error.

## Command lifecycle and the Safety Engine

```
pending ─► approved ─► dispatched ─► acknowledged
   │          │             ├──────► failed        (device reported ok=false, or dispatch failed)
   │          │             └──────► timed_out     (no acknowledgement in time)
   │          └──────────► cancelled
   ├──────► rejected                                (Safety Engine said no)
   └──────► awaiting_confirmation ─► approved / rejected / expired / cancelled
```

Every command passes the Safety Engine before anything is sent. A refusal is recorded as a command with
`status: "rejected"` and a list of `decision_reasons`:

| Reason | Meaning |
|---|---|
| `emergency_stop_active` | Emergency stop is on |
| `device_not_found`, `device_disabled`, `device_offline` | The device cannot receive commands |
| `unknown_action`, `unsupported_action`, `invalid_parameters` | Action not allowed, capability missing, or bad parameters |
| `risky_action` | Needs human confirmation (for example `turn_on` on a relay or plug) |
| `automated_confirmation_not_allowed` | A risky action from an automated source (AI or automation) |
| `rate_limit_exceeded` | Too many recent commands for the device |
| `conflicting_command_active` | A conflicting command is still in progress |

Supported actions: `turn_on` and `turn_off` (capability `on_off`), and `set_brightness` with
`{"brightness": 0..100}` (capability `brightness`). Risky commands wait in `awaiting_confirmation` until a human calls
the confirm endpoint; the confirmation window is limited, and expired confirmations become `expired`.

Rules of thumb for clients:

- Treat `approved` and `dispatched` as "accepted", **not** "executed". Only `acknowledged` means the device did it.
- Always check the `status` in the response of `confirm`: confirming an expired command returns HTTP 200 with
  `status: "expired"`.
- Retrying a submission with the same `command_id` and the same content is safe and returns the same command.

## MQTT contract

Topics (the prefix defaults to `smart-space/devices`; `{id}` is the device UUID assigned by the backend):

| Topic | Direction | Payload |
|---|---|---|
| `{prefix}/{id}/commands` | backend → device (QoS 1, not retained) | `{"command_id", "device_id", "action", "parameters", "correlation_id"}` |
| `{prefix}/{id}/status` | device → (retained, with Last Will) | `{"device_id", "online": bool, "availability", "timestamp"}` |
| `{prefix}/{id}/telemetry` | device → | `{"device_id", "timestamp", "readings": {...}}` |
| `{prefix}/{id}/ack` | device → | `{"command_id", "device_id", "ok": bool}` |

QoS 1 is at-least-once, so devices and gateways must deduplicate by `command_id` (the simulator and the gateway do).
Details and ACL and TLS recommendations: [docs/mqtt-gateway.md](docs/mqtt-gateway.md).

## Device simulator

`device_simulator/` runs virtual devices, each with its **own MQTT connection and Last Will**, like real hardware.
Their command semantics mirror the Safety Engine's action table (a test fails if they drift apart).

| Fleet | Devices |
|---|---|
| `living_room` | `living_lamp` (light), `living_relay` (relay, needs confirmation), `living_temp`, `living_humidity` |
| `kitchen` | `kitchen_light`, `kitchen_plug` (plug, needs confirmation), `kitchen_temp` |

Fault injection at runtime (`python -m device_simulator.control <op> <slug|*> [key=value ...]`):

| Operation | Effect |
|---|---|
| `offline` / `online` | The device disappears or comes back |
| `crash` | The connection dies without DISCONNECT, the broker publishes the Last Will, the device reboots |
| `faults ack_delay=N` | Executes immediately, acknowledges after N seconds |
| `faults fail_next=N` | Next N commands: `ok=false`, state unchanged |
| `faults drop_next=N` | Next N commands: executed, but the acknowledgement is lost |
| `faults duplicate_ack=true` | Every acknowledgement is sent twice |
| `reset`, `set` | Clear faults, or change the device state from outside |

Full guide: [docs/simulator.md](docs/simulator.md).

## Testing

Integration tests need a **real PostgreSQL** (the schema uses JSONB and native UUIDs). The database is truncated
between tests, so use a throwaway one.

```bash
export TEST_DATABASE_URL=postgresql+asyncpg://smartspace:<password>@localhost:5432/smartspace_test
pytest                                                   # everything
pytest tests/test_simulator.py tests/test_gateway.py     # no database or broker needed
lint-imports                                             # architecture boundaries
mypy src                                                 # strict typing
```

`tests/test_e2e_mqtt.py` runs the backend, gateway and simulator together against a real broker
(`MQTT_TEST_HOST` / `MQTT_TEST_PORT`, default `localhost:1883`, provided by `docker compose up -d mqtt`). It covers
command round-trips, human confirmation, failed, slow, lost and duplicated acknowledgements, going offline, and
crash detection through the Last Will. Without a broker or database these tests are skipped.

## Development rules

- **Layering** (enforced by `lint-imports`): `shared` imports nothing from `modules` or `api`; `modules` never import `api`.
- **Entity vs DTO:** entities are ORM objects and stay inside their module; DTOs are the module boundary;
  services take and return DTOs.
- **Events** are published only after the transaction commits.
- **Decisions** are recorded as ADRs in [docs/adr](docs/adr).
- **Typing and validation:** `mypy` strict; Pydantic models validate all external input (`extra="forbid"` on request bodies).

## Security notes

- Tokens are random, stored only as hashes, and support expiry and revocation. Never commit `.env` or tokens.
- The Compose broker is **anonymous** and bound to `127.0.0.1` for development. In production enable broker
  authentication, ACLs and TLS (`MQTT_TLS=true`).
- Only the `gateway` and `admin` roles can report device state. Do not give device-reporting rights to user tokens.
- The gateway ignores messages whose payload `device_id` differs from the topic, and devices unknown to the backend.
- Token lookup hits the database on every request (add a short TTL cache if it becomes a bottleneck).

## Known gaps

- No `room` module: `device.room_id` is a plain UUID without a foreign key.
- No real-time push (SSE or WebSocket); clients poll.
- No endpoint to list commands or to read the audit log yet, so a command-history view needs one.
- The gateway handles messages sequentially; if the backend is unreachable, a message is dropped after three retries.
- No telemetry history (only the current state is stored).
- No automations and no AI assistant integration yet.

## Documentation index

| Document | Content |
|---|---|
| [docs/simulator.md](docs/simulator.md) | Running the gateway and simulator, fault scenarios, tests |
| [docs/mqtt-gateway.md](docs/mqtt-gateway.md) | MQTT command contract and gateway requirements |
| [docs/adr](docs/adr) | Architecture decision records |
| [docs/desktop](docs/desktop) | Desktop client architecture and API mapping |