"""Create forged access tokens, signed with a key the attacker made up.

Usage: python forge_token.py <issuer> <kid>
Prints a token with the right issuer, audience and claims, signed with a fresh
RSA key that is not in the issuer's JWKS. Passing the real kid shows that the kid
only selects a key: the signature check still fails.
"""
import sys
import time

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

issuer, kid = sys.argv[1], sys.argv[2]
attacker_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
now = int(time.time())
claims = {"iss": issuer, "sub": "orders-app", "aud": "orders-api", "scope": "orders:read",
          "iat": now, "exp": now + 600}
print(jwt.encode(claims, attacker_key, algorithm="RS256", headers={"kid": kid, "typ": "at+jwt"}))
