"""Demo wallets for the simulated payment rail. Never use fixed keys like these for real money."""

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

# Fixed 32-byte seeds so every run prints the same output.
SEEDS = {"demo-buyer-wallet": bytes(range(32)), "demo-poor-wallet": bytes(range(32, 64))}
PRIVATE_KEYS = {name: Ed25519PrivateKey.from_private_bytes(seed) for name, seed in SEEDS.items()}
PUBLIC_KEYS = {name: key.public_key() for name, key in PRIVATE_KEYS.items()}
STARTING_BALANCES = {"demo-buyer-wallet": 10000, "demo-poor-wallet": 1000}  # atomic units, 6 decimals
