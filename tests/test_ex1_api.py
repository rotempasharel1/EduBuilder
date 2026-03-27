from fastapi.testclient import TestClient

from poseai_backend.main_ex1 import PLANS, app

client = TestClient(app)


def setup_function():
    PLANS.clear()


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_full_crud_flow():
    create_res = client.post(
        "/plans",
        json={
            "title": "Beginner squat reset",
            "goal": "Build a stable stance",
            "cues": "Brace the core and keep the knees tracking over the toes.",
            "level": "Beginner",
            "is_public": True,
        },
    )
    assert create_res.status_code == 200
    created = create_res.json()
    plan_id = created["id"]

    list_res = client.get("/plans")
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1

    get_res = client.get(f"/plans/{plan_id}")
    assert get_res.status_code == 200
    assert get_res.json()["title"] == "Beginner squat reset"

    update_res = client.put(
        f"/plans/{plan_id}",
        json={
            "title": "Beginner squat reset updated",
            "goal": "Build a stronger setup",
            "cues": "Brace the core and sit down between the hips.",
            "level": "Beginner",
            "is_public": False,
        },
    )
    assert update_res.status_code == 200
    assert update_res.json()["title"] == "Beginner squat reset updated"
    assert update_res.json()["is_public"] is False

    delete_res = client.delete(f"/plans/{plan_id}")
    assert delete_res.status_code == 200
    assert delete_res.json()["status"] == "success"

    missing_res = client.get(f"/plans/{plan_id}")
    assert missing_res.status_code == 404
