-- Session persistence — cookie-based login that survives page refresh
CREATE TABLE IF NOT EXISTS user_sessions (
    token TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_user_sessions_expires ON user_sessions (expires_at);

ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY service_role_all_sessions ON user_sessions
    FOR ALL USING (auth.role() = 'service_role');
