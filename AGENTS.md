# Cursor agents — platform-backend

Platform API: user profile, product catalog, subscriptions. Includes local infra (Postgres, Keycloak).

## Agents (`.cursor/agents/`)

| Agent | When to use |
|-------|-------------|
| **architect** | API shape, cross-product integration |
| **planner** | Task breakdown before coding |
| **testing-agent** | Run `pytest` after changes |
| **code-review** | Review diff |
| **refactor** | Simplify services |
| **documentation** | Update `docs/api.md` when routes change |

## Feature flow

```
planner → implement → testing-agent → code-review → documentation
```

## Docs in this repo

| Doc | Purpose |
|-----|---------|
| [README.md](README.md) | Run API, port 8002 |
| [docs/api.md](docs/api.md) | REST contract |
| [docs/architecture.md](docs/architecture.md) | Data ownership, auth |
| [infra/local/README.md](infra/local/README.md) | Docker Compose |

## Rules

See `.cursor/rules/` — especially `backend-python`, `platform-core`, `api-boundaries`.

## Related repos

- [platform-frontend](https://github.com/my-dataorg/platform-frontend)
- Product backends check subscriptions via this API
