"""Demo keys for the examples. Generated on first use, never for production."""
import json
import pathlib

from jwcrypto import jwk

KEY_DIR = pathlib.Path(__file__).parent / "demo-keys"


def _load_or_create(name, **params):
    path = KEY_DIR / f"{name}.json"
    if path.exists():
        return jwk.JWK.from_json(path.read_text())
    KEY_DIR.mkdir(exist_ok=True)
    key = jwk.JWK.generate(kid=name, **params)
    path.write_text(key.export_private())
    return key


# The auth server signs tokens with this EC P-256 key (ES256).
AUTH_SIGNING_KEY = _load_or_create("auth-server-signing-demo", kty="EC", crv="P-256")

# The Orders API decrypts tokens with this RSA key (RSA-OAEP-256).
ORDERS_API_ENCRYPTION_KEY = _load_or_create("orders-api-encryption-demo", kty="RSA", size=2048)


def public(key):
    """The public half of a key: what other parties are allowed to see."""
    return jwk.JWK.from_json(key.export_public())


if __name__ == "__main__":
    print(json.dumps(json.loads(public(AUTH_SIGNING_KEY).export()), indent=2))
    print(json.dumps(json.loads(public(ORDERS_API_ENCRYPTION_KEY).export()), indent=2)[:300], "...")
