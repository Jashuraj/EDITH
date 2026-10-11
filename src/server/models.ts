import { createCipheriv, createDecipheriv, createHash, randomBytes } from "node:crypto";
import { getMode, getProfile, getSetting, setSetting, type Mode } from "./settings";

export type ProviderId = "local" | "gemini" | "openai" | "groq" | "openrouter" | "gateway";
export const CLOUD: ProviderId[] = ["gemini", "openai", "groq", "openrouter", "gateway"];

interface ProviderPrefs {
  active_provider: ProviderId;
  models: Partial<Record<ProviderId, string>>;
  gateway_url?: string;
  keys_enc?: Partial<Record<ProviderId, string>>;
}

const DEFAULT_MODELS: Record<ProviderId, string> = {
  local: "hermes3:3b",
  gemini: "gemini-2.0-flash",
  openai: "gpt-4o-mini",
  groq: "llama-3.3-70b-versatile",
  openrouter: "openrouter/auto",
  gateway: "auto",
};

const ENV_KEYS: Record<ProviderId, string | null> = {
  local: null,
  gemini: "GEMINI_API_KEY",
  openai: "OPENAI_API_KEY",
  groq: "GROQ_API_KEY",
  openrouter: "OPENROUTER_API_KEY",
  gateway: "OMNIROUTE_API_KEY",
};

const BASE_URLS: Partial<Record<ProviderId, string>> = {
  openai: process.env.OPENAI_BASE_URL || "https://api.openai.com/v1",
  groq: "https://api.groq.com/openai/v1",
  openrouter: "https://openrouter.ai/api/v1",
};

export const ollamaUrl = () => (process.env.OLLAMA_URL || "http://127.0.0.1:11434").replace(/\/+$/, "");

export async function getPrefs(): Promise<ProviderPrefs> {
  const p = await getSetting<ProviderPrefs>("providers");
  return { active_provider: "local", models: {}, ...(p ?? {}) };
}

function secretKey(): Buffer | null {
  const s = process.env.EDITH_SECRET_KEY;
  if (!s || s.length < 16) return null;
  return createHash("sha256").update(s).digest();
}

export function canStoreKeys() {
  return secretKey() !== null;
}

function encrypt(plain: string): string {
  const key = secretKey();
  if (!key) throw new Error("EDITH_SECRET_KEY is not set");
  const iv = randomBytes(12);
  const c = createCipheriv("aes-256-gcm", key, iv);
  const enc = Buffer.concat([c.update(plain, "utf8"), c.final()]);
  return `${iv.toString("base64")}.${c.getAuthTag().toString("base64")}.${enc.toString("base64")}`;
}

function decrypt(blob: string): string | null {
  const key = secretKey();
  if (!key) return null;
  try {
    const [iv, tag, data] = blob.split(".");
    const d = createDecipheriv("aes-256-gcm", key, Buffer.from(iv, "base64"));
    d.setAuthTag(Buffer.from(tag, "base64"));
    return Buffer.concat([d.update(Buffer.from(data, "base64")), d.final()]).toString("utf8");
  } catch {
    return null;
  }
}

export async function apiKeyFor(p: ProviderId, prefs?: ProviderPrefs): Promise<string | null> {
  const envName = ENV_KEYS[p];
  if (envName && process.env[envName]) return process.env[envName] as string;
  const pr = prefs ?? (await getPrefs());
  const enc = pr.keys_enc?.[p];
  return enc ? decrypt(enc) : null;
}

export async function savePrefs(input: { provider?: string; api_key?: string; model?: string; base_url?: string }) {
  const prefs = await getPrefs();
  const p = (input.provider || prefs.active_provider) as ProviderId;
  if (!(p in DEFAULT_MODELS)) throw new Error("Unknown provider");
  prefs.active_provider = p;
  if (input.model) prefs.models[p] = input.model.slice(0, 120);
  if (p === "gateway" && input.base_url) prefs.gateway_url = input.base_url.slice(0, 300);
  if (input.api_key) {
    if (!canStoreKeys()) throw new Error("To store API keys, set EDITH_SECRET_KEY (16+ chars) in .env, or put the key in .env directly (e.g. GEMINI_API_KEY).");
    prefs.keys_enc = { ...(prefs.keys_enc ?? {}), [p]: encrypt(input.api_key.trim()) };
  }
  await setSetting("providers", prefs);
  return prefs;
}

