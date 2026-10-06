#!/bin/sh
set -eu

cd /app/website
npm run dev -- --hostname 0.0.0.0 --port 3000 &
website_pid=$!

cd /app/backoffice
npm run dev -- --hostname 0.0.0.0 --port 3001 &
backoffice_pid=$!

stop_apps() {
  trap - INT TERM EXIT
  kill "$website_pid" "$backoffice_pid" 2>/dev/null || true
  wait "$website_pid" "$backoffice_pid" 2>/dev/null || true
}

trap stop_apps INT TERM EXIT

while kill -0 "$website_pid" 2>/dev/null && kill -0 "$backoffice_pid" 2>/dev/null; do
  sleep 1
done

exit 1