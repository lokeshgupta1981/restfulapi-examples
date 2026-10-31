"""Measures the cost of DPoP on one CPU core: creating a proof (client) and checking it (server)."""
import time

import dpop

N = 2000
URL = "https://api.example.com/orders"
TOKEN = "demo-access-token"
key = dpop.new_key()

start = time.perf_counter()
proofs = [dpop.make_proof(key, "GET", URL, access_token=TOKEN) for _ in range(N)]
make_ms = (time.perf_counter() - start) * 1000 / N

replay = dpop.ReplayCache()
start = time.perf_counter()
for p in proofs:
    dpop.verify_proof([p], "GET", URL, replay, access_token=TOKEN)
verify_ms = (time.perf_counter() - start) * 1000 / N

print(f"{N} proofs, ES256 (P-256)")
print(f"create a proof: {make_ms:.3f} ms on average")
print(f"check a proof:  {verify_ms:.3f} ms on average")
print(f"proof size:     {len(proofs[0])} characters")