/* ---------- connectivity ---------- */
let probeCache: { at: number; online: boolean; ms: number | null } | null = null;
export async function probeInternet(force = false): Promise<{ online: boolean; ms: number | null }> {
  if (!force && probeCache && Date.now() - probeCache.at < 20_000) return probeCache;
  const t0 = Date.now();
  let online = false;
  try {
    const r = await fetch("https://www.gstatic.com/generate_204", { signal: AbortSignal.timeout(2500), cache: "no-store" });
    online = r.status === 204 || r.ok;
  } catch {
    online = false;
  }
  probeCache = { at: Date.now(), online, ms: online ? Date.now() - t0 : null };
  return probeCache;
}

/* ---------- Ollama ---------- */
let ollamaCache: { at: number; up: boolean; models: { name: string; size: number }[]; error?: string } | null = null;
export async function ollamaStatus(force = false) {
  if (!force && ollamaCache && Date.now() - ollamaCache.at < 10_000) return ollamaCache;
  try {
    const r = await fetch(`${ollamaUrl()}/api/tags`, { signal: AbortSignal.timeout(1500), cache: "no-store" });
    const j = (await r.json()) as { models?: { name: string; size: number }[] };
    ollamaCache = { at: Date.now(), up: true, models: (j.models ?? []).map((m) => ({ name: m.name, size: m.size })) };
  } catch (e) {
    ollamaCache = { at: Date.now(), up: false, models: [], error: `Ollama not reachable at ${ollamaUrl()} (${(e as Error).name})` };
  }
  return ollamaCache;
}

export async function activeLocalModel(): Promise<string> {
  const prefs = await getPrefs();
  return prefs.models.local || process.env.OLLAMA_MODEL || DEFAULT_MODELS.local;
}

const SYSTEM_PROMPT = `You are EDITH, a concise, helpful personal assistant running on the owner's Windows PC.
Answer briefly (max ~120 words) unless asked for detail. You cannot execute actions yourself.
If the user clearly wants a PC action, reply ONLY with JSON: {"tool":"<name>","args":{...}} using one of:
open_app{app}, open_url{url}, open_folder{folder}, media_control{action: play_pause|next|prev|mute|vol_up|vol_down},
set_volume{level}, lock_pc{}, system_status{}. The app will validate and may ask the user to approve.
Never invent results of actions. Never give medical dosage advice.`;

export interface ChatResult {
  ok: boolean;
  text: string;
  engine: string;
  attempts: { engine: string; ok: boolean; ms: number; error?: string }[];
  mode: Mode;
}

async function callOllama(prompt: string, model: string, signal: AbortSignal): Promise<string> {
  const profile = await getProfile();
  const keepAlive = (await getSetting<string>("ollama_keep_alive")) || "5m";
  const r = await fetch(`${ollamaUrl()}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    signal,
    body: JSON.stringify({
      model,
      stream: false,
      keep_alive: keepAlive,
      options: { num_ctx: profile.resourceProfile === "4gb" ? 1024 : 2048, num_thread: profile.resourceProfile === "4gb" ? 2 : 4 },
      messages: [
        { role: "system", content: SYSTEM_PROMPT },
        { role: "user", content: prompt },
      ],
    }),
  });
  if (!r.ok) throw new Error(`Ollama HTTP ${r.status}: ${(await r.text()).slice(0, 160)}`);
  const j = (await r.json()) as { message?: { content?: string } };
  return j.message?.content?.trim() || "";
}

async function callOpenAICompat(base: string, key: string | null, model: string, prompt: string, signal: AbortSignal): Promise<string> {
  const r = await fetch(`${base.replace(/\/+$/, "")}/chat/completions`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(key ? { Authorization: `Bearer ${key}` } : {}) },
    signal,
    body: JSON.stringify({
      model,
      max_tokens: 400,
      temperature: 0.4,
      messages: [
        { role: "system", content: SYSTEM_PROMPT },
        { role: "user", content: prompt },
      ],
    }),
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}: ${(await r.text()).slice(0, 160)}`);
  const j = (await r.json()) as { choices?: { message?: { content?: string } }[] };
  return j.choices?.[0]?.message?.content?.trim() || "";
}

