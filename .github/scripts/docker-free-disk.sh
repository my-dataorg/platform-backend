#!/usr/bin/env bash
# Free Docker/containerd disk before pull. Does NOT remove named volumes (Postgres data).
set -eu

MIN_FREE_MB="${MIN_FREE_MB:-800}"
MIN_FREE_KB=$((MIN_FREE_MB * 1024))

report() {
  echo "=== $1 ==="
  df -h / /var/lib/docker /var/lib/containerd 2>/dev/null || df -h /
  docker system df 2>/dev/null || true
}

clear_containerd_ingest() {
  if command -v sudo >/dev/null 2>&1; then
    sudo rm -rf /var/lib/containerd/io.containerd.content.v1.content/ingest/* 2>/dev/null || true
    sudo find /var/lib/docker/tmp -mindepth 1 -maxdepth 1 -type d -exec rm -rf {} + 2>/dev/null || true
  fi
}

prune_unused_ghcr_images() {
  local ids
  ids=$(docker images 'ghcr.io/my-dataorg/*' -q 2>/dev/null | sort -u || true)
  [ -z "$ids" ] && return 0
  while read -r id; do
    [ -z "$id" ] && continue
    if [ -z "$(docker ps -aq --filter "ancestor=${id}" 2>/dev/null || true)" ]; then
      docker rmi -f "$id" 2>/dev/null || true
    fi
  done <<< "$ids"
}

report "Disk before cleanup"
clear_containerd_ingest

docker container prune -f 2>/dev/null || true
docker network prune -f 2>/dev/null || true
docker image prune -af 2>/dev/null || true
docker builder prune -af 2>/dev/null || true
docker system prune -af 2>/dev/null || true
prune_unused_ghcr_images
clear_containerd_ingest

if command -v sudo >/dev/null 2>&1; then
  sudo journalctl --vacuum-size=100M 2>/dev/null || true
fi

report "Disk after cleanup"

avail_kb=$(df -k / | awk 'NR==2 {print $4}')
if [ "$MIN_FREE_MB" = "0" ]; then
  exit 0
fi
if [ "${avail_kb:-0}" -lt "$MIN_FREE_KB" ]; then
  echo "ERROR: Only $((avail_kb / 1024)) MiB free on /; need at least ${MIN_FREE_MB} MiB to pull a new image." >&2
  echo "1) Run mydata Actions → Free server disk (branch Srikanth_Changes)" >&2
  echo "2) SSH: sudo rm -rf /var/lib/containerd/.../ingest/* && docker image prune -af" >&2
  echo "3) Resize VPS disk (recommend 40GB+ for full stack)" >&2
  exit 1
fi
