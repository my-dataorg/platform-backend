from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth import get_current_user
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def auth_user():
    app.dependency_overrides[get_current_user] = lambda: {"id": "user-1", "email": "a@b.com"}
    yield
    app.dependency_overrides.pop(get_current_user, None)


def test_business_gateway_post_proxies():
    mock_response = AsyncMock()
    mock_response.status_code = 201
    mock_response.content = b'{"id":"biz-1","name":"Janani","businessType":"small_scale_industry"}'
    mock_response.headers = {"content-type": "application/json"}

    with patch("app.routers.business_gateway.httpx.AsyncClient") as client_cls:
        instance = client_cls.return_value.__aenter__.return_value
        instance.request = AsyncMock(return_value=mock_response)

        res = client.post(
            "/v1/business/businesses",
            json={"name": "Janani", "businessType": "small_scale_industry"},
            headers={"Authorization": "Bearer test-token"},
        )

    assert res.status_code == 201
    assert res.json()["id"] == "biz-1"
    instance.request.assert_awaited_once()
    call_kwargs = instance.request.await_args.kwargs
    assert call_kwargs["headers"]["Authorization"] == "Bearer test-token"
