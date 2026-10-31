"""Prints one token: python issue.py jws|jwe|nested|forged-jwe|forged-nested"""
import sys

from jwcrypto import jwk

import tokens as t

kind = sys.argv[1]
if kind.startswith("forged"):
    claims = t.claims_for(user_id="admin", email="mallory@example.com")
    claims["scope"] = "orders:read orders:write"
else:
    claims = t.claims_for()

if kind == "jws":
    print(t.make_jws(claims))
elif kind in ("jwe", "forged-jwe"):
    print(t.make_jwe(claims))
elif kind == "nested":
    print(t.make_nested(claims))
elif kind == "forged-nested":
    attacker_key = jwk.JWK.generate(kty="EC", crv="P-256", kid="auth-server-signing-demo")
    print(t.make_nested(claims, signing_key=attacker_key))
else:
    sys.exit(__doc__)