async function callGemini(key: string, model: string, prompt: string, signal: AbortSignal): Promise<string> {
  const r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "x-goog-api-key": key },
    signal,
    body: JSON.stringify({
      systemInstruction: { parts: [{ text: SYSTEM_PROMPT }] },
      contents: [{ role: "user", parts: [{ text: prompt }] }],
      generationConfig: { maxOutputTokens: 400, temperature: 0.4 },
    }),
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}: ${(await r.text()).slice(0, 160)}`);
  const j = (await r.json()) as { candidates?: { content?: { parts?: { text?: string }[] } }[] };
  return j.candidates?.[0]?.content?.parts?.map((p) => p.text ?? "").join("").trim() || "";
}

export async function callProvider(p: ProviderId, prompt: string, opts: { model?: string; key?: string; base?: string; timeoutMs?: number } = {}) {
  const prefs = await getPrefs();
  const model = opts.model || prefs.models[p] || (p === "local" ? await activeLocalModel() : DEFAULT_MODELS[p]);
  const signal = AbortSignal.timeout(opts.timeoutMs ?? (p === "local" ? 90_000 : 25_000));
  if (p === "local") return { text: await callOllama(prompt, model, signal), model };
  const key = opts.key || (await apiKeyFor(p, prefs));
  if (p === "gemini") {
    if (!key) throw new Error("No Gemini API key configured");
    return { text: await callGemini(key, model, prompt, signal), model };
  }
  if (p === "gateway") {
    const base = opts.base || prefs.gateway_url || process.env.OMNIROUTE_URL;
    if (!base) throw new Error("No gateway/OmniRoute URL configured");
    return { text: await callOpenAICompat(base, key, model, prompt, signal), model };
  }
  if (!key) throw new Error(`No ${p} API key configured`);
  return { text: await callOpenAICompat(opts.base || BASE_URLS[p]!, key, model, prompt, signal), model };
}

export async function cloudConfigured(p: ProviderId, prefs?: ProviderPrefs): Promise<boolean> {
  const pr = prefs ?? (await getPrefs());
  if (p === "gateway") return Boolean(pr.gateway_url || process.env.OMNIROUTE_URL);
  return Boolean(await apiKeyFor(p, pr));
}

/** Route a free-form prompt according to Auto / Online / Offline policy. */
export async function routeChat(prompt: string): Promise<ChatResult> {
  const mode = await getMode();
  const prefs = await getPrefs();
  const attempts: ChatResult["attempts"] = [];
  const chain: ProviderId[] = [];

  if (mode !== "offline") {
    const net = await probeInternet();
    if (net.online) {
      const ordered = [prefs.active_provider, ...CLOUD.filter((c) => c !== prefs.active_provider)].filter((c) => c !== "local");
      for (const c of ordered) if (await cloudConfigured(c, prefs)) chain.push(c);
    } else {
      attempts.push({ engine: "internet", ok: false, ms: 0, error: "Internet unreachable" });
    }
  }
  // Local model: always allowed in offline/auto; in online mode only as last-resort fallback.
  chain.push("local");
  if (mode === "auto" && prefs.active_provider === "local") {
    chain.splice(chain.indexOf("local"), 1);
    chain.unshift("local");
  }

  for (const p of chain) {
    if (p === "local") {
      const st = await ollamaStatus();
      if (!st.up) {
        attempts.push({ engine: "ollama", ok: false, ms: 0, error: st.error });
        continue;
      }
    }
    const t0 = Date.now();
    try {
      const { text, model } = await callProvider(p, prompt);
      if (!text) throw new Error("Empty response");
      const engine = `${p === "local" ? "ollama" : p}:${model}`;
      attempts.push({ engine, ok: true, ms: Date.now() - t0 });
      return { ok: true, text, engine, attempts, mode };
    } catch (e) {
      attempts.push({ engine: p, ok: false, ms: Date.now() - t0, error: (e as Error).message.slice(0, 200) });
    }
  }
  return {
    ok: false,
    text:
      mode === "offline"
        ? "Offline mode: no local model is available (is Ollama running?). Deterministic commands — reminders, timers, opening apps, status — still work."
        : "No AI engine is reachable right now (no configured online provider responded and Ollama is unavailable). Deterministic commands still work.",
    engine: "none",
    attempts,
    mode,
  };
}

export function providerSummary() {
  return { defaults: DEFAULT_MODELS };
}
