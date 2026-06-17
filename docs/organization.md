# Organization — MyData repos

GitHub org: **[my-dataorg](https://github.com/my-dataorg)**

## Repo naming

```
platform-frontend / platform-backend
<module>-frontend / <module>-backend
```

Modules: `education`, `social`, …

## Repositories

| Repo | Type | Port (local) |
|------|------|--------------|
| [platform-frontend](https://github.com/my-dataorg/platform-frontend) | Platform UI | 3000 |
| [platform-backend](https://github.com/my-dataorg/platform-backend) | Platform API + infra | 8002 |
| [education-frontend](https://github.com/my-dataorg/education-frontend) | Product UI | 3010 |
| [education-backend](https://github.com/my-dataorg/education-backend) | Product API | 8010 |
| [social-frontend](https://github.com/my-dataorg/social-frontend) | Product UI (scaffold) | 3020 |
| [social-backend](https://github.com/my-dataorg/social-backend) | Product API (scaffold) | 8020 |

## Not separate repos

The following are **merged or deprecated** — do not create standalone repos:

- ~~platform-auth~~ → `platform-backend`
- ~~platform-subscriptions~~ → `platform-backend`
- ~~platform-contracts~~ → document APIs in each repo's `docs/api.md`
- ~~platform-dashboard / platform-marketplace~~ → `platform-frontend`

## Dependency direction

```
platform-backend  ←  platform-frontend, education-backend, social-backend
education-backend ✗  social-backend   (no shared DB; optional HTTP/events later)
```

## Local workspace layout

Clone repos as siblings:

```
~/workspace/mydata/
├── platform-frontend/
├── platform-backend/
├── education-frontend/
├── education-backend/
├── social-frontend/
└── social-backend/
```

Each repo contains its own `README.md`, `AGENTS.md`, and `docs/`.
