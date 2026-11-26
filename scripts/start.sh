#!/bin/sh
# Run on the host. Only this foreground process can change Compose replicas.
set -eu
cd "$(dirname "$0")/.."
docker compose build app
docker compose up -d --wait --scale app=2
echo "Dashboard: http://localhost:8087 — keep this terminal open for automatic scaling."
while :; do
  desired=$(curl -fsS --max-time 3 http://127.0.0.1:8087/desired) || { sleep 2; continue; }
  case "$desired" in
    2|4|6)
      live=$(docker compose ps --status running -q app | wc -l | tr -d ' ')
      if [ "$live" != "$desired" ]; then
        echo "Changing app containers: $live -> $desired"
        docker compose up -d --no-deps --no-recreate --scale "app=$desired" app
      fi ;;
  esac
  sleep 2
done
