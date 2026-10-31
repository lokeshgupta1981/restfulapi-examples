"""Print sample IDs and check the properties the article talks about."""
import uuid
from datetime import datetime, timezone

from ulid import ULID

from ids import KINDS, created_at, new_id

print("1. Sample IDs")
for kind in KINDS:
    for _ in range(2):
        value = new_id(kind)
        print(f"   {kind:5}  {value}  ({len(value)} chars)")

print("\n2. Creation time inside the ID")
for kind in KINDS:
    value = new_id(kind)
    print(f"   {kind:5}  {value}  -> {created_at(value)}")
print(f"   now (UTC)  {datetime.now(timezone.utc)}")

print("\n3. Does sorting the text give the creation order?")
for kind in KINDS:
    created = [new_id(kind) for _ in range(10_000)]
    print(f"   {kind:5}  10,000 IDs in a tight loop: sorted == created order? {sorted(created) == created}")

print("\n4. Same-millisecond neighbours (5 IDs in a row)")
for kind in ("uuid7", "ulid"):
    print(f"   {kind}:")
    for value in [new_id(kind) for _ in range(5)]:
        print(f"     {value}")

print("\n5. Can we guess the next ID from the last one?")
first = ULID()
second = ULID()
guess = ULID.from_int(int(first) + 1)
print(f"   ulid  last seen {first}, guess {guess}, actual next {second}, guess right? {guess == second}")
a, b = uuid.uuid7(), uuid.uuid7()
counter = lambda u: (((u.int >> 64) & 0xfff) << 30) | ((u.int >> 32) & 0x3fffffff)
print(f"   uuid7 last seen {a}, actual next {b}")
print(f"         42-bit counter: {counter(a)} -> {counter(b)} (+{counter(b) - counter(a)}),"
      f" 32 random bits: {a.int & 0xffffffff:08x} -> {b.int & 0xffffffff:08x}")

print("\n6. Same 128 bits, two spellings")
u7 = uuid.uuid7()
print(f"   UUIDv7 text      {u7}")
print(f"   as ULID text     {ULID.from_uuid(u7)}")
print(f"   with prefix      ord_{str(ULID.from_uuid(u7)).lower()}")
