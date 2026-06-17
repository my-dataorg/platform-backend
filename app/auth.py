import httpx
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import settings

_bearer = HTTPBearer(auto_error=False)
_jwks_cache: dict | None = None


async def _get_jwks() -> dict:
    global _jwks_cache
    if _jwks_cache:
        return _jwks_cache
    async with httpx.AsyncClient() as client:
        res = await client.get(settings.jwks_url, timeout=10)
        res.raise_for_status()
        _jwks_cache = res.json()
        return _jwks_cache


async def _decode_token(token: str) -> dict:
    jwks = await _get_jwks()
    header = jwt.get_unverified_header(token)
    key = next(k for k in jwks["keys"] if k["kid"] == header["kid"])
    return jwt.decode(
        token,
        key,
        algorithms=[header["alg"]],
        issuer=settings.issuer,
        options={"verify_aud": False},
    )


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    if not creds:
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        payload = await _decode_token(creds.credentials)
    except (JWTError, StopIteration, httpx.HTTPError) as e:
        raise HTTPException(status_code=401, detail="Invalid token") from e
    return {
        "id": payload.get("sub"),
        "email": payload.get("email") or payload.get("preferred_username"),
        "name": payload.get("name") or payload.get("given_name", "User"),
    }


async def get_optional_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict | None:
    if not creds:
        return None
    try:
        payload = await _decode_token(creds.credentials)
        return {"id": payload.get("sub")}
    except (JWTError, StopIteration, httpx.HTTPError):
        return None
