/**
 * Remote-desktop relay hub (single gateway process, in-memory by design:
 * screen pixels and keystrokes are never persisted).
 *
 *  Windows host agent --(HTTPS POST JPEG frames)--> gateway --(GET capture / MJPEG)--> phone/HUD
 *  phone/HUD --(POST /api/remote/input)--> gateway --(long-poll /api/host/poll)--> host agent --> SendInput
 */

export interface InputEvent {
  id: number;
  action: string;
  params: Record<string, unknown>;
  at: number;
  origin: string;
}

export interface Frame {
  data: Buffer;
  seq: number;
  receivedAt: number;
  width: number;
  height: number;
  hostId: string;
  captureMs: number;
}

interface Hub {
  frame: Frame | null;
  frameSeq: number;
  frameTimes: number[];
  frameWaiters: Set<() => void>;
  inputs: InputEvent[];
  inputSeq: number;
  recentEventKeys: Map<string, number>;
  hostWaiters: Set<() => void>;
  viewers: Map<string, { lastAt: number; startedAt: number; origin: string }>;
  prefs: { scale: number; quality: number; fps: number };
  paused: boolean;
  killedAt: number;
  inputLatency: number[]; // ms from enqueue -> host pickup (server clock)
  frameAge: number[]; // ms frame age when served
  sessions: { origin: string; startedAt: number; endedAt?: number; inputs: number }[];
}

const g = globalThis as typeof globalThis & { __edithHub?: Hub };
export const hub: Hub =
  g.__edithHub ??
  (g.__edithHub = {
    frame: null,
    frameSeq: 0,
    frameTimes: [],
    frameWaiters: new Set(),
    inputs: [],
    inputSeq: 0,
    recentEventKeys: new Map(),
    hostWaiters: new Set(),
    viewers: new Map(),
    prefs: { scale: 1280, quality: 60, fps: 15 },
    paused: false,
    killedAt: 0,
    inputLatency: [],
    frameAge: [],
    sessions: [],
  });

const VIEWER_TTL = 4000;

function pushSample(arr: number[], v: number, max = 300) {
  arr.push(v);
  if (arr.length > max) arr.splice(0, arr.length - max);
}

export function percentile(arr: number[], p: number): number | null {
  if (!arr.length) return null;
  const s = [...arr].sort((a, b) => a - b);
  return Math.round(s[Math.min(s.length - 1, Math.floor((p / 100) * s.length))]);
}

export function wakeHost() {
  for (const w of hub.hostWaiters) w();
  hub.hostWaiters.clear();
}

/** Register a viewer heartbeat; returns true if this begins a new session. */
export function touchViewer(key: string, origin: string, prefs?: Partial<Hub["prefs"]>): boolean {
  const now = Date.now();
  const existing = hub.viewers.get(key);
  let isNew = false;
  if (!existing || now - existing.lastAt > VIEWER_TTL * 3) {
    hub.viewers.set(key, { lastAt: now, startedAt: now, origin });
    hub.sessions.unshift({ origin, startedAt: now, inputs: 0 });
    if (hub.sessions.length > 50) hub.sessions.length = 50;
    isNew = true;
    wakeHost();
  } else existing.lastAt = now;
  if (prefs) {
    if (prefs.scale) hub.prefs.scale = Math.max(480, Math.min(1920, Math.round(prefs.scale)));
    if (prefs.quality) hub.prefs.quality = Math.max(20, Math.min(90, Math.round(prefs.quality)));
    if (prefs.fps) hub.prefs.fps = Math.max(1, Math.min(30, Math.round(prefs.fps)));
  }
  return isNew;
}

export function activeViewers() {
  const now = Date.now();
  const out: { key: string; origin: string; startedAt: number }[] = [];
  for (const [k, v] of hub.viewers) {
    if (now - v.lastAt <= VIEWER_TTL) out.push({ key: k, origin: v.origin, startedAt: v.startedAt });
    else if (now - v.lastAt > 60_000) {
      hub.viewers.delete(k);
      const s = hub.sessions.find((x) => x.origin === v.origin && !x.endedAt);
      if (s) s.endedAt = v.lastAt;
    }
  }
  return out;
}

export function streamWanted(): boolean {
  return !hub.paused && activeViewers().length > 0;
}

export function putFrame(data: Buffer, hostId: string, width: number, height: number, captureMs: number) {
  const now = Date.now();
  hub.frameSeq += 1;
  hub.frame = { data, seq: hub.frameSeq, receivedAt: now, width, height, hostId, captureMs };
  hub.frameTimes.push(now);
  while (hub.frameTimes.length && now - hub.frameTimes[0] > 5000) hub.frameTimes.shift();
  for (const w of hub.frameWaiters) w();
  hub.frameWaiters.clear();
}

