#!/usr/bin/env bash
# Starts the backends (port 9001) and the gateways (port 8000), then runs every case.
set -u
PY=${PYTHON:-python3}
rm -f gateway.log alpha_down.flag
$PY -m uvicorn backends:app --host 127.0.0.1 --port 9001 --log-level warning &
B=$!
$PY -m uvicorn gateway:app --host 127.0.0.1 --port 8000 --log-level warning &
G=$!
for i in $(seq 1 50); do curl -s -o /dev/null http://127.0.0.1:8000/docs && curl -s -o /dev/null http://127.0.0.1:9001/docs && break; sleep 0.2; done
quote() { for a in "$@"; do case "$a" in *[\ \"]*) printf " '%s'" "$a";; *) printf " %s" "$a";; esac; done; }
run() { echo "\$ python demo.py$(quote "$@")"; $PY demo.py "$@"; echo; }

echo "== AI gateway 1. Support team calls the alias fast =="
run chat vk-support-123 fast "Customer says the invoice total is wrong."
echo "== AI gateway 2. Provider alpha fails, the gateway falls back to beta =="
touch alpha_down.flag
run chat vk-support-123 fast "Refund request for order 1042."
rm -f alpha_down.flag
echo "== AI gateway 3. Support team uses up its token budget =="
run chat vk-support-123 fast "Please summarize the full conversation history of this customer account for me."
echo "== AI gateway 4. Support team asks for a model it may not use =="
run chat vk-support-123 smart "Draft a reply."

echo "== MCP gateway 1. Each team sees only its tools =="
run tools mcp-support-token
run tools mcp-admin-token
echo "== MCP gateway 2. Support calls an allowed tool and a hidden tool =="
run call mcp-support-token crm__search_customers '{"query": "Ana"}'
run call mcp-support-token crm__delete_customer '{"id": "c-7"}'

echo "== Gateway log =="
cat gateway.log
kill $G $B; wait $G $B 2>/dev/null
