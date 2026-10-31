"""Unit tests for the orders handler with both payload formats.

The base events come from `sam local generate-event apigateway aws-proxy`
(format 1.0) and `sam local generate-event apigateway http-api-proxy` (format 2.0),
saved in events/.
"""

import base64
import copy
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT))
import handler  # noqa: E402
import pricing  # noqa: E402

REST_EVENT = json.loads((ROOT / "events/rest-get-order.json").read_text())
HTTP_EVENT = json.loads((ROOT / "events/http-api-sample.json").read_text())


def rest_event(method, path, resource, params=None, body=None, api_key_id=None):
    e = copy.deepcopy(REST_EVENT)
    e.update(httpMethod=method, path=path, resource=resource, pathParameters=params,
             body=body, isBase64Encoded=False)
    e["requestContext"]["identity"]["apiKeyId"] = api_key_id
    return e


def http_event(method, path, route, params=None, body=None, sub=None, b64=False):
    e = copy.deepcopy(HTTP_EVENT)
    e.update(routeKey=route, rawPath=path, pathParameters=params, isBase64Encoded=b64,
             body=base64.b64encode(body.encode()).decode() if (body and b64) else body)
    e["requestContext"]["http"]["method"] = method
    e["requestContext"]["authorizer"]["jwt"]["claims"] = {"sub": sub} if sub else {}
    return e


def test_get_order_with_rest_api_event():
    res = handler.handler(rest_event("GET", "/orders/1001", "/orders/{orderId}", {"orderId": "1001"}), None)
    assert res["statusCode"] == 200
    assert json.loads(res["body"])["book"] == "REST in Practice"


def test_get_order_with_http_api_event():
    res = handler.handler(http_event("GET", "/orders/1001", "GET /orders/{orderId}", {"orderId": "1001"}), None)
    assert res["statusCode"] == 200
    assert json.loads(res["body"])["id"] == "1001"


def test_unknown_order_is_404_in_both_formats():
    r1 = handler.handler(rest_event("GET", "/orders/9", "/orders/{orderId}", {"orderId": "9"}), None)
    r2 = handler.handler(http_event("GET", "/orders/9", "GET /orders/{orderId}", {"orderId": "9"}), None)
    assert r1["statusCode"] == r2["statusCode"] == 404


def test_create_order_records_api_key_caller_for_rest():
    body = json.dumps({"book": "RESTful Web APIs", "quantity": 2})
    res = handler.handler(rest_event("POST", "/orders", "/orders", body=body, api_key_id="k-123"), None)
    assert res["statusCode"] == 201
    assert json.loads(res["body"])["createdBy"] == "api-key:k-123"


def test_create_order_records_jwt_subject_for_http_and_decodes_base64():
    body = json.dumps({"book": "Designing Web APIs", "quantity": 1})
    res = handler.handler(http_event("POST", "/orders", "POST /orders", body=body, sub="user-42", b64=True), None)
    assert res["statusCode"] == 201
    assert json.loads(res["body"])["createdBy"] == "jwt:user-42"


@pytest.mark.parametrize("body", ["not json", json.dumps({"book": "x"}), json.dumps({"quantity": 1})])
def test_invalid_body_is_400(body):
    res = handler.handler(http_event("POST", "/orders", "POST /orders", body=body), None)
    assert res["statusCode"] == 400


def test_response_shape_is_valid_for_rest_proxy_integration():
    res = handler.handler(rest_event("GET", "/orders/1001", "/orders/{orderId}", {"orderId": "1001"}), None)
    assert isinstance(res["statusCode"], int)
    assert isinstance(res["body"], str)
    assert isinstance(res["headers"], dict)


def test_pricing_matches_aws_examples():
    assert pricing.cost(432e6, pricing.HTTP_TIERS) == pytest.approx(418.80)
    assert pricing.cost(5e6, pricing.REST_TIERS) == pytest.approx(17.50)
    assert pricing.http_metered(1, 4.5 * 1024) == 9  # the page's 4.5 MB example: 9 requests
