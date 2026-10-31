"""Write one valid and several broken demo tokens to tokens/<name>.jwt for demo.sh."""
import time
from pathlib import Path

from tokens import PRIVATE_KEY, make_token
from cryptography.hazmat.primitives.asymmetric import rsa

now = int(time.time())
other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

cases = {
    "valid": make_token(),
    "expired": make_token(iat=now - 900, nbf=now - 900, exp=now - 600),
    "expired-within-leeway": make_token(exp=now - 10),
    "not-yet-valid": make_token(nbf=now + 3600),
    "wrong-audience": make_token(aud="https://api.bookstore.example/inventory"),
    "audience-list": make_token(aud=["https://api.bookstore.example/inventory",
                                     "https://api.bookstore.example/orders"]),
    "wrong-issuer": make_token(iss="https://evil.example"),
    "no-exp": make_token(drop=["exp"]),
    "id-token-type": make_token(headers={"typ": "JWT"}),
    "forged-signature": make_token(key=other_key),
    "read-only-scope": make_token(scope="orders:read"),
}

out = Path(__file__).parent / "tokens"
out.mkdir(exist_ok=True)
for name, token in cases.items():
    (out / f"{name}.jwt").write_text(token)
print(f"wrote {len(cases)} tokens to {out.name}/")
