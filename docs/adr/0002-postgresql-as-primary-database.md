# ADR-0002: PostgreSQL as the primary database

- Status: Proposed
- Date: 2026-11-20
- Deciders: @owner

## Context
Smart Space stores relational data (rooms, devices, automations, commands)
and high-volume append-only data (sensor readings, device events, audit log).
Telemetry is written continuously and concurrently with command and state updates.
Old telemetry must be removed or aggregated without blocking writes.
Backend is async (FastAPI, SQLAlchemy 2.x, asyncpg).
Docker Compose is already the deployment model (ADR-0004), so an extra container is cheap.
Target hardware: mini PC, NAS, Raspberry Pi 4/5 (4 GB+ RAM).

## Decision
PostgreSQL 16 is the only supported database in v0.1.

- Driver: asyncpg via SQLAlchemy 2.x async engine.
- Migrations: Alembic. Schema changes only through migrations.
- All timestamps: `timestamptz`, stored in UTC.
- `sensor_reading`: range-partitioned by time (daily or weekly).
  Retention drops old partitions. Hourly aggregates are kept in a separate table.
- Critical writes (command, audit) happen in one transaction before an event is published.
- Engine is created in `lifespan` and disposed on shutdown. No engine at import time.
- `DATABASE_URL` is mandatory. No default credentials in code.
- The database port is not published in the main compose file. Dev override only.
- Tests run against real PostgreSQL (Testcontainers or a CI service container). SQLite and in-memory substitutes are not used.
- Redis is not part of the stack. The event bus is in-process (ADR-0003).

## Alternatives considered
- SQLite (WAL): zero extra container and lighter on small devices.
  Rejected: single writer limits telemetry throughput under load, weak partitioning and retention,
  type differences (timestamps, JSON) cause divergence from the production database,
  and a later migration to PostgreSQL would cost more than starting there.
- SQLite for v0.1, PostgreSQL later: two code paths and double test matrix. Rejected.
- TimescaleDB: strong for time series, but an extra extension and image.
  Native partitioning is enough at this scale. Revisit if telemetry volume grows.
- Dedicated time-series DB (InfluxDB, VictoriaMetrics): another service and query language.
  Rejected as unjustified complexity.

## Consequences
+ Concurrent telemetry writes do not block commands and state updates.
+ Partition drop makes retention cheap and non-blocking.
+ Rich types (JSONB, enums, timestamptz) and indexes (partial, BRIN) for event and reading queries.
+ Development and production use the same database.
- One more container and roughly 100-200 MB of RAM at idle.
  Tight on 2 GB boards. Minimum hardware: 4 GB RAM.
- Backups are required: scheduled `pg_dump`, documented in the deployment guide.
- Users who want a single-file database are not served in v0.1.
  Supporting SQLite later needs a new ADR and a full test matrix.
- Partition management needs a maintenance job (create future partitions, drop expired ones).
  It runs as a backend background task and is covered by tests.

## References
- [ADR-0001: modular monolith](0001-modular-monolith.md)
