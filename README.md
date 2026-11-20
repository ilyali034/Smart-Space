# Smart Space backend

Modular monolith: FastAPI, SQLAlchemy 2 (async), PostgreSQL.

## Layout
```
src/backend_engine/
  app.py            create_app(), lifespan, wiring
  api/              HTTP only: routers, error mapping
  shared/           config, events (bus), auth, storage (Base, UoW)
  modules/
    audit/          audit log entity + writer
    devices/        dto, entity, repository, uow, service, events, exceptions
```
Rules (enforced by `lint-imports`): `shared` imports nothing from `modules`/`api`; `modules` never import `api`.
Entity = ORM, stays inside its module. DTO = module boundary. Service takes/returns DTOs.
Events are published only after commit.

## Run
```
cp .env.example .env            # set real passwords
docker compose up -d postgres
pip install -e ".[dev]"
export DATABASE_URL=postgresql+asyncpg://smartspace:<pwd>@localhost:5432/smartspace
alembic upgrade head
python scripts/create_token.py --name admin --role admin
uvicorn backend_engine.app:create_app --factory
```
Docs: http://localhost:8000/docs  (Authorization: Bearer <token>)

## Test (real PostgreSQL required)
```
export TEST_DATABASE_URL=postgresql+asyncpg://smartspace:<pwd>@localhost:5432/smartspace_test
pytest
lint-imports
mypy src
```

## Known gaps
- No `room` module: `device.room_id` is a plain UUID, no FK yet.
- Token lookup hits the DB on every request (add short TTL cache if needed).
- Gateway (MQTT), context, safety, automation, rate limiting: not implemented.
