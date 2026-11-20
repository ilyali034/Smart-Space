# ADR-0001: Modular monolith instead of microservices

- Status: Accepted
- Date: 2026-11-20
- Deciders: @owner

## Context
Smart Space runs at home on a single machine (mini PC, Raspberry Pi, NAS).
Load is low: tens of devices, a few messages per second.
Every command must pass through the Safety Engine.
The chain "command → ack → state → audit" requires consistency.
The project is developed by a single engineer.

## Decision
The backend is a single process (Python, FastAPI). Modules are packages inside it:
devices, gateway, context, safety, automation, ai, events.

Rules:
- Modules communicate through interfaces and the event bus, never through each other's internals.
- Dependencies point downward only. Boundaries are enforced by `import-linter` in CI.
- Each module owns its tables; no cross-module JOINs.
- Contracts (MQTT, API) live in `contracts/` (JSON Schema).

Only components with a different lifecycle run as separate processes:
Mosquitto, Simulator, Voice, LLM runtime (Ollama / llama.cpp), ML training.

## Alternatives considered
- Microservices: network calls between Safety and Planner, sagas instead of DB transactions, N containers on one machine. No scaling benefit at this load.
- Classic monolith without boundaries: fast to start, but modules fuse together and later splitting is expensive.
- k8s orchestration: excessive for a single machine (see ADR-0004).

## Consequences
+ One DB transaction per command, audit entry and state change.
+ Simple startup: `docker compose up`.
+ Simple debugging and tracing, single deployment unit.
+ Path to splitting is preserved: interfaces, event bus, separate tables, contracts.
- A process crash stops all modules. Mitigation: `restart: unless-stopped`; critical data is written to the DB before an event is published.
- Boundary discipline is held only by the linter. `import-linter` rules are mandatory in CI.
- A module cannot be scaled independently. Criteria for extracting a service: different hardware needed (GPU), a module destabilizes the rest, independent teams appear. First candidates: Voice, Gateway.

## References
