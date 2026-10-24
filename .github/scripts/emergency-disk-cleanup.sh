#!/usr/bin/env bash
# Run on the VPS via: ssh user@host 'bash -s' < emergency-disk-cleanup.sh
set +e

echo "=== Emergency Docker disk cleanup ==="
df -h / 2>/dev/null || true

if command -v sudo >/dev/null 2>&1; then
  sudo rm -rf /var/lib/containerd/io.containerd.content.v1.content/ingest/* 2>/dev/null
  sudo find /var/lib/docker/tmp -mindepth 1 -maxdepth 1 -type d -exec rm -rf {} + 2>/dev/null
  sudo journalctl --vacuum-size=50M 2>/dev/null
fi

docker container prune -f 2>/dev/null
docker network prune -f 2>/dev/null
docker image prune -af 2>/dev/null
docker builder prune -af 2>/dev/null
docker system prune -af 2>/dev/null

ids=$(docker images 'ghcr.io/my-dataorg/*' -q 2>/dev/null | sort -u)
if [ -n "$ids" ]; then
  while read -r id; do
    [ -z "$id" ] && continue
    if [ -z "$(docker ps -aq --filter "ancestor=${id}" 2>/dev/null)" ]; then
      docker rmi -f "$id" 2>/dev/null
    fi
  done <<< "$ids"
fi

if command -v sudo >/dev/null 2>&1; then
  sudo rm -rf /var/lib/containerd/io.containerd.content.v1.content/ingest/* 2>/dev/null
fi

echo "=== After cleanup ==="
df -h / 2>/dev/null || true
exit 0
