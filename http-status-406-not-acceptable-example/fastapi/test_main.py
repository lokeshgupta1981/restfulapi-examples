from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_unsupported_accept_gets_406_with_alternatives():
    response = client.get("/reports/2026-09", headers={"Accept": "application/xml"})
    assert response.status_code == 406
    assert response.headers["Content-Type"] == "application/problem+json"
    assert response.headers["Vary"] == "Accept"
    offered = [entry["type"] for entry in response.json()["available"]]
    assert offered == ["application/json", "text/csv"]


def test_q_values_pick_csv():
    response = client.get(
        "/reports/2026-09", headers={"Accept": "text/csv;q=0.5, application/json;q=0.4"}
    )
    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("text/csv")


def test_missing_accept_gets_json():
    response = client.get("/reports/2026-09", headers={"Accept": ""})
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"
