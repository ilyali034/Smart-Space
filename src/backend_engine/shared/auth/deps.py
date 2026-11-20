from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend_engine.shared.auth.principal import Principal

_bearer = HTTPBearer(auto_error=False)


async def get_principal(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> Principal:
    if creds is None:
        raise HTTPException(401, "missing bearer token", {"WWW-Authenticate": "Bearer"})
    principal: Principal | None = await request.app.state.token_verifier.verify(creds.credentials)
    if principal is None:
        raise HTTPException(401, "invalid token", {"WWW-Authenticate": "Bearer"})
    return principal