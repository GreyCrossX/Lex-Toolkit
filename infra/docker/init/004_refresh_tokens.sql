CREATE TABLE IF NOT EXISTS refresh_tokens (
    token_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    secret_hash TEXT NOT NULL,
    revoked BOOLEAN NOT NULL DEFAULT FALSE,
    replaced_by TEXT,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id);
