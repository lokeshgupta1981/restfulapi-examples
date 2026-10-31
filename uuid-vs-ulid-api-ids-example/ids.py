"""Create, parse and inspect the three kinds of IDs used in the article."""
import os
import uuid
from datetime import datetime, timezone

from ulid import ULID

KINDS = ("uuid4", "uuid7", "ulid")


def new_id(kind: str) -> str:
    """Return a new ID of the given kind in its canonical text form."""
    if kind == "uuid4":
        return str(uuid.uuid4())          # 8-4-4-4-12 lowercase hex, 36 chars
    if kind == "uuid7":
        return str(uuid.uuid7())          # Python 3.14 or later
    if kind == "ulid":
        return str(ULID())                # 26 chars, Crockford Base32, uppercase
    raise ValueError(f"unknown kind {kind}")


def parse_id(kind: str, text: str) -> str:
    """Validate an ID from a URL or a request body and return its canonical form.

    Raises ValueError if the text is not a valid ID of this kind.
    """
    if kind == "ulid":
        return str(ULID.from_str(text.upper()))
    u = uuid.UUID(text)                   # accepts upper and lower case
    expected = 4 if kind == "uuid4" else 7
    if u.version != expected or u.variant != uuid.RFC_4122:
        raise ValueError(f"expected a UUIDv{expected}, got version {u.version}")
    return str(u)


def created_at(text: str) -> datetime | None:
    """Read the creation time hidden in a UUIDv7 or a ULID. UUIDv4 has none."""
    if len(text) == 26:
        return ULID.from_str(text.upper()).datetime
    u = uuid.UUID(text)
    if u.version == 7:
        return datetime.fromtimestamp(u.time / 1000, tz=timezone.utc)
    return None


def uuid7_at(when: datetime) -> str:
    """Build a UUIDv7 with a chosen timestamp (used to test the server's checks)."""
    ms = int(when.timestamp() * 1000)
    rand = int.from_bytes(os.urandom(10))
    value = (ms << 80) | (0x7 << 76) | ((rand >> 62) & 0xfff) << 64 | (0b10 << 62) | (rand & ((1 << 62) - 1))
    return str(uuid.UUID(int=value))
