#!/usr/bin/env bash
set +e
PRUNE_VOLUMES="${PRUNE_VOLUMES:-0}"

echo "=== Docker: remove unused data (emergency) ==="
df -h / 2>/dev/null || true

if command -v sudo >/dev/null 2>&1; then
  sudo rm -rf /var/lib/containerd/io.containerd.content.v1.content/ingest/* 2>/dev/null
  sudo find /var/lib/docker/tmp -mindepth 1 -maxdepth 1 -type d -exec rm -rf {} + 2>/dev/null
  sudo journalctl --vacuum-size=80M 2>/dev/null
fi

docker container prune -f 2>/dev/null
docker network prune -f 2>/dev/null
docker image prune -af 2>/dev/null
docker builder prune -af 2>/dev/null
docker system prune -af 2>/dev/null

for id in $(docker images -q 2>/dev/null | sort -u); do
  [ -z "$id" ] && continue
  [ -z "$(docker ps -aq --filter "ancestor=${id}" 2>/dev/null)" ] && docker rmi -f "$id" 2>/dev/null
done

[ "$PRUNE_VOLUMES" = "1" ] && docker volume prune -f 2>/dev/null

if command -v sudo >/dev/null 2>&1; then
  sudo rm -rf /var/lib/containerd/io.containerd.content.v1.content/ingest/* 2>/dev/null
fi

docker system df 2>/dev/null || true
df -h / 2>/dev/null || true
exit 0
