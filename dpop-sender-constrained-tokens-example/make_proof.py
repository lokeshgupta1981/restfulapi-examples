"""Prints a DPoP proof for curl. Usage: python make_proof.py METHOD URL [ACCESS_TOKEN]

Keeps a demo key in demo-key.pem (created on first use, never commit it).
"""
import os
import sys

from cryptography.hazmat.primitives import serialization

import dpop

KEY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo-key.pem")
if os.path.exists(KEY_FILE):
    key = serialization.load_pem_private_key(open(KEY_FILE, "rb").read(), None)
else:
    key = dpop.new_key()
    open(KEY_FILE, "wb").write(key.private_bytes(serialization.Encoding.PEM,
                                                 serialization.PrivateFormat.PKCS8,
                                                 serialization.NoEncryption()))
method, url = sys.argv[1], sys.argv[2]
token = sys.argv[3] if len(sys.argv) > 3 else None
print(dpop.make_proof(key, method, url, access_token=token))
