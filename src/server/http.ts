import { NextRequest } from "next/server";

export const CORS_HEADERS: Record<string, string> = {
  // "*" without credentials: browsers never attach the owner cookie cross-origin,
  // so only bearer/device-token calls (phone APK / PWA) work cross-origin.
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
  "Access-Control-Allow-Headers":
    "Content-Type, Authorization, X-Token, X-Host-Token, X-Request-Id, Bypass-Tunnel-Reminder",
  "Access-Control-Max-Age": "600",
};

export function json(data: unknown, status = 200, extra?: Record<string, string>): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
      ...CORS_HEADERS,
      ...(extra ?? {}),
    },
  });
}

export function err(status: number, error: string, extra?: Record<string, unknown>): Response {
  return json({ ok: false, error, ...(extra ?? {}) }, status);
}

export async function readJson(req: NextRequest): Promise<Record<string, unknown>> {
  const ct = req.headers.get("content-type") || "";
  if (!ct.includes("application/json") && !ct.includes("text/plain")) {
    // still try: many legacy clients omit content-type
  }
  try {
    const text = await req.text();
    if (!text) return {};
    const parsed = JSON.parse(text);
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
  } catch {
    return {};
  }
}

export function clientIp(req: NextRequest): string {
  const xf = req.headers.get("x-forwarded-for");
  if (xf) return xf.split(",")[0].trim();
  return req.headers.get("x-real-ip") || "unknown";
}

export function str(v: unknown, max = 2000): string {
  if (typeof v !== "string") return "";
  return v.slice(0, max);
}

export function num(v: unknown, fallback: number, min?: number, max?: number): number {
  const n = typeof v === "number" ? v : typeof v === "string" ? Number(v) : NaN;
  if (!Number.isFinite(n)) return fallback;
  let out = n;
  if (min !== undefined) out = Math.max(min, out);
  if (max !== undefined) out = Math.min(max, out);
  return out;
}

/** Simple in-memory fixed-window rate limiter (per process). */
const buckets = new Map<string, { count: number; resetAt: number }>();
export function rateLimit(key: string, limit: number, windowMs: number): boolean {
  const now = Date.now();
  const b = buckets.get(key);
  if (!b || b.resetAt < now) {
    buckets.set(key, { count: 1, resetAt: now + windowMs });
    return true;
  }
  b.count += 1;
  if (buckets.size > 5000) {
    for (const [k, v] of buckets) if (v.resetAt < now) buckets.delete(k);
  }
  return b.count <= limit;
}

/** Redact anything that looks like a secret before logging. */
export function redact(s: string): string {
  return s
    .replace(/(token|key|secret|password|passphrase)["'=:\s]+[^\s"',}]+/gi, "$1=[REDACTED]")
    .replace(/\b(sk|gsk|AIza)[A-Za-z0-9_\-]{10,}\b/g, "[REDACTED]");
}
