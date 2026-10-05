#!/usr/bin/env bash
# Stops everything start.sh started.
cd "$(dirname "$0")"
nginx -p "$PWD/nginx" -c nginx.conf -s stop 2> /dev/null
[ -f .pids ] && kill $(cat .pids) 2> /dev/null
rm -f .pids
