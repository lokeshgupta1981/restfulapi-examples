"""A client that reacts to HTTP 401, 403 and 404 in different ways."""
import sys

import httpx2

BASE = "http://localhost:9130"


class ProjectsClient:
    def __init__(self, access_token, refresh_token):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.http = httpx2.Client(base_url=BASE)

    def refresh(self):
        response = self.http.post("/token", data={"grant_type": "refresh_token",
                                                  "refresh_token": self.refresh_token})
        response.raise_for_status()
        self.access_token = response.json()["access_token"]
        print("  refreshed the access token")

    def request(self, method, path):
        for attempt in (1, 2):
            response = self.http.request(
                method, path, headers={"Authorization": f"Bearer {self.access_token}"})
            print(f"  {method} {path} -> HTTP {response.status_code} (attempt {attempt})")
            challenge = response.headers.get("www-authenticate", "")
            if response.status_code == 401 and 'error="invalid_token"' in challenge and attempt == 1:
                self.refresh()
                continue
            if response.status_code == 401:
                return "sign in again"
            if response.status_code == 403:
                return "show 'no permission': " + response.json()["detail"]
            if response.status_code == 404:
                return "show 'not found' and drop the cached item"
            response.raise_for_status()
            return "ok"


def main():
    client = ProjectsClient(access_token="tok-alice-old", refresh_token="rt-alice")
    for method, path in [("GET", "/projects/p-100"), ("DELETE", "/projects/p-102"),
                         ("GET", "/projects/p-200")]:
        print(f"{method} {path}")
        print("  result:", client.request(method, path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
