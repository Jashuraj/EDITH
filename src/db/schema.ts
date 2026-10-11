import {
  pgTable,
  text,
  timestamp,
  integer,
  boolean,
  jsonb,
  serial,
  uuid,
  index,
  uniqueIndex,
} from "drizzle-orm/pg-core";

/** Key/value settings (non-secret preferences: mode, preferred provider, profile, permissions). */
export const settings = pgTable("settings", {
  key: text("key").primaryKey(),
  value: jsonb("value").notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

/** Owner browser sessions (HUD). Only SHA-256 hashes of session tokens are stored. */
export const ownerSessions = pgTable("owner_sessions", {
  id: serial("id").primaryKey(),
  tokenHash: text("token_hash").notNull().unique(),
  userAgent: text("user_agent"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  expiresAt: timestamp("expires_at", { withTimezone: true }).notNull(),
});

/** Paired phones / companion devices. */
export const devices = pgTable("devices", {
  id: uuid("id").defaultRandom().primaryKey(),
  name: text("name").notNull(),
  tokenHash: text("token_hash").notNull().unique(),
  scopes: jsonb("scopes").$type<string[]>().notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  lastSeenAt: timestamp("last_seen_at", { withTimezone: true }),
  lastIp: text("last_ip"),
  battery: integer("battery"),
  connType: text("conn_type"),
  revokedAt: timestamp("revoked_at", { withTimezone: true }),
});

/** One-time, expiring pairing codes (phone pairing and PC host linking). */
export const pairingCodes = pgTable("pairing_codes", {
  id: serial("id").primaryKey(),
  codeHash: text("code_hash").notNull(),
  kind: text("kind").notNull(), // 'device' | 'host'
  scopes: jsonb("scopes").$type<string[]>().notNull(),
  label: text("label"),
  attempts: integer("attempts").default(0).notNull(),
  expiresAt: timestamp("expires_at", { withTimezone: true }).notNull(),
  usedAt: timestamp("used_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

/** Linked Windows host agents (the PC being controlled). */
export const hosts = pgTable("hosts", {
  id: uuid("id").defaultRandom().primaryKey(),
  name: text("name").notNull(),
  tokenHash: text("token_hash").notNull().unique(),
  agentVersion: text("agent_version"),
  platform: text("platform"),
  capabilities: jsonb("capabilities").$type<Record<string, unknown>>(),
  metrics: jsonb("metrics").$type<Record<string, unknown>>(),
  lastSeenAt: timestamp("last_seen_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  revokedAt: timestamp("revoked_at", { withTimezone: true }),
});

/** Reminders, alarms and routine items. Durable; survive restarts. */
export const reminders = pgTable(
  "reminders",
  {
    id: uuid("id").defaultRandom().primaryKey(),
    title: text("title").notNull(),
    notes: text("notes"),
    dueAt: timestamp("due_at", { withTimezone: true }).notNull(),
    timezone: text("timezone").default("Asia/Kolkata").notNull(),
    // none | daily | weekdays | weekly | monthly | yearly
    recurrence: text("recurrence").default("none").notNull(),
    byWeekday: jsonb("by_weekday").$type<number[]>(), // 0=Sun..6=Sat for weekly
    priority: text("priority").default("normal").notNull(), // low | normal | high
    category: text("category").default("general").notNull(), // general | routine | medicine | chore | study | work
    status: text("status").default("active").notNull(), // active | done | dismissed
    lastFiredAt: timestamp("last_fired_at", { withTimezone: true }),
    fireCount: integer("fire_count").default(0).notNull(),
    trigger: text("trigger").default("time").notNull(), // time | manual_arrival
    source: text("source").default("ui").notNull(),
    createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
    updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  },
  (t) => [index("reminders_due_idx").on(t.status, t.dueAt)],
);

/** Calendar events: birthdays, anniversaries, exams, custom holidays, events. */
export const events = pgTable(
  "events",
  {
    id: uuid("id").defaultRandom().primaryKey(),
    title: text("title").notNull(),
    date: text("date").notNull(), // YYYY-MM-DD (local date)
    time: text("time"), // HH:MM or null for all-day
    category: text("category").default("event").notNull(), // birthday | anniversary | exam | holiday | festival | event
    recurrence: text("recurrence").default("none").notNull(), // none | yearly
    notes: text("notes"),
    color: text("color"),
    source: text("source").default("user").notNull(),
    createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  },
  (t) => [index("events_date_idx").on(t.date)],
);

/** Commands/tasks with idempotency (request_id) so retries never execute twice. */
export const tasks = pgTable(
  "tasks",
  {
    id: uuid("id").defaultRandom().primaryKey(),
    requestId: text("request_id").notNull(),
    origin: text("origin").notNull(), // hud | phone:<deviceId>
    command: text("command").notNull(),
    engine: text("engine"), // REFLEX_ENGINE | ollama:<model> | openai:<model> | ...
    status: text("status").notNull(), // running | done | error | awaiting_approval | queued | denied
    result: jsonb("result").$type<Record<string, unknown>>(),
    createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
    finishedAt: timestamp("finished_at", { withTimezone: true }),
  },
  (t) => [uniqueIndex("tasks_request_uq").on(t.requestId)],
);

/** Jobs that must run on the Windows host (via the host agent). */
export const hostJobs = pgTable(
  "host_jobs",
  {
    id: uuid("id").defaultRandom().primaryKey(),
    taskId: uuid("task_id"),
    tool: text("tool").notNull(),
    args: jsonb("args").$type<Record<string, unknown>>().notNull(),
    risk: text("risk").notNull(), // low | medium | high
    summary: text("summary").notNull(),
    status: text("status").notNull(), // awaiting_approval | pending | claimed | done | error | denied | expired
    origin: text("origin").notNull(),
    result: jsonb("result").$type<Record<string, unknown>>(),
    createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
    claimedAt: timestamp("claimed_at", { withTimezone: true }),
    finishedAt: timestamp("finished_at", { withTimezone: true }),
  },
  (t) => [index("host_jobs_status_idx").on(t.status)],
);

/** Delivery queue for reminder notifications per channel (hud | phone | host). */
export const notifications = pgTable(
  "notifications",
  {
    id: serial("id").primaryKey(),
    reminderId: uuid("reminder_id"),
    channel: text("channel").notNull(),
    title: text("title").notNull(),
    body: text("body"),
    createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
    deliveredAt: timestamp("delivered_at", { withTimezone: true }),
  },
  (t) => [index("notifications_channel_idx").on(t.channel, t.deliveredAt)],
);

/** Audit trail (no secrets, no typed text, no screen content). */
export const auditLog = pgTable("audit_log", {
  id: serial("id").primaryKey(),
  at: timestamp("at", { withTimezone: true }).defaultNow().notNull(),
  actor: text("actor").notNull(),
  action: text("action").notNull(),
  detail: text("detail"),
  ok: boolean("ok").default(true).notNull(),
});
