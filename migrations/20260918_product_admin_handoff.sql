-- Upgrade existing platform databases before deploying product administration.
-- Run with: psql "$DATABASE_URL" -f migrations/20260918_product_admin_handoff.sql

ALTER TABLE auth_users
    ADD COLUMN IF NOT EXISTS is_superuser BOOLEAN;
UPDATE auth_users SET is_superuser = FALSE WHERE is_superuser IS NULL;
ALTER TABLE auth_users
    ALTER COLUMN is_superuser SET DEFAULT FALSE,
    ALTER COLUMN is_superuser SET NOT NULL;

ALTER TABLE products
    ADD COLUMN IF NOT EXISTS status VARCHAR(16),
    ADD COLUMN IF NOT EXISTS default_path VARCHAR(256),
    ADD COLUMN IF NOT EXISTS embed_enabled BOOLEAN;
UPDATE products SET status = 'enabled' WHERE status IS NULL;
UPDATE products SET default_path = '/' WHERE default_path IS NULL;
UPDATE products SET embed_enabled = TRUE WHERE embed_enabled IS NULL;
ALTER TABLE products
    ALTER COLUMN status SET DEFAULT 'enabled',
    ALTER COLUMN status SET NOT NULL,
    ALTER COLUMN default_path SET DEFAULT '/',
    ALTER COLUMN default_path SET NOT NULL,
    ALTER COLUMN embed_enabled SET DEFAULT TRUE,
    ALTER COLUMN embed_enabled SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_auth_users_single_superuser
    ON auth_users (is_superuser) WHERE is_superuser IS TRUE;

CREATE TABLE IF NOT EXISTS product_audits (
    id VARCHAR(36) PRIMARY KEY,
    actor_user_id VARCHAR(36) NOT NULL,
    product_slug VARCHAR(64) NOT NULL,
    action VARCHAR(32) NOT NULL,
    changed_fields JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_product_audits_actor_user_id
    ON product_audits (actor_user_id);
CREATE INDEX IF NOT EXISTS ix_product_audits_product_slug
    ON product_audits (product_slug);

CREATE TABLE IF NOT EXISTS product_handoffs (
    code_hash VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES auth_users(id),
    product_slug VARCHAR(64) NOT NULL REFERENCES products(slug),
    target_origin VARCHAR(256) NOT NULL,
    return_path VARCHAR(512) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_product_handoffs_user_id
    ON product_handoffs (user_id);
CREATE INDEX IF NOT EXISTS ix_product_handoffs_product_slug
    ON product_handoffs (product_slug);
CREATE INDEX IF NOT EXISTS ix_product_handoffs_expires_at
    ON product_handoffs (expires_at);
