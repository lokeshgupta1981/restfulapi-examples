"""Compares the body size of the same ticket in each format.

Run: python sizes.py   (needs requests, which brings urllib3)
"""
import base64
import json
import random
from urllib.parse import urlencode

from urllib3 import encode_multipart_formdata

BOUNDARY = "----formdata-boundary-0123456789"  # 32 characters, like a real client


def multipart_size(fields):
    body, _ = encode_multipart_formdata(fields, boundary=BOUNDARY)
    return len(body)


fields = {"subject": "Login fails & shows 500", "priority": "high"}
print("Text fields only:")
print("  x-www-form-urlencoded:", len(urlencode(fields)))
print("  application/json:     ", len(json.dumps(fields, separators=(",", ":"))))
print("  multipart/form-data:  ", multipart_size(fields))

attachment = random.Random(42).randbytes(30_000)  # 30,000 bytes of binary data
print("Text fields plus a 30,000-byte binary file:")
form_raw = urlencode({**fields, "attachment": attachment})
form_b64 = urlencode({**fields, "attachment": base64.b64encode(attachment)})
json_b64 = json.dumps({**fields, "attachment": base64.b64encode(attachment).decode()},
                      separators=(",", ":"))
multipart = multipart_size({**fields, "attachment": ("error.bin", attachment, "application/octet-stream")})
print("  x-www-form-urlencoded, raw bytes:", len(form_raw))
print("  x-www-form-urlencoded, Base64:   ", len(form_b64))
print("  application/json, Base64:        ", len(json_b64))
print("  multipart/form-data, raw bytes:  ", multipart)
