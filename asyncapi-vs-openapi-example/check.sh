#!/usr/bin/env bash
# Validates both API documents, then shows what the AsyncAPI validator reports for a broken copy.
cd "$(dirname "$0")"
export SUPPRESS_NO_CONFIG_WARNING=1
echo "== redocly lint openapi.yaml"
npx redocly lint openapi.yaml 2>&1
echo "== asyncapi validate asyncapi.yaml"
npx asyncapi validate asyncapi.yaml 2>&1 | grep -v '^WARNING'
echo "== asyncapi validate asyncapi-broken.yaml"
npx asyncapi validate asyncapi-broken.yaml 2>&1 | grep -v '^WARNING'
exit 0