export function measuredFps(): number {
  const now = Date.now();
  const recent = hub.frameTimes.filter((t) => now - t <= 3000);
  return Math.round((recent.length / 3) * 10) / 10;
}

/** Wait for a frame newer than `afterSeq` (or timeout). */
export function waitFrame(afterSeq: number, timeoutMs: number): Promise<Frame | null> {
  if (hub.frame && hub.frame.seq > afterSeq) return Promise.resolve(hub.frame);
  return new Promise((resolve) => {
    const done = () => {
      clearTimeout(timer);
      hub.frameWaiters.delete(done);
      resolve(hub.frame && hub.frame.seq > afterSeq ? hub.frame : null);
    };
    const timer = setTimeout(done, timeoutMs);
    hub.frameWaiters.add(done);
  });
}

export function noteFrameServed(f: Frame) {
  pushSample(hub.frameAge, Date.now() - f.receivedAt);
}

/** Queue an input event. `eventKey` (client-supplied) makes retries idempotent. */
export function enqueueInput(action: string, params: Record<string, unknown>, origin: string, eventKey?: string): { queued: boolean; duplicate: boolean } {
  const now = Date.now();
  if (eventKey) {
    if (hub.recentEventKeys.has(eventKey)) return { queued: false, duplicate: true };
    hub.recentEventKeys.set(eventKey, now);
    if (hub.recentEventKeys.size > 2000) {
      for (const [k, t] of hub.recentEventKeys) if (now - t > 120_000) hub.recentEventKeys.delete(k);
    }
  }
  // Coalesce consecutive pointer moves to keep latency low on slow links.
  const last = hub.inputs[hub.inputs.length - 1];
  if ((action === "mouse_move" || action === "move") && last && (last.action === "mouse_move" || last.action === "move")) {
    last.params = params;
    last.at = now;
  } else {
    hub.inputSeq += 1;
    hub.inputs.push({ id: hub.inputSeq, action, params, at: now, origin });
    if (hub.inputs.length > 500) hub.inputs.splice(0, hub.inputs.length - 500);
  }
  const s = hub.sessions.find((x) => x.origin === origin && !x.endedAt);
  if (s) s.inputs += 1;
  wakeHost();
  return { queued: true, duplicate: false };
}

export function drainInputs(): InputEvent[] {
  if (!hub.inputs.length) return [];
  const now = Date.now();
  const out = hub.inputs.splice(0, hub.inputs.length).filter((e) => now - e.at < 5000); // drop stale input
  for (const e of out) pushSample(hub.inputLatency, now - e.at);
  return out;
}

export function waitHost(timeoutMs: number): Promise<void> {
  return new Promise((resolve) => {
    const done = () => {
      clearTimeout(timer);
      hub.hostWaiters.delete(done);
      resolve();
    };
    const timer = setTimeout(done, timeoutMs);
    hub.hostWaiters.add(done);
  });
}

/** Local/remote kill switch: drop viewers, clear inputs, pause the stream. */
export function killSessions() {
  hub.viewers.clear();
  hub.inputs.length = 0;
  hub.frame = null;
  hub.killedAt = Date.now();
  for (const s of hub.sessions) if (!s.endedAt) s.endedAt = Date.now();
  wakeHost();
}

export function relayStats() {
  return {
    has_frame: Boolean(hub.frame),
    frame_age_ms: hub.frame ? Date.now() - hub.frame.receivedAt : null,
    width: hub.frame?.width ?? null,
    height: hub.frame?.height ?? null,
    last_frame_bytes: hub.frame?.data.length ?? null,
    capture_encode_ms: hub.frame?.captureMs ?? null,
    measured_fps: measuredFps(),
    est_kbps: hub.frame ? Math.round((measuredFps() * hub.frame.data.length * 8) / 1000) : null,
    input_relay_ms_p50: percentile(hub.inputLatency, 50),
    input_relay_ms_p95: percentile(hub.inputLatency, 95),
    frame_age_ms_p50: percentile(hub.frameAge, 50),
    frame_age_ms_p95: percentile(hub.frameAge, 95),
    samples: { input: hub.inputLatency.length, frames: hub.frameAge.length },
    prefs: hub.prefs,
    paused: hub.paused,
    viewers: activeViewers(),
    sessions: hub.sessions.slice(0, 15),
  };
}
