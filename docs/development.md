# Development — platform-backend

## Prerequisites

- Python 3.12+
- Docker Desktop (for infra)

## 1. Start infrastructure

```bash
./infra/local/run.sh
```

Or from repo root:

```bash
bash infra/local/run.sh
```

## 2. Start this API

```bash
./scripts/run.sh
```

Runs on **http://localhost:8002** (creates `.venv` and `.env` on first run).

## Health check

```bash
curl http://localhost:8002/health
```

## Stop infra

```bash
cd infra/local && docker compose down
```
