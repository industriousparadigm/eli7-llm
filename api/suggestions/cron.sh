#!/usr/bin/env bash
# Runs the suggestion pool generator once, via the API's venv, with the repo's
# .env loaded. Meant to be invoked by cron every 6h - see README.md for the
# line. Guards against overlapping runs with flock (belt-and-braces now that
# it's scheduled 4x/day instead of once) - falls back to running unguarded if
# flock isn't available on the host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_DIR="$(dirname "$SCRIPT_DIR")"
REPO_ROOT="$(dirname "$API_DIR")"

cd "$API_DIR"

if [ -f "$REPO_ROOT/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . "$REPO_ROOT/.env"
  set +a
fi

if command -v flock >/dev/null 2>&1; then
  exec flock -n "$SCRIPT_DIR/.generate.lock" .venv/bin/python suggestions/generate.py
else
  exec .venv/bin/python suggestions/generate.py
fi
