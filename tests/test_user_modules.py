from uuid import uuid4

from fastapi.testclient import TestClient


def test_assign_module_to_user(client: TestClient, module: dict) -> None:
    user_id = uuid4()
    response = client.put(f"/api/v1/users/{user_id}/modules/{module['id']}")
    assert response.status_code == 204

    assigned = client.get(f"/api/v1/users/{user_id}/modules").json()
    assert [m["id"] for m in assigned] == [module["id"]]


def test_assignment_is_idempotent(client: TestClient, module: dict) -> None:
    user_id = uuid4()
    for _ in range(3):
        assert client.put(f"/api/v1/users/{user_id}/modules/{module['id']}").status_code == 204
    assert len(client.get(f"/api/v1/users/{user_id}/modules").json()) == 1


def test_assign_unknown_module_is_404(client: TestClient) -> None:
    response = client.put(f"/api/v1/users/{uuid4()}/modules/{uuid4()}")
    assert response.status_code == 404
    assert response.json()["code"] == "MODULE_NOT_FOUND"


def test_user_without_modules_gets_empty_list(client: TestClient) -> None:
    response = client.get(f"/api/v1/users/{uuid4()}/modules")
    assert response.status_code == 200
    assert response.json() == []
