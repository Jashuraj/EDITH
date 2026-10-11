import { PGlite } from "@electric-sql/pglite";
import { drizzle } from "drizzle-orm/pglite";
import path from "path";

const globalForDb = globalThis as typeof globalThis & {
  __jarvisPgliteClient?: PGlite;
  __jarvisPgliteDb?: ReturnType<typeof drizzle>;
};

const dataDir = path.join(process.cwd(), ".edith_db");

export const client =
  globalForDb.__jarvisPgliteClient ??
  new PGlite(dataDir);

export const db =
  globalForDb.__jarvisPgliteDb ??
  drizzle(client);

if (process.env.NODE_ENV !== "production") {
  globalForDb.__jarvisPgliteClient = client;
  globalForDb.__jarvisPgliteDb = db;
}

// Ensure database tables exist
client.exec(`
  CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
  );

  CREATE TABLE IF NOT EXISTS owner_sessions (
    id SERIAL PRIMARY KEY,
    token_hash TEXT NOT NULL UNIQUE,
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL
  );

  CREATE TABLE IF NOT EXISTS devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    scopes JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at TIMESTAMPTZ,
    last_ip TEXT,
    battery INTEGER,
    conn_type TEXT,
    revoked_at TIMESTAMPTZ
  );

  CREATE TABLE IF NOT EXISTS pairing_codes (
    id SERIAL PRIMARY KEY,
    code_hash TEXT NOT NULL,
    kind TEXT NOT NULL,
    scopes JSONB NOT NULL,
    label TEXT,
    attempts INTEGER NOT NULL DEFAULT 0,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
  );

  CREATE TABLE IF NOT EXISTS hosts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    agent_version TEXT,
    platform TEXT,
    capabilities JSONB,
    metrics JSONB,
    last_seen_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at TIMESTAMPTZ
  );

  CREATE TABLE IF NOT EXISTS reminders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    notes TEXT,
    due_at TIMESTAMPTZ NOT NULL,
    timezone TEXT NOT NULL DEFAULT 'Asia/Kolkata',
    recurrence TEXT NOT NULL DEFAULT 'none',
    by_weekday JSONB,
    priority TEXT NOT NULL DEFAULT 'normal',
    category TEXT NOT NULL DEFAULT 'general',
    status TEXT NOT NULL DEFAULT 'active',
    last_fired_at TIMESTAMPTZ,
    fire_count INTEGER NOT NULL DEFAULT 0,
    trigger TEXT NOT NULL DEFAULT 'time',
    source TEXT NOT NULL DEFAULT 'ui',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
  );
  CREATE INDEX IF NOT EXISTS reminders_due_idx ON reminders (status, due_at);

  CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    date TEXT NOT NULL,
    time TEXT,
    category TEXT NOT NULL DEFAULT 'event',
    recurrence TEXT NOT NULL DEFAULT 'none',
    notes TEXT,
    color TEXT,
    source TEXT NOT NULL DEFAULT 'user',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
  );
  CREATE INDEX IF NOT EXISTS events_date_idx ON events (date);

  CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id TEXT NOT NULL UNIQUE,
    origin TEXT NOT NULL,
    command TEXT NOT NULL,
    engine TEXT,
    status TEXT NOT NULL,
    result JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ
  );

  CREATE TABLE IF NOT EXISTS host_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID,
    tool TEXT NOT NULL,
    args JSONB NOT NULL,
    risk TEXT NOT NULL,
    summary TEXT NOT NULL,
    status TEXT NOT NULL,
    origin TEXT NOT NULL,
    result JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    claimed_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ
  );
  CREATE INDEX IF NOT EXISTS host_jobs_status_idx ON host_jobs (status);

  CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    reminder_id UUID,
    channel TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    delivered_at TIMESTAMPTZ
  );
  CREATE INDEX IF NOT EXISTS notifications_channel_idx ON notifications (channel, delivered_at);

  CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    at TIMESTAMPTZ NOT NULL DEFAULT now(),
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    detail TEXT,
    ok BOOLEAN NOT NULL DEFAULT true
  );
`).catch((err) => {
  console.error("Failed to initialize database tables:", err);
});

export const pool = client;

