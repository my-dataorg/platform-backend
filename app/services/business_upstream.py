import os

from app.config import settings

_LOCALHOST_BUSINESS = {"http://127.0.0.1:8040", "http://localhost:8040"}
_DOCKER_BUSINESS = "http://business-backend:8040"


def business_api_upstream_base() -> str:
    """URL platform-backend uses to call business-backend (Docker-aware)."""
    url = settings.business_api_url.rstrip("/")
    if os.environ.get("RUNNING_IN_DOCKER") == "1" and url in _LOCALHOST_BUSINESS:
        return _DOCKER_BUSINESS
    return url
