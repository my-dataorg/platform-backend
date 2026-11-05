#!/usr/bin/env bash
# Remove ALL unused Docker data (images, containers, networks, build cache, ingest temp files).
set +e

echo "=== Docker: remove unused data ==="
docker system df 2>/dev/null || true
df -h / 2>/dev/null || true

clear_containerd_ingest() {
  if command -v sudo >/dev/null 2>&1; then
    sudo rm -rf /var/lib/containerd/io.containerd.content.v1.content/ingest/* 2>/dev/null
    sudo find /var/lib/docker/tmp -mindepth 1 -maxdepth 1 -type d -exec rm -rf {} + 2>/dev/null
    sudo find /var/lib/containerd/tmpmounts -mindepth 1 -maxdepth 1 -type d -exec rm -rf {} + 2>/dev/null
  fi
}

remove_images_not_used_by_any_container() {
  local id
  for id in $(docker images -q 2>/dev/null | sort -u); do
    [ -z "$id" ] && continue
    if [ -z "$(docker ps -aq --filter "ancestor=${id}" 2>/dev/null)" ]; then
      docker rmi -f "$id" 2>/dev/null
    fi
  done
}

clear_containerd_ingest

docker container prune -f 2>/dev/null
docker network prune -f 2>/dev/null
docker image prune -af 2>/dev/null
docker builder prune -af 2>/dev/null
docker system prune -af 2>/dev/null
remove_images_not_used_by_any_container

if [ "${PRUNE_VOLUMES:-0}" = "1" ]; then
  docker volume prune -f 2>/dev/null
fi

clear_containerd_ingest
if command -v sudo >/dev/null 2>&1; then
  sudo journalctl --vacuum-size=80M 2>/dev/null
fi

echo "=== After removing unused Docker data ==="
docker system df 2>/dev/null || true
df -h / 2>/dev/null || true
exit 0
