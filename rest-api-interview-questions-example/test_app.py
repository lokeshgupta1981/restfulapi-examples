from itertools import count

import pytest
from fastapi.testclient import TestClient

import app as orders_app

WRITER = {"Authorization": "Bearer writer-token"}
READER = {"Authorization": "Bearer reader-token"}


@pytest.fixture
def client():
    orders_app.orders.clear()
    orders_app.idempotency_cache.clear()
    orders_app.next_id = count(1001)
    return TestClient(orders_app.app)


def create(client, product="keyboard", quantity=2, headers=None):
    return client.post("/orders", json={"product": product, "quantity": quantity},
                       headers={**WRITER, **(headers or {})})


def test_post_returns_201_with_location(client):
    response = create(client)
    assert response.status_code == 201
    assert response.headers["Location"] == "/orders/1001"


def test_post_with_same_idempotency_key_creates_one_order(client):
    first = create(client, headers={"Idempotency-Key": "abc"})
    retry = create(client, headers={"Idempotency-Key": "abc"})
    assert first.json() == retry.json()
    assert first.headers["Location"] == retry.headers["Location"]
    assert first.headers["ETag"] == retry.headers["ETag"]
    assert client.get("/orders", headers=READER).json()["total"] == 1


def test_post_without_key_is_not_idempotent(client):
    create(client)
    create(client)
    assert client.get("/orders", headers=READER).json()["total"] == 2


def test_put_is_idempotent(client):
    create(client)
    body = {"product": "keyboard", "quantity": 5}
    first = client.put("/orders/1001", json=body, headers=WRITER)
    second = client.put("/orders/1001", json=body, headers=WRITER)
    assert first.json() == second.json()
    assert first.headers["ETag"] == second.headers["ETag"]


def test_delete_twice_has_same_effect_but_different_status(client):
    create(client)
    assert client.delete("/orders/1001", headers=WRITER).status_code == 204
    assert client.delete("/orders/1001", headers=WRITER).status_code == 404


def test_conditional_get_returns_304(client):
    create(client)
    etag = client.get("/orders/1001", headers=READER).headers["ETag"]
    response = client.get("/orders/1001", headers={**READER, "If-None-Match": etag})
    assert response.status_code == 304
    assert response.content == b""


def test_stale_if_match_returns_412(client):
    create(client)
    old_etag = client.get("/orders/1001", headers=READER).headers["ETag"]
    client.patch("/orders/1001", json={"quantity": 3}, headers=WRITER)
    response = client.put("/orders/1001", json={"product": "keyboard", "quantity": 9},
                          headers={**WRITER, "If-Match": old_etag})
    assert response.status_code == 412


def test_missing_token_is_401_and_missing_scope_is_403(client):
    no_token = client.post("/orders", json={"product": "keyboard", "quantity": 2})
    reader = client.post("/orders", json={"product": "keyboard", "quantity": 2}, headers=READER)
    assert no_token.status_code == 401
    assert no_token.headers["WWW-Authenticate"].startswith("Bearer")
    assert reader.status_code == 403


def test_invalid_value_is_422_and_broken_json_is_400(client):
    invalid = create(client, quantity=0)
    broken = client.post("/orders", content=b'{"product": "keyboard",',
                         headers={**WRITER, "Content-Type": "application/json"})
    assert invalid.status_code == 422
    assert invalid.headers["Content-Type"] == "application/problem+json"
    assert broken.status_code == 400


def test_unsupported_method_is_405_with_allow(client):
    response = client.put("/orders", json={}, headers=WRITER)
    assert response.status_code == 405
    assert response.headers["Allow"] == "GET, POST"


def test_pagination_sends_link_header(client):
    create(client)
    create(client, product="mouse")
    response = client.get("/orders?limit=1", headers=READER)
    assert response.headers["Link"] == '</orders?limit=1&offset=1>; rel="next"'
