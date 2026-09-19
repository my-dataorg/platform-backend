from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_validation_errors_use_problem_details_and_400():
    response = client.post("/v1/auth/login", json={})

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["type"].endswith("/validation")


def test_admin_auth_errors_use_problem_details():
    response = client.get("/v1/admin/products")

    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["status"] == 401
