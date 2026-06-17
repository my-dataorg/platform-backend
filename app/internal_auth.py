from fastapi import Header, HTTPException

from app.config import settings


def require_internal_token(x_internal_token: str | None = Header(default=None)) -> None:
    expected = settings.internal_api_token
    if not expected:
        raise HTTPException(status_code=503, detail="Internal API not configured")
    if not x_internal_token or x_internal_token != expected:
        raise HTTPException(status_code=401, detail="Invalid internal token")
