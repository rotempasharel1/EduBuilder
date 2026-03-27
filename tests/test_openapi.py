from hypothesis import HealthCheck, settings
import schemathesis
from fastapi.testclient import TestClient

from poseai_backend.main import app

client = TestClient(app)

health_schema = schemathesis.openapi.from_asgi("/openapi.json", app).include(
    path_regex=r"^/health$",
    method="GET",
)


@health_schema.parametrize()
@settings(max_examples=3, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_health_contract(case):
    case.call_and_validate()


def test_public_plans_list_contract():
    response = client.get("/plans")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_shared_plans_contract():
    response = client.get("/plans/shared")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_plans_mine_requires_auth():
    response = client.get("/plans", params={"mine": True})
    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required for mine=true"
