#!/usr/bin/env bash
# Runs every script of the example and prints the output (used to create OUTPUTS.txt).
set -euo pipefail
cd "$(dirname "$0")"
echo "### python3 make_tokens.py && python3 decode_token.py tokens/valid.jwt"
python3 make_tokens.py
python3 decode_token.py tokens/valid.jwt
echo; echo "### ./demo.sh"
./demo.sh
echo "### python3 pitfalls.py"
python3 pitfalls.py
echo; echo "### python3 size.py"
python3 size.py
