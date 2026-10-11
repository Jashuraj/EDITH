import { createHash, randomBytes, scryptSync, timingSafeEqual, randomInt } from "node:crypto";
import { NextRequest } from "next/server";
import { and, eq, gt, isNull, sql } from "drizzle-orm";
import { db } from "@/db";
import { devices, hosts, ownerSessions, pairingCodes, auditLog } from "@/db/schema";
import { getSetting, setSetting } from "./settings";
import { clientIp, redact } from "./http";

export const OWNER_COOKIE = "edith_owner";
const SESSION_DAYS = 14;

export const sha256 = (s: string) => createHash("sha256").update(s).digest("hex");
export const newToken = (bytes = 32) => randomBytes(bytes).toString("base64url");

export function hashPassphrase(pass: string): string {
  const salt = randomBytes(16).toString("hex");
  const hash = scryptSync(pass, salt, 64).toString("hex");
  return `scrypt$${salt}$${hash}`;
}

export function verifyPassphrase(pass: string, stored: string): boolean {
  const [alg, salt, hash] = stored.split("$");
  if (alg !== "scrypt" || !salt || !hash) return false;
  const test = scryptSync(pass, salt, 64);
  const ref = Buffer.from(hash, "hex");
  return ref.length === test.length && timingSafeEqual(ref, test);
}

export async function ownerConfigured(): Promise<boolean> {
  return Boolean(await getSetting<string>("owner_pass_hash"));
}

export async function setOwnerPassphrase(pass: string) {
  await setSetting("owner_pass_hash", hashPassphrase(pass));
}

export async function createOwnerSession(req: NextRequest): Promise<string> {
  const token = newToken();
  await db.insert(ownerSessions).values({
    tokenHash: sha256(token),
    userAgent: (req.headers.get("user-agent") || "").slice(0, 200),
    expiresAt: new Date(Date.now() + SESSION_DAYS * 86400_000),
  });
  return token;
}

export function sessionCookie(token: string, maxAgeSec = SESSION_DAYS * 86400): string {
  // `Secure` would break plain-http LAN access, so it is opt-in (set it when served over HTTPS).
  const secure = process.env.EDITH_SECURE_COOKIE === "1" ? "; Secure" : "";
  return `${OWNER_COOKIE}=${token}; Path=/; HttpOnly; SameSite=Strict; Max-Age=${maxAgeSec}${secure}`;
}

function readCookie(req: NextRequest, name: string): string | null {
  return req.cookies.get(name)?.value ?? null;
}

export async function isOwner(req: NextRequest): Promise<boolean> {
  const token = readCookie(req, OWNER_COOKIE);
  if (!token) return false;
  const rows = await db
    .select({ id: ownerSessions.id })
    .from(ownerSessions)
    .where(and(eq(ownerSessions.tokenHash, sha256(token)), gt(ownerSessions.expiresAt, new Date())))
    .limit(1);
  return rows.length > 0;
}

export async function destroyOwnerSession(req: NextRequest) {
  const token = readCookie(req, OWNER_COOKIE);
  if (token) await db.delete(ownerSessions).where(eq(ownerSessions.tokenHash, sha256(token)));
}

export type DeviceRow = typeof devices.$inferSelect;
export type HostRow = typeof hosts.$inferSelect;

export function extractToken(req: NextRequest, body?: Record<string, unknown>): string {
  const auth = req.headers.get("authorization");
  if (auth?.toLowerCase().startsWith("bearer ")) return auth.slice(7).trim();
  const x = req.headers.get("x-token");
  if (x) return x.trim();
  if (body && typeof body.token === "string") return body.token.trim();
  const q = req.nextUrl.searchParams.get("token");
  return q ? q.trim() : "";
}

const deviceSeenCache = new Map<string, number>();

export async function deviceFromToken(token: string, req?: NextRequest): Promise<DeviceRow | null> {
  if (!token || token.length < 20) return null;
  const rows = await db
    .select()
    .from(devices)
    .where(and(eq(devices.tokenHash, sha256(token)), isNull(devices.revokedAt)))
    .limit(1);
  const d = rows[0] ?? null;
  if (d) {
    const last = deviceSeenCache.get(d.id) ?? 0;
    if (Date.now() - last > 10_000) {
      deviceSeenCache.set(d.id, Date.now());
      await db
        .update(devices)
        .set({ lastSeenAt: new Date(), lastIp: req ? clientIp(req) : d.lastIp })
        .where(eq(devices.id, d.id));
    }
  }
  return d;
}

export async function hostFromRequest(req: NextRequest): Promise<HostRow | null> {
  const t = req.headers.get("x-host-token") || "";
  if (t.length < 20) return null;
  const rows = await db
    .select()
    .from(hosts)
    .where(and(eq(hosts.tokenHash, sha256(t)), isNull(hosts.revokedAt)))
    .limit(1);
  return rows[0] ?? null;
}

export type Principal =
  | { kind: "owner"; label: "owner" }
  | { kind: "device"; label: string; device: DeviceRow }
  | { kind: "none"; label: "anonymous" };

export async function principal(req: NextRequest, body?: Record<string, unknown>): Promise<Principal> {
  if (await isOwner(req)) return { kind: "owner", label: "owner" };
  const d = await deviceFromToken(extractToken(req, body), req);
  if (d) return { kind: "device", label: `phone:${d.name}`, device: d };
  return { kind: "none", label: "anonymous" };
}

export function hasScope(p: Principal, scope: string): boolean {
  if (p.kind === "owner") return true;
  if (p.kind === "device") return p.device.scopes.includes(scope);
  return false;
}

/** Generate a 6-digit one-time code valid for `ttlMin` minutes. Only its hash is stored. */
export async function createPairingCode(kind: "device" | "host", scopes: string[], label: string, ttlMin = 5) {
  const code = String(randomInt(0, 1_000_000)).padStart(6, "0");
  const expiresAt = new Date(Date.now() + ttlMin * 60_000);
  await db.insert(pairingCodes).values({ codeHash: sha256(`${kind}:${code}`), kind, scopes, label, expiresAt });
  return { code, expiresAt };
}

/** Atomically consume a pairing code. Returns the row or null (expired/used/invalid). */
export async function consumePairingCode(kind: "device" | "host", code: string) {
  const clean = code.replace(/\D/g, "");
  if (clean.length !== 6) return null;
  const rows = await db
    .update(pairingCodes)
    .set({ usedAt: new Date() })
    .where(
      and(
        eq(pairingCodes.codeHash, sha256(`${kind}:${clean}`)),
        isNull(pairingCodes.usedAt),
        gt(pairingCodes.expiresAt, new Date()),
      ),
    )
    .returning();
  return rows[0] ?? null;
}

export async function audit(actor: string, action: string, detail?: string, ok = true) {
  try {
    await db.insert(auditLog).values({ actor, action, detail: detail ? redact(detail).slice(0, 500) : null, ok });
    // Retention: keep the most recent 5000 rows.
    if (Math.random() < 0.02) {
      await db.execute(sql`delete from audit_log where id < (select coalesce(max(id),0) - 5000 from audit_log)`);
    }
  } catch {
    /* never let audit failures break requests */
  }
}
