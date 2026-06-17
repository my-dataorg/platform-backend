# Local development

## Start infrastructure

```bash
cd infra/local
docker compose up -d
```

Wait for Keycloak: http://localhost:8080 (admin / admin)

## Demo login

- Email: `demo@mydata.local`
- Password: `demo1234`

## Services

| Service | URL |
|---------|-----|
| Keycloak | http://localhost:8080 |
| Postgres | localhost:5433 (user/pass: mydata) |
| Redis | localhost:6379 |
| NATS | localhost:4222 |
| platform-frontend | http://localhost:3000 |
| platform-backend | http://localhost:8002 |
| education-frontend | http://localhost:3010 |
| education-backend | http://localhost:8010 |

## Databases

`subscriptions_db`, `education_db`, `social_db`, `keycloak_db`
