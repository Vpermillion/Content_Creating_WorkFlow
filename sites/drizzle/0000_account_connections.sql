CREATE TABLE oauth_sessions (
  state_hash TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  account TEXT NOT NULL,
  target TEXT NOT NULL,
  verifier TEXT NOT NULL,
  started_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL
);
--> statement-breakpoint
CREATE INDEX oauth_sessions_expiry ON oauth_sessions (expires_at);
--> statement-breakpoint
CREATE TABLE account_connections (
  owner_id TEXT NOT NULL,
  account TEXT NOT NULL,
  provider_id TEXT NOT NULL,
  handle TEXT NOT NULL,
  display_name TEXT NOT NULL,
  grant TEXT NOT NULL,
  expires_at INTEGER,
  started_at INTEGER NOT NULL,
  connected_at INTEGER NOT NULL,
  PRIMARY KEY (owner_id, account)
);

