#!/usr/bin/env bash
# Runs the client, which starts server.py over stdio. Only the Python standard library is needed.
cd "$(dirname "$0")"
${PYTHON:-python3} client.py
