"""Reads an Authorization header by hand, the way frameworks do it inside.

Run it with: python3 parse_header.py
"""
import base64
import binascii
import re

# auth-scheme, one or more spaces, then the credentials (RFC 9110, section 11.4).
AUTHORIZATION = re.compile(r"^([A-Za-z0-9!#$%&'*+.^_`|~-]+) +(\S+)$")


def parse_authorization(value):
    """Returns (scheme in lowercase, credentials), or None for a malformed value."""
    match = AUTHORIZATION.match(value or "")
    if not match:
        return None
    return match.group(1).lower(), match.group(2)


def decode_basic(credentials):
    """Returns (user, password) from Basic credentials, or None."""
    try:
        text = base64.b64decode(credentials, validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return None
    user, colon, password = text.partition(":")
    return (user, password) if colon else None


def scheme_for_log(value):
    """Returns the scheme name for a log line, never the credentials."""
    if not value:
        return "-"
    match = re.match(r"^([A-Za-z][A-Za-z0-9._~+-]{0,19}) ", value)
    return match.group(1) if match else "(malformed)"


if __name__ == "__main__":
    samples = [
        "Basic cmVwb3J0cy1hcHA6ZGVtby1wYXNzLTEyMw==",
        "basic cmVwb3J0cy1hcHA6ZGVtby1wYXNzLTEyMw==",
        "Basic  cmVwb3J0cy1hcHA6ZGVtby1wYXNzLTEyMw==",
        "BasiccmVwb3J0cy1hcHA6ZGVtby1wYXNzLTEyMw==",
        "Basic reports-app:demo-pass-123",
        "Bearer demo-token-123",
    ]
    for value in samples:
        parsed = parse_authorization(value)
        user = decode_basic(parsed[1]) if parsed and parsed[0] == "basic" else None
        print(f"{value:46} -> {parsed} {user or ''}")
    print("log:", scheme_for_log("Bearer demo-token-123"),
          scheme_for_log("BasiccmVwb3J0cy1hcHA6ZGVtby1wYXNzLTEyMw=="))
