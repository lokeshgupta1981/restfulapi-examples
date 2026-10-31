"""Create and read JWS, JWE and nested (signed, then encrypted) JWTs."""
import json
import time

from jwcrypto import jwe, jwt

from keys import AUTH_SIGNING_KEY, ORDERS_API_ENCRYPTION_KEY, public

ISSUER = "https://auth.example.com"
AUDIENCE = "https://api.example.com/orders"

# What the Orders API knows: the auth server's PUBLIC signing key
# and its own PRIVATE decryption key.
AUTH_PUBLIC_KEY = public(AUTH_SIGNING_KEY)
ORDERS_API_PUBLIC_KEY = public(ORDERS_API_ENCRYPTION_KEY)


def claims_for(user_id="user-42", email="alice@example.com", lifetime=300):
    now = int(time.time())
    return {
        "iss": ISSUER,
        "sub": user_id,
        "aud": AUDIENCE,
        "iat": now,
        "exp": now + lifetime,
        "scope": "orders:read",
        "email": email,
    }


# ---------- creating tokens (the auth server's side) ----------

def make_jws(claims, signing_key=AUTH_SIGNING_KEY):
    """Sign the claims: anyone can read them, nobody can change them."""
    header = {"alg": "ES256", "typ": "JWT", "kid": signing_key.key_id}
    token = jwt.JWT(header=header, claims=claims)
    token.make_signed_token(signing_key)
    return token.serialize()


def make_jwe(claims):
    """Encrypt the claims to the Orders API's public key: only the API can read them."""
    key = ORDERS_API_PUBLIC_KEY
    header = {"alg": "RSA-OAEP-256", "enc": "A256GCM", "typ": "JWT", "kid": key.key_id}
    token = jwt.JWT(header=header, claims=claims)
    token.make_encrypted_token(key)
    return token.serialize()


def make_nested(claims, signing_key=AUTH_SIGNING_KEY):
    """Sign first, then encrypt the signed token (RFC 7519, Section 11.2)."""
    signed = make_jws(claims, signing_key)
    key = ORDERS_API_PUBLIC_KEY
    header = {"alg": "RSA-OAEP-256", "enc": "A256GCM", "cty": "JWT", "kid": key.key_id}
    outer = jwe.JWE(signed.encode(), protected=json.dumps(header, separators=(",", ":")))
    outer.add_recipient(key)
    return outer.serialize(compact=True)


# ---------- reading tokens (the Orders API's side) ----------

def kind_of(token):
    """Tell a JWS from a JWE the way RFC 7516, Section 9 describes."""
    parts = token.split(".")
    if len(parts) == 3:
        return "JWS"
    if len(parts) == 5:
        return "JWE"
    return "not a compact JWS or JWE"


def verify_jws(token):
    """Check the signature and the claims, return the claims."""
    t = jwt.JWT(jwt=token, key=AUTH_PUBLIC_KEY, algs=["ES256"],
                check_claims={"iss": ISSUER, "aud": AUDIENCE, "exp": None})
    return json.loads(t.claims)


def decrypt_only(token):
    """The naive way: decrypt and trust whatever comes out."""
    t = jwt.JWT(jwt=token, key=ORDERS_API_ENCRYPTION_KEY, algs=["RSA-OAEP-256", "A256GCM"],
                check_claims={"iss": ISSUER, "aud": AUDIENCE, "exp": None})
    return json.loads(t.claims)


def decrypt_and_verify(token):
    """Nested JWT: decrypt the outer JWE, then verify the inner JWS."""
    outer = jwe.JWE()
    outer.deserialize(token, key=ORDERS_API_ENCRYPTION_KEY)
    header = outer.jose_header
    if header.get("alg") != "RSA-OAEP-256" or header.get("enc") != "A256GCM":
        raise ValueError("unexpected encryption algorithm")
    if header.get("cty") != "JWT":
        raise ValueError("the encrypted content is not a signed JWT")
    inner = outer.payload.decode()
    if kind_of(inner) != "JWS":
        raise ValueError("the inner token is not a JWS")
    return verify_jws(inner)

