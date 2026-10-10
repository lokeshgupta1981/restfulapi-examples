"""Discovers how to get a token for an API from its 401 response (RFC 9728 and RFC 8414).

Usage: python discover.py http://127.0.0.1:8000/orders
"""
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

CLIENT_ID, CLIENT_SECRET = "orders-cli", "orders-cli-secret"  # registered with the authorization server


def get(url, token=None):
    req = urllib.request.Request(url)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, resp.headers, json.load(resp)
    except urllib.error.HTTPError as err:
        body = err.read()
        return err.code, err.headers, json.loads(body) if body.startswith(b"{") else {}


def well_known_url(identifier, suffix):
    """Inserts /.well-known/<suffix> between the host and the path (RFC 9728 section 3)."""
    parts = urllib.parse.urlsplit(identifier)
    path = parts.path.rstrip("/") + (f"?{parts.query}" if parts.query else "")
    return f"{parts.scheme}://{parts.netloc}/.well-known/{suffix}{path}"


def main(resource_url):
    # Step 1: call the API without a token
    status, headers, _ = get(resource_url)
    challenge = headers.get("WWW-Authenticate", "")
    print(f"1. GET {resource_url} -> HTTP {status}")
    print(f"   WWW-Authenticate: {challenge}")

    # Step 2: read the metadata URL from the challenge, or build the well-known URL
    found = re.search(r'resource_metadata="([^"]+)"', challenge)
    if found:
        candidates = [found.group(1)]
    else:  # no header: try the path-based URL first, then the root (the MCP order)
        root = urllib.parse.urlsplit(resource_url)
        candidates = [well_known_url(resource_url, "oauth-protected-resource"),
                      f"{root.scheme}://{root.netloc}/.well-known/oauth-protected-resource"]
    scope = (re.search(r'scope="([^"]+)"', challenge) or [None, ""])[1]
    for metadata_url in candidates:
        status, _, prm = get(metadata_url)
        print(f"2. GET {metadata_url} -> HTTP {status}")
        if status == 200:
            break
    else:
        sys.exit("STOP: no protected resource metadata found")
    print("   " + json.dumps(prm))

    # Step 3: the resource value must be identical to the URL we called
    if prm.get("resource") != resource_url:
        print(f"3. STOP: resource {prm.get('resource')!r} does not match {resource_url!r}, metadata not used")
        sys.exit(1)
    print("3. resource matches the URL we called")

    # Step 4: read the authorization server metadata (RFC 8414)
    issuer = prm["authorization_servers"][0]
    status, _, asm = get(well_known_url(issuer, "oauth-authorization-server"))
    print(f"4. GET {well_known_url(issuer, 'oauth-authorization-server')} -> HTTP {status}")
    print(f"   token_endpoint: {asm['token_endpoint']}")
    if asm.get("issuer") != issuer:
        sys.exit("STOP: issuer does not match")

    # Step 5: get a token for this resource (RFC 8707 resource parameter)
    form = {"grant_type": "client_credentials", "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
            # scope from the challenge first, all of scopes_supported only when the challenge has none (MCP rule)
            "scope": scope or " ".join(prm.get("scopes_supported", [])), "resource": prm["resource"]}
    with urllib.request.urlopen(asm["token_endpoint"], data=urllib.parse.urlencode(form).encode(), timeout=5) as resp:
        token = json.load(resp)
    print(f"5. POST {asm['token_endpoint']} -> HTTP {resp.status}, scope {token['scope']!r}, expires_in {token['expires_in']}")

    # Step 6: repeat the first request with the token
    status, _, body = get(resource_url, token["access_token"])
    print(f"6. GET {resource_url} with token -> HTTP {status}, {len(body)} orders")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000/orders")
