# API — platform-backend

Base URL: `http://localhost:8002` (dev) · Prefix: `/v1` · Auth: `Authorization: Bearer <JWT>`

## Standards

| Aspect | Convention |
|--------|------------|
| Protocol | HTTPS REST (JSON) |
| Auth | Keycloak JWT via JWKS |
| Versioning | URL prefix `/v1/` |
| Errors | `{ "detail": "..." }` (FastAPI default) |
| Pagination | `?cursor=&limit=` on products |

## Identity

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/v1/users/me` | Required | Current user profile |

**Response:**

```json
{ "id": "uuid", "email": "user@example.com", "name": "Display Name" }
```

## Marketplace

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/v1/products` | Optional | Paginated catalog |
| GET | `/v1/products/categories` | Optional | Category counts |

**Query params for `/v1/products`:** `q`, `category`, `featured`, `cursor`, `limit` (max 48)

## Subscriptions

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/v1/users/me/subscriptions` | Required | Active entitlements |
| POST | `/v1/users/me/subscriptions?productSlug=` | Required | Subscribe |

**Subscription item:**

```json
{ "productSlug": "education", "status": "active" }
```

## Consumers

- **platform-frontend** — dashboard and marketplace
- **education-backend** — checks `education` slug in subscriptions before most routes
- **social-backend** (future) — checks `social` slug

## JWT claims

```json
{
  "sub": "user_id",
  "email": "user@example.com",
  "name": "Display Name",
  "iss": "http://localhost:8080/realms/mydata"
}
```

Products validate issuer via Keycloak JWKS — same realm as platform-frontend.
