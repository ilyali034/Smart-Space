"""Create an API token. The raw token is printed once; only its hash is stored.

    DATABASE_URL=... python scripts/create_token.py --name admin --role admin [--days 365]
"""
import argparse
import asyncio
from datetime import datetime, timedelta, timezone

from backend_engine.shared.auth.principal import Role
from backend_engine.shared.auth.tokens import ApiTokenEntity, generate_token
from backend_engine.shared.config import Settings
from backend_engine.shared.storage.database import create_engine, create_session_factory


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--role", required=True, choices=[r.value for r in Role])
    parser.add_argument("--days", type=int, default=None, help="lifetime; omit for no expiry")
    args = parser.parse_args()

    raw, token_hash = generate_token()
    expires = datetime.now(timezone.utc) + timedelta(days=args.days) if args.days else None

    engine = create_engine(Settings.from_env())
    factory = create_session_factory(engine)
    async with factory() as session, session.begin():
        session.add(
            ApiTokenEntity(name=args.name, token_hash=token_hash, role=args.role, expires_at=expires)
        )
    await engine.dispose()
    print(f"token (shown once): {raw}")


if __name__ == "__main__":
    asyncio.run(main())
