# Architecture — platform-backend

## Owns

| Data | Database |
|------|----------|
| Product catalog metadata | `subscriptions_db.products` |
| User entitlements | `subscriptions_db.user_subscriptions` |

## Does not own

- User passwords or OIDC sessions (Keycloak)
- Institute, section, or assignment data (education-backend)
- Social graph (social-backend)

## Auth

Validates JWT from Keycloak realm `mydata`. Exposes `/v1/users/me` for profile reads.

Products duplicate JWT validation in their own repos — no shared Python package required for MVP.

## Subscription check pattern

Product backends call:

```
GET {platform-backend}/v1/users/me/subscriptions
Authorization: Bearer <same user token>
```

and require product slug (e.g. `education`) in the response.

## Local infra

This repo includes `infra/local/` — Docker Compose for Postgres (multi-DB), Keycloak, Redis, NATS. All product repos document dependency on this stack for local dev.

## Deployment

Single service on port **8002**. Scale independently from product backends.
