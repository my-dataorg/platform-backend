#!/usr/bin/env bash
set -eu

MIN_FREE_MB="${MIN_FREE_MB:-800}"
MIN_FREE_KB=$((MIN_FREE_MB * 1024))
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -x "$SCRIPT_DIR/docker-remove-unused.sh" ]; then
  PRUNE_VOLUMES="${PRUNE_VOLUMES:-0}" "$SCRIPT_DIR/docker-remove-unused.sh"
else
  set +e
  docker container prune -f 2>/dev/null
  docker image prune -af 2>/dev/null
  docker system prune -af 2>/dev/null
fi

avail_kb=$(df -k / | awk 'NR==2 {print $4}')
if [ "$MIN_FREE_MB" = "0" ]; then
  exit 0
fi
if [ "${avail_kb:-0}" -lt "$MIN_FREE_KB" ]; then
  echo "ERROR: Only $((avail_kb / 1024)) MiB free on /; need at least ${MIN_FREE_MB} MiB." >&2
  exit 1
fi
