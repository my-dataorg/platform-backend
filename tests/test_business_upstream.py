import os

from app.services.business_upstream import business_api_upstream_base


def test_docker_rewrites_localhost(monkeypatch):
    monkeypatch.setenv("RUNNING_IN_DOCKER", "1")
    from app.config import Settings

    settings = Settings(business_api_url="http://127.0.0.1:8040")
    monkeypatch.setattr("app.services.business_upstream.settings", settings)
    assert business_api_upstream_base() == "http://business-backend:8040"


def test_explicit_url_unchanged(monkeypatch):
    monkeypatch.delenv("RUNNING_IN_DOCKER", raising=False)
    from app.config import Settings

    settings = Settings(business_api_url="http://business-backend:8040")
    monkeypatch.setattr("app.services.business_upstream.settings", settings)
    assert business_api_upstream_base() == "http://business-backend:8040"
