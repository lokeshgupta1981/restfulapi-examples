"""Command line helper for demo.sh.

  python id_tool.py new uuid7            print a new ID
  python id_tool.py future-uuid7         print a UUIDv7 dated one year ahead
  python id_tool.py when <id>            print the creation time hidden in an ID
"""
import sys
from datetime import datetime, timedelta, timezone

from ids import created_at, new_id, uuid7_at

cmd = sys.argv[1]
if cmd == "new":
    print(new_id(sys.argv[2]))
elif cmd == "future-uuid7":
    print(uuid7_at(datetime.now(timezone.utc) + timedelta(days=365)))
elif cmd == "when":
    print(created_at(sys.argv[2]))
