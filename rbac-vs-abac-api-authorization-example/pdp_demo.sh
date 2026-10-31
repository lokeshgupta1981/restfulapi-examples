#!/usr/bin/env bash
# Talks AuthZEN to the PDP directly. Start it first: uvicorn pdp:app --port 8001
PDP=${PDP:-http://127.0.0.1:8001}
KEY=${PDP_KEY:-demo-pep-key-not-secret}

echo "### PDP metadata"
curl -s "$PDP/.well-known/authzen-configuration"; echo; echo

echo "### Can Erin read launch-plan?"
curl -s -i -X POST "$PDP/access/v1/evaluation" \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"subject":{"type":"user","id":"erin"},"action":{"name":"can_read"},"resource":{"type":"document","id":"launch-plan"}}' \
  | grep -v -i -E '^(date|server):'
echo; echo

echo "### Can Erin edit launch-plan?"
curl -s -i -X POST "$PDP/access/v1/evaluation" \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"subject":{"type":"user","id":"erin"},"action":{"name":"can_edit"},"resource":{"type":"document","id":"launch-plan"}}' \
  | grep -v -i -E '^(date|server):'
echo; echo

echo "### Batch: can Alice read, edit and delete pricing-2027?"
curl -s -X POST "$PDP/access/v1/evaluations" \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"subject":{"type":"user","id":"alice"},"resource":{"type":"document","id":"pricing-2027"},"evaluations":[{"action":{"name":"can_read"}},{"action":{"name":"can_edit"}},{"action":{"name":"can_delete"}}]}'
echo; echo

echo "### A caller that is not one of our APIs"
curl -s -i -X POST "$PDP/access/v1/evaluation" -H "Content-Type: application/json" \
  -d '{"subject":{"type":"user","id":"erin"},"action":{"name":"can_read"},"resource":{"type":"document","id":"launch-plan"}}' \
  | grep -v -i -E '^(date|server|content-length):'
echo
