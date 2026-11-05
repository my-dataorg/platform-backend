#!/usr/bin/env bash
# Deploy a single Compose service with a pinned GHCR image digest.
set -eu

DEPLOY_PATH="${DEPLOY_PATH:-/opt/mydata/production}"
SERVICE="${SERVICE:?SERVICE is required}"
IMAGE="${IMAGE:?IMAGE is required}"

cd "$DEPLOY_PATH"

image_variable=$(printf '%s' "$SERVICE" | tr '[:lower:]-' '[:upper:]_')_IMAGE
[ -f service.env ] && cp service.env service.env.previous || true
printf '%s=%s\n' "$image_variable" "$IMAGE" > service.env
export "$image_variable=$IMAGE"

compose() {
  args=(-p production --env-file .env)
  [ -f image.env ] && args+=(--env-file image.env)
  [ -f service.env ] && args+=(--env-file service.env)
  docker compose "${args[@]}" "$@"
}

remove_stale_service_container() {
  local svc="$1"
  compose stop "$svc" 2>/dev/null || true
  compose rm -f "$svc" 2>/dev/null || true
  local id name
  for id in $(docker ps -aq --filter "name=${svc}" 2>/dev/null); do
    docker rm -f "$id" 2>/dev/null || true
  done
  while read -r id name; do
    [ -z "$id" ] && continue
    case "$name" in
      *"production-${svc}"*) docker rm -f "$id" 2>/dev/null || true ;;
    esac
  done < <(docker ps -a --format '{{.ID}} {{.Names}}' 2>/dev/null || true)
}

rollback() {
  if [ -f service.env.previous ]; then
    cp service.env.previous service.env
  else
    rm -f service.env
  fi
  remove_stale_service_container "$SERVICE"
  compose up -d --force-recreate --no-deps "$SERVICE" 2>/dev/null || true
  exit 1
}
trap rollback ERR

if ! compose config --services 2>/dev/null | grep -qx "$SERVICE"; then
  echo "Service $SERVICE is missing from $DEPLOY_PATH/compose.yml." >&2
  echo "Run mydata → Deploy production once to upload compose.yml." >&2
  exit 1
fi

ensure_postgres_db() {
  local db_name="$1"
  local pg
  pg=$(compose ps -q postgres 2>/dev/null | head -n1)
  [ -n "$pg" ] || { echo "Postgres is not running." >&2; exit 1; }
  local exists
  exists=$(docker exec "$pg" psql -U mydata -d postgres -tAc \
    "SELECT 1 FROM pg_database WHERE datname = '${db_name}'" 2>/dev/null || true)
  [ "$(echo "$exists" | tr -d '[:space:]')" = "1" ] && return 0
  docker exec "$pg" psql -U mydata -d postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE ${db_name};"
}

case "$SERVICE" in
  business-backend) ensure_postgres_db business_db ;;
esac

wait_for_platform_backend() {
  echo "Ensuring platform-backend is running..."
  compose up -d postgres nats platform-backend
  local bc=""
  for attempt in $(seq 1 36); do
    bc=$(compose ps -q platform-backend 2>/dev/null | head -n1)
    if [ -n "$bc" ]; then
      if docker exec "$bc" python -c 'from urllib.request import urlopen; urlopen("http://127.0.0.1:8002/health", timeout=3)' 2>/dev/null; then
        echo "platform-backend is healthy"
        return 0
      fi
      if [ "$(docker inspect -f '{{.State.Status}}' "$bc" 2>/dev/null)" = "exited" ]; then
        echo "platform-backend exited; recent logs:" >&2
        docker logs "$bc" 2>&1 | tail -n 50 >&2 || true
      fi
    fi
    sleep 5
  done
  echo "platform-backend did not become healthy" >&2
  exit 1
}

if [ "$SERVICE" = "platform-frontend" ]; then
  wait_for_platform_backend
fi

