from uuid import uuid4

from fastapi.testclient import TestClient


def test_create_normalizes_code(module: dict) -> None:
    assert module["code"] == "CLOUD-ARCH"
    assert module["name"] == "Cloud Architecture"


def test_create_duplicate_code_is_409(client: TestClient, module: dict) -> None:
    response = client.post("/api/v1/modules", json={"code": "CLOUD-ARCH", "name": "Other"})
    assert response.status_code == 409
    assert response.json()["code"] == "MODULE_CODE_EXISTS"


def test_create_invalid_payload_is_422(client: TestClient) -> None:
    response = client.post("/api/v1/modules", json={"code": " ", "name": "x"})
    assert response.status_code == 422


def test_list_and_retrieve(client: TestClient, module: dict) -> None:
    assert [m["id"] for m in client.get("/api/v1/modules").json()] == [module["id"]]
    response = client.get(f"/api/v1/modules/{module['id']}")
    assert response.status_code == 200
    assert response.json()["code"] == "CLOUD-ARCH"


def test_retrieve_unknown_module_is_404(client: TestClient) -> None:
    response = client.get(f"/api/v1/modules/{uuid4()}")
    assert response.status_code == 404
    assert response.json()["code"] == "MODULE_NOT_FOUND"


def test_retrieve_malformed_id_is_422(client: TestClient) -> None:
    assert client.get("/api/v1/modules/not-a-uuid").status_code == 422


def test_update_and_delete(client: TestClient, module: dict) -> None:
    response = client.patch(f"/api/v1/modules/{module['id']}", json={"name": "Cloud Arch II"})
    assert response.status_code == 200
    assert response.json()["name"] == "Cloud Arch II"

    assert client.delete(f"/api/v1/modules/{module['id']}").status_code == 204
    assert client.get(f"/api/v1/modules/{module['id']}").status_code == 404
