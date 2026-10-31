"""Walks through JWS, JWE and nested JWTs and prints what each one shows."""
import base64
import json
import statistics
import sys
import time

from jwcrypto import jwk

import tokens as t


def b64url_decode(part):
    return base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))


def title(text):
    print(f"\n== {text}")


claims = t.claims_for()

title("1. JWS: a signed JWT")
signed = t.make_jws(claims)
print(signed)
print("parts:", len(signed.split(".")), "->", t.kind_of(signed))
header, payload, signature = signed.split(".")
print("header :", b64url_decode(header).decode())
print("payload:", b64url_decode(payload).decode())
print("signature bytes:", len(b64url_decode(signature)))

title("2. JWS: change one claim and verify again")
forged_payload = json.loads(b64url_decode(payload))
forged_payload["sub"] = "user-99"
forged_part = base64.urlsafe_b64encode(json.dumps(forged_payload).encode()).rstrip(b"=").decode()
try:
    t.verify_jws(f"{header}.{forged_part}.{signature}")
except Exception as e:
    print("rejected:", type(e).__name__, "-", e)

title("3. JWE: an encrypted JWT")
encrypted = t.make_jwe(claims)
print(encrypted[:120] + "...")
print("parts:", len(encrypted.split(".")), "->", t.kind_of(encrypted))
names = ["protected header", "encrypted key", "initialization vector", "ciphertext", "authentication tag"]
for name, part in zip(names, encrypted.split(".")):
    print(f"  {name:<22} {len(b64url_decode(part)):>4} bytes")
print("header :", b64url_decode(encrypted.split(".")[0]).decode())
print("ciphertext, first 24 bytes:", b64url_decode(encrypted.split(".")[3])[:24])
print("decrypted by the Orders API:", t.decrypt_only(encrypted))

title("4. JWE: change one byte of the ciphertext")
p = encrypted.split(".")
ct = bytearray(b64url_decode(p[3]))
ct[0] ^= 1
p[3] = base64.urlsafe_b64encode(bytes(ct)).rstrip(b"=").decode()
try:
    t.decrypt_only(".".join(p))
except Exception as e:
    print("rejected:", type(e).__name__, "-", e)

title("5. JWE: anyone with the public key can create one")
# The attacker only needs the Orders API's PUBLIC key, which is public by design.
fake = t.claims_for(user_id="admin", email="mallory@example.com")
fake["scope"] = "orders:read orders:write"
forged_jwe = t.make_jwe(fake)
print("decrypt_only() accepted:", t.decrypt_only(forged_jwe))

title("6. Nested JWT: signed, then encrypted")
nested = t.make_nested(claims)
print(nested[:120] + "...")
print("parts:", len(nested.split(".")), "->", t.kind_of(nested))
print("outer header:", b64url_decode(nested.split(".")[0]).decode())
print("decrypt_and_verify():", t.decrypt_and_verify(nested))

title("7. Nested JWT: the attacker signs with a key of their own")
attacker_key = jwk.JWK.generate(kty="EC", crv="P-256", kid="auth-server-signing-demo")
forged_nested = t.make_nested(fake, signing_key=attacker_key)
try:
    t.decrypt_and_verify(forged_nested)
except Exception as e:
    print("rejected:", type(e).__name__, "-", e)
try:
    t.decrypt_and_verify(forged_jwe)
except Exception as e:
    print("plain forged JWE rejected:", type(e).__name__, "-", e)

title("8. Token size")
for name, tok in [("JWS (ES256)", signed), ("JWE (RSA-OAEP-256 + A256GCM)", encrypted),
                  ("Nested (JWS inside JWE)", nested)]:
    print(f"  {name:<30} {len(tok):>5} characters")

title("9. Time per token on the Orders API side (median of 5 rounds)")
n = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
for name, fn, tok in [("verify JWS", t.verify_jws, signed),
                      ("decrypt JWE", t.decrypt_only, encrypted),
                      ("decrypt + verify nested", t.decrypt_and_verify, nested)]:
    fn(tok)
    rounds = []
    for _ in range(5):
        start = time.perf_counter()
        for _ in range(n):
            fn(tok)
        rounds.append((time.perf_counter() - start) / n * 1_000_000)
    print(f"  {name:<26} {statistics.median(rounds):6.0f} microseconds "
          f"(rounds: {', '.join(f'{r:.0f}' for r in rounds)}; {n} tokens each)")