if [ -x ./docker-free-disk.sh ]; then
  MIN_FREE_MB=0 ./docker-free-disk.sh
  MIN_FREE_MB=300 ./docker-free-disk.sh
fi

repo="ghcr.io/my-dataorg/${SERVICE}"
for id in $(docker images "${repo}" -q 2>/dev/null | sort -u); do
  [ -z "$(docker ps -aq --filter "ancestor=${id}" 2>/dev/null || true)" ] && docker rmi -f "$id" 2>/dev/null || true
done

docker pull "$IMAGE"
remove_stale_service_container "$SERVICE"
compose up -d --force-recreate --no-deps "$SERVICE"

container=""
for attempt in $(seq 1 15); do
  container=$(compose ps -q "$SERVICE" 2>/dev/null | head -n1)
  if [ -n "$container" ] && docker inspect -f '{{.State.Running}}' "$container" 2>/dev/null | grep -qx true; then
    break
  fi
  sleep 2
done
[ -n "$container" ] || { compose ps >&2 || true; rollback; }

case "$SERVICE" in
  platform-backend) check="python -c 'from urllib.request import urlopen; urlopen(\"http://127.0.0.1:8002/health\", timeout=2)'" ;;
  education-backend) check="python -c 'from urllib.request import urlopen; urlopen(\"http://127.0.0.1:8010/health\", timeout=2)'" ;;
  social-backend) check="python -c 'from urllib.request import urlopen; urlopen(\"http://127.0.0.1:8020/health\", timeout=2)'" ;;
  pokerworld-backend) check="python -c 'from urllib.request import urlopen; urlopen(\"http://127.0.0.1:8030/health\", timeout=2)'" ;;
  business-backend) check="python -c 'from urllib.request import urlopen; urlopen(\"http://127.0.0.1:8040/health\", timeout=2)'" ;;
  platform-frontend)
    check="node -e 'fetch(\"http://127.0.0.1:3000/api/auth/session\").then(r => process.exit(r.ok ? 0 : 1)).catch(() => process.exit(1))'"
    backend_check="node -e 'fetch(\"http://platform-backend:8002/health\").then(r => process.exit(r.ok ? 0 : 1)).catch(() => process.exit(1))'"
    ;;
  education-frontend) check="node -e 'fetch(\"http://127.0.0.1:3010/api/auth/session\").then(r => process.exit(r.ok ? 0 : 1)).catch(() => process.exit(1))'" ;;
  pokerworld-frontend) check="node -e 'fetch(\"http://127.0.0.1:3110/api/auth/session\").then(r => process.exit(r.ok ? 0 : 1)).catch(() => process.exit(1))'" ;;
  business-frontend) check="node -e 'fetch(\"http://127.0.0.1:3120/api/auth/session\").then(r => process.exit(r.ok ? 0 : 1)).catch(() => process.exit(1))'" ;;
  *) check="" ;;
esac

if [ -n "$check" ]; then
  for attempt in $(seq 1 30); do
    docker exec "$container" sh -c "$check" >/dev/null 2>&1 && break
    [ "$attempt" = 30 ] && { docker logs "$container" 2>&1 | tail -n 80 >&2 || true; rollback; }
    sleep 5
  done
fi

if [ -n "${backend_check:-}" ]; then
  for attempt in $(seq 1 12); do
    docker exec "$container" sh -c "$backend_check" >/dev/null 2>&1 && break
    [ "$attempt" = 12 ] && {
      echo "platform-frontend cannot reach platform-backend on Docker network" >&2
      bc=$(compose ps -q platform-backend 2>/dev/null | head -n1)
      [ -n "$bc" ] && docker logs "$bc" 2>&1 | tail -n 50 >&2 || true
      rollback
    }
    sleep 5
  done
fi

trap - ERR
rm -f service.env.previous
docker image prune -f 2>/dev/null || true
echo "Deployed $SERVICE OK"
