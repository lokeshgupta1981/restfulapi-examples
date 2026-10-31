"""What an HMAC is: a keyed hash that changes with the message and with the key."""
import hashlib
import hmac

secret = b"demo-secret-key-2026-10"  # example value, not a real key


def hmac_hex(key: bytes, message: bytes) -> str:
    return hmac.new(key, message, hashlib.sha256).hexdigest()


print("quantity 2: ", hmac_hex(secret, b'{"item":"keyboard","quantity":2}'))
print("quantity 3: ", hmac_hex(secret, b'{"item":"keyboard","quantity":3}'))
print("other key:  ", hmac_hex(b"guessed-key", b'{"item":"keyboard","quantity":2}'))
print("length:", len(hmac_hex(secret, b"x")), "hex characters (32 bytes)")
