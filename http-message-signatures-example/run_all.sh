#!/usr/bin/env bash
# Runs every example and prints the output (saved as OUTPUTS.txt).
# Ports are configurable: ORIGIN_PORT (default 8000), DIRECTORY_PORT (default 8001).
set -u
cd "$(dirname "$0")"
ORIGIN_PORT=${ORIGIN_PORT:-8000}
DIRECTORY_PORT=${DIRECTORY_PORT:-8001}
export ORIGIN="http://127.0.0.1:${ORIGIN_PORT}"
export AGENT_URL="http://127.0.0.1:${DIRECTORY_PORT}/.well-known/http-message-signatures-directory"

echo "## 1. Test vectors (RFC 9421 B.2.6, Web Bot Auth draft E.2.1)"
python test_vectors.py
echo
echo "## 2. Verifying ChatGPT agent's signed key directory (snapshot)"
python verify_directory.py
echo

uvicorn bot_directory:app --port "$DIRECTORY_PORT" --log-level warning > directory.log 2>&1 &
DIR_PID=$!
uvicorn server:app --port "$ORIGIN_PORT" --log-level warning > origin.log 2>&1 &
ORIGIN_PID=$!
trap 'kill $DIR_PID $ORIGIN_PID 2>/dev/null' EXIT
for i in $(seq 1 50); do
  curl -s -o /dev/null "$AGENT_URL" && curl -s -o /dev/null "$ORIGIN/books/1" && break
  sleep 0.2
done

echo "## 3. The bot's key directory"
curl -s -i "$AGENT_URL"
echo
echo
echo "## 4. Bookstore API scenarios (bot.py)"
python bot.py
echo
echo "## 5. Origin log"
cat origin.log
rm -f origin.log directory.log
echo
echo "## 6. Live: Cloudflare Research demo server (needs internet)"
python live_cloudflare_demo.py || echo "skipped: no internet access"
