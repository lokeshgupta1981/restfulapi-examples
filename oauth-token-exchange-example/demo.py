"""Walks through token exchange step by step and prints what goes over the wire.

Start the three servers first (see README.md), then: python demo.py
"""
import base64
import json
import os

import httpx

AUTH_URL = os.environ.get("AUTH_URL", "http://127.0.0.1:8000")
ORDERS_URL = os.environ.get("ORDERS_URL", "http://127.0.0.1:8001")
EXCHANGE = "urn:ietf:params:oauth:grant-type:token-exchange"
ACCESS_TOKEN = "urn:ietf:params:oauth:token-type:access_token"
# Fake demo secrets, the same as in auth_server.py.
ORDERS = ("orders-api", "demo-secret-orders-api")
PAYMENTS = ("payments-api", "demo-secret-payments-api")
REPORTS = ("reports-api", "demo-secret-reports-api")

http = httpx.Client(timeout=5)


def title(text):
    print(f"\n== {text}")


def claims(token):
    """Decode the JWT payload WITHOUT verifying it, only to print it."""
    payload = token.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))


def show_claims(token, keys=("sub", "aud", "scope", "client_id", "act", "exp", "iat")):
    c = claims(token)
    print(json.dumps({k: c[k] for k in keys if k in c}, indent=2))


def show(response):
    print(response.status_code, json.dumps(response.json(), indent=2))


def login(aud="orders-api"):
    return http.post(AUTH_URL + "/demo/login", data={"user": "asha", "aud": aud}).json()["access_token"]


def client_token(client):
    return http.post(AUTH_URL + "/token", auth=client,
                     data={"grant_type": "client_credentials"}).json()["access_token"]


def exchange(client, subject, actor=None, **extra):
    form = {"grant_type": EXCHANGE, "subject_token": subject,
            "subject_token_type": ACCESS_TOKEN}
    if actor:
        form.update(actor_token=actor, actor_token_type=ACCESS_TOKEN)
    form.update(extra)
    return http.post(AUTH_URL + "/token", auth=client, data=form)


def order(user_token, forward):
    return http.post(ORDERS_URL + "/orders", params={"forward": forward},
                     json={"book_id": "bk-101", "amount": 39.0},
                     headers={"Authorization": "Bearer " + user_token})


title("1. Asha signs in. Her token is for the Orders API only")
user_token = login()
show_claims(user_token)

title("2. Orders API forwards Asha's token to the Payments API")
show(order(user_token, "user-token"))

title("3. Token exchange without an actor_token (impersonation)")
r = exchange(ORDERS, user_token, audience="payments-api", scope="payments:charge")
body = r.json()
print(r.status_code, json.dumps({**body, "access_token": body["access_token"][:24] + "..."}, indent=2))
show_claims(body["access_token"])

title("4. Token exchange with an actor_token (delegation)")
orders_own = client_token(ORDERS)
print("actor_token claims:")
show_claims(orders_own, keys=("sub", "aud", "client_id"))
r = exchange(ORDERS, user_token, actor=orders_own, audience="payments-api",
             scope="payments:charge")
delegated = r.json()["access_token"]
print("issued token claims:")
show_claims(delegated)

title("5. Place orders with both kinds of exchanged token")
print("forward=impersonate:")
show(order(user_token, "impersonate"))
print("forward=delegate:")
show(order(user_token, "delegate"))

title("6. A chain: the Payments API exchanges the delegated token for the Ledger API")
r = exchange(PAYMENTS, delegated, actor=client_token(PAYMENTS), audience="ledger-api",
             scope="ledger:write")
show_claims(r.json()["access_token"], keys=("sub", "aud", "scope", "act"))

title("7. Requests the authorization server refuses")
print("7a. Orders API asks for a Ledger API token:")
show(exchange(ORDERS, user_token, audience="ledger-api", scope="ledger:write"))
print("7b. Orders API asks for more scope than its policy allows:")
show(exchange(ORDERS, user_token, audience="payments-api",
              scope="payments:charge payments:refund"))
print("7c. Payments API tries to exchange a token that was issued for the Orders API:")
show(exchange(PAYMENTS, user_token, actor=client_token(PAYMENTS), audience="ledger-api",
              scope="ledger:write"))
print("7d. Orders API sends the Payments API's own token as actor_token:")
show(exchange(ORDERS, user_token, actor=client_token(PAYMENTS), audience="payments-api",
              scope="payments:charge"))
print("7e. The user token with a changed payload (signature no longer matches):")
head, payload, sig = user_token.split(".")
fake = base64.urlsafe_b64encode(json.dumps({**claims(user_token), "sub": "mallory"})
                                .encode()).decode().rstrip("=")
show(exchange(ORDERS, f"{head}.{fake}.{sig}", audience="payments-api",
              scope="payments:charge"))

title("8. The Payments API checks the current actor")
reports_user = login(aud="reports-api")
r = exchange(REPORTS, reports_user, actor=client_token(REPORTS), audience="payments-api",
             scope="payments:charge")
reports_token = r.json()["access_token"]
show_claims(reports_token, keys=("sub", "aud", "act"))
r = http.post(os.environ.get("PAYMENTS_URL", "http://127.0.0.1:8002") + "/charges",
              json={"order_id": "ord_test", "amount": 1.0},
              headers={"Authorization": "Bearer " + reports_token})
show(r)

title("9. Caching: ten orders with a fresh user token")
fresh = login()
before = http.get(AUTH_URL + "/demo/stats").json()["exchanges"]
sources = [order(fresh, "delegate").json()["payment_token"] for _ in range(10)]
after = http.get(AUTH_URL + "/demo/stats").json()["exchanges"]
print("payment_token per order:", sources)
print("token exchanges at the authorization server:", after - before)
