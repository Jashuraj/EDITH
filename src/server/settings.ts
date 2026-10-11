import { eq } from "drizzle-orm";
import { db } from "@/db";
import { settings } from "@/db/schema";

const cache = new Map<string, { v: unknown; at: number }>();
const TTL = 3000;

export async function getSetting<T>(key: string, fallback?: T): Promise<T | undefined> {
  const c = cache.get(key);
  if (c && Date.now() - c.at < TTL) return (c.v as T) ?? fallback;
  const rows = await db.select().from(settings).where(eq(settings.key, key)).limit(1);
  const v = rows[0]?.value as T | undefined;
  cache.set(key, { v, at: Date.now() });
  return v ?? fallback;
}

export async function setSetting(key: string, value: unknown) {
  await db
    .insert(settings)
    .values({ key, value: value as object, updatedAt: new Date() })
    .onConflictDoUpdate({ target: settings.key, set: { value: value as object, updatedAt: new Date() } });
  cache.set(key, { v: value, at: Date.now() });
}

export type Mode = "auto" | "online" | "offline";

export interface Profile {
  name: string;
  country: string;
  state: string;
  city: string;
  timezone: string;
  language: string;
  resourceProfile: "4gb" | "8gb";
  holidayCategories: string[]; // gazetted | national | restricted
  quietStart: string | null; // HH:MM
  quietEnd: string | null;
}

export const DEFAULT_PROFILE: Profile = {
  name: "",
  country: "IN",
  state: "",
  city: "",
  timezone: "Asia/Kolkata",
  language: "en-IN",
  resourceProfile: "8gb",
  holidayCategories: ["national", "gazetted"],
  quietStart: null,
  quietEnd: null,
};

export async function getProfile(): Promise<Profile> {
  const p = await getSetting<Partial<Profile>>("profile");
  return { ...DEFAULT_PROFILE, ...(p ?? {}) };
}

export async function getMode(): Promise<Mode> {
  const m = await getSetting<string>("mode");
  return m === "online" || m === "offline" ? m : "auto";
}
