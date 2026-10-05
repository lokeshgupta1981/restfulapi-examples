#!/usr/bin/env bash
# Calls the Projects API with each case. Start the API first: uvicorn app:app --port 9130
BASE=${BASE:-http://localhost:9130}

call() {
  echo "### $1"
  shift
  curl -s -i "$@" | grep -v -i -E '^(date|server|content-length):'
  echo
  echo
}

call "1. No credentials" "$BASE/projects/p-100"
call "2. Basic credentials instead of a bearer token" -u alice:secret "$BASE/projects/p-100"
call "3. Malformed Authorization header" -H "Authorization: Bearer a b" "$BASE/projects/p-100"
call "4. Unknown token" -H "Authorization: Bearer tok-nobody" "$BASE/projects/p-100"
call "5. Expired token" -H "Authorization: Bearer tok-alice-old" "$BASE/projects/p-100"
call "6. Suspended account" -H "Authorization: Bearer tok-dave" "$BASE/projects/p-100"
call "7. Alice reads her tenant's project" -H "Authorization: Bearer tok-alice" "$BASE/projects/p-100"
call "8. Alice reads a project that does not exist" -H "Authorization: Bearer tok-alice" "$BASE/projects/p-999"
call "9. Alice reads another tenant's project" -H "Authorization: Bearer tok-alice" "$BASE/projects/p-200"
call "10. Carol reads Alice's private project" -H "Authorization: Bearer tok-carol" "$BASE/projects/p-101"
call "11. Carol deletes with a read-only token" -X DELETE -H "Authorization: Bearer tok-carol" "$BASE/projects/p-100"
call "12. Alice deletes Erin's project" -X DELETE -H "Authorization: Bearer tok-alice" "$BASE/projects/p-102"
call "13. Alice opens the admin audit log" -H "Authorization: Bearer tok-alice" "$BASE/admin/audit-log"
call "14. Unknown path without credentials" "$BASE/no-such-path"
call "15. Unknown path with a valid token" -H "Authorization: Bearer tok-alice" "$BASE/no-such-path"
call "16. Alice deletes her own project" -X DELETE -H "Authorization: Bearer tok-alice" "$BASE/projects/p-100"
