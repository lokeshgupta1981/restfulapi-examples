from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_every_401_carries_a_challenge():
    for headers in ({}, auth("tok-nobody"), auth("tok-alice-old")):
        response = client.get("/projects/p-100", headers=headers)
        assert response.status_code == 401
        assert response.headers["www-authenticate"].startswith("Bearer ")


def test_missing_and_foreign_projects_look_the_same():
    missing = client.get("/projects/p-999", headers=auth("tok-alice"))
    foreign = client.get("/projects/p-200", headers=auth("tok-alice"))
    assert missing.status_code == foreign.status_code == 404
    assert missing.headers["content-type"] == foreign.headers["content-type"]
    assert missing.json()["detail"].replace("p-999", "X") == foreign.json()["detail"].replace("p-200", "X")


def test_private_project_is_hidden_from_colleague():
    assert client.get("/projects/p-101", headers=auth("tok-carol")).status_code == 404
    assert client.get("/projects/p-101", headers=auth("tok-alice")).status_code == 200


def test_visible_but_not_allowed_is_403():
    response = client.delete("/projects/p-102", headers=auth("tok-alice"))
    assert response.status_code == 403
    assert "www-authenticate" not in response.headers


def test_scope_check_runs_before_lookup():
    response = client.delete("/projects/p-200", headers=auth("tok-carol"))
    assert response.status_code == 403
    assert 'error="insufficient_scope"' in response.headers["www-authenticate"]
