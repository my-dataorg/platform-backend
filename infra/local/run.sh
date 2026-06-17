#!/usr/bin/env bash
# Start local infra: Postgres, Keycloak, Redis, NATS
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required. Install Docker Desktop and retry."
  exit 1
fi

cd "$DIR"
docker compose up -d

echo ""
echo "Infra starting..."
echo "  Keycloak:  http://localhost:8080  (admin / admin)"
echo "  Postgres:  localhost:5433         (mydata / mydata)"
echo "  Redis:     localhost:6379"
echo "  NATS:      localhost:4222"
echo ""
echo "Wait ~30s for Keycloak on first boot, then start application run scripts."
