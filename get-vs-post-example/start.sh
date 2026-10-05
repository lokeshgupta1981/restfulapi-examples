#!/usr/bin/env bash
# Starts the app (9120), nginx (9121), the broken upstream (9122) and the attacker pages (9123).
set -u
cd "$(dirname "$0")"
mkdir -p nginx/logs nginx/temp nginx/cache
rm -rf nginx/cache/* nginx/logs/*

.venv/bin/uvicorn app:app --port 9120 --log-level warning & echo $! > .pids
.venv/bin/python dropper.py > /dev/null & echo $! >> .pids
(cd attacker && exec ../.venv/bin/python -m http.server 9123 --bind 127.0.0.1 > /dev/null 2>&1) & echo $! >> .pids
nginx -p "$PWD/nginx" -c nginx.conf
sleep 2
