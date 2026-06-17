# platform-backend

Unified MyData platform API: user profile, product catalog, and subscriptions.

**Org:** [my-dataorg](https://github.com/my-dataorg) · **Stack:** FastAPI · SQLAlchemy · PostgreSQL · Keycloak JWT

Replaces the former split between `platform-auth` and `platform-subscriptions`.

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8002
```

## Infrastructure

```bash
cd infra/local && docker compose up -d
```

See [infra/local/README.md](infra/local/README.md) for Keycloak, Postgres, Redis, NATS.

Demo user: `demo@mydata.local` / `demo1234`

## API summary (port 8002)

| Route | Purpose |
|-------|---------|
| `GET /health` | Health check |
| `GET /v1/users/me` | Current user profile |
| `GET /v1/products` | Marketplace catalog |
| `GET /v1/users/me/subscriptions` | Entitlements |
| `POST /v1/users/me/subscriptions?productSlug=` | Subscribe |

Full spec: [docs/api.md](docs/api.md)

## Documentation

| Doc | Description |
|-----|-------------|
| [AGENTS.md](AGENTS.md) | Cursor agents |
| [docs/api.md](docs/api.md) | REST contract |
| [docs/architecture.md](docs/architecture.md) | Ownership and auth |
| [docs/organization.md](docs/organization.md) | GitHub org repo map |

## Related repos

| Repo | Port |
|------|------|
| [platform-frontend](https://github.com/my-dataorg/platform-frontend) | 3000 |
| [education-backend](https://github.com/my-dataorg/education-backend) | 8010 |

## Tests

```bash
pytest
```
