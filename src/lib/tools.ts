/** Tool registry: typed validation, risk class, where it runs. Pure (no I/O). */

export type Risk = "low" | "medium" | "high";
export type Permission = "auto" | "ask" | "deny";

export interface ToolDef {
  name: string;
  description: string;
  risk: Risk;
  runsOn: "host" | "gateway";
  supported: boolean;
  unsupportedReason?: string;
  validate: (args: Record<string, unknown>) => { ok: true; args: Record<string, unknown>; summary: string } | { ok: false; error: string };
}

const APPS = [
  "chrome", "edge", "firefox", "notepad", "calculator", "explorer", "taskmgr", "settings", "terminal", "powershell",
  "cmd", "vscode", "spotify", "word", "excel", "powerpoint", "paint", "snippingtool", "camera", "whatsapp",
  "telegram", "discord", "vlc", "outlook", "teams",
];
const FOLDERS = ["downloads", "documents", "desktop", "pictures", "music", "videos", "home"];
const MEDIA = ["play_pause", "next", "prev", "mute", "vol_up", "vol_down"];

export const TOOLS: Record<string, ToolDef> = {
  open_app: {
    name: "open_app", description: "Launch an approved desktop application", risk: "low", runsOn: "host", supported: true,
    validate: (a) => {
      const app = String(a.app ?? "").toLowerCase().trim();
      if (!APPS.includes(app)) return { ok: false, error: `“${app || "?"}” is not on the approved app list (${APPS.slice(0, 8).join(", ")}, …). Add it to the host agent allowlist to enable it.` };
      return { ok: true, args: { app }, summary: `Open ${app}` };
    },
  },
  open_url: {
    name: "open_url", description: "Open an http(s) URL in the default browser", risk: "low", runsOn: "host", supported: true,
    validate: (a) => {
      const url = String(a.url ?? "");
      try {
        const u = new URL(url);
        if (u.protocol !== "https:" && u.protocol !== "http:") return { ok: false, error: "Only http/https URLs are allowed." };
        return { ok: true, args: { url: u.toString() }, summary: `Open ${u.hostname}` };
      } catch {
        return { ok: false, error: "Invalid URL." };
      }
    },
  },
  open_folder: {
    name: "open_folder", description: "Open a known user folder in Explorer", risk: "low", runsOn: "host", supported: true,
    validate: (a) => {
      const folder = String(a.folder ?? "").toLowerCase();
      if (!FOLDERS.includes(folder)) return { ok: false, error: `Folder must be one of ${FOLDERS.join(", ")}.` };
      return { ok: true, args: { folder }, summary: `Open ${folder} folder` };
    },
  },
  media_control: {
    name: "media_control", description: "Media keys: play/pause, next, previous, mute, volume", risk: "low", runsOn: "host", supported: true,
    validate: (a) => {
      const action = String(a.action ?? "");
      if (!MEDIA.includes(action)) return { ok: false, error: "Unknown media action." };
      return { ok: true, args: { action }, summary: `Media: ${action.replace("_", " ")}` };
    },
  },
  set_volume: {
    name: "set_volume", description: "Set master volume (0-100)", risk: "low", runsOn: "host", supported: true,
    validate: (a) => {
      const level = Number(a.level);
      if (!Number.isFinite(level) || level < 0 || level > 100) return { ok: false, error: "Volume must be 0-100." };
      return { ok: true, args: { level: Math.round(level) }, summary: `Set volume to ${Math.round(level)}%` };
    },
  },
  system_status: {
    name: "system_status", description: "Refresh battery/CPU/RAM/disk metrics", risk: "low", runsOn: "host", supported: true,
    validate: () => ({ ok: true, args: {}, summary: "Read system status" }),
  },
  notify: {
    name: "notify", description: "Show a Windows notification", risk: "low", runsOn: "host", supported: true,
    validate: (a) => ({ ok: true, args: { title: String(a.title ?? "EDITH").slice(0, 80), body: String(a.body ?? "").slice(0, 300) }, summary: "Show notification" }),
  },
  lock_pc: {
    name: "lock_pc", description: "Lock the Windows workstation", risk: "medium", runsOn: "host", supported: true,
    validate: () => ({ ok: true, args: {}, summary: "Lock the PC" }),
  },
  type_text: {
    name: "type_text", description: "Type text into the focused window", risk: "medium", runsOn: "host", supported: true,
    validate: (a) => {
      const text = String(a.text ?? "");
      if (!text || text.length > 500) return { ok: false, error: "Text must be 1-500 characters." };
      return { ok: true, args: { text }, summary: `Type ${text.length} characters into the focused window` };
    },
  },
  sleep_pc: {
    name: "sleep_pc", description: "Put the PC to sleep (it will be unreachable until woken)", risk: "high", runsOn: "host", supported: true,
    validate: () => ({ ok: true, args: {}, summary: "Put the PC to sleep — remote access will stop until it wakes" }),
  },
  shutdown_pc: {
    name: "shutdown_pc", description: "Shut down the PC", risk: "high", runsOn: "host", supported: true,
    validate: () => ({ ok: true, args: {}, summary: "Shut down the PC — it cannot be reached remotely afterwards" }),
  },
  restart_pc: {
    name: "restart_pc", description: "Restart the PC", risk: "high", runsOn: "host", supported: true,
    validate: () => ({ ok: true, args: {}, summary: "Restart the PC" }),
  },
  unlock_pc: {
    name: "unlock_pc", description: "Unlock Windows", risk: "high", runsOn: "host", supported: false,
    unsupportedReason: "Windows does not allow programs to unlock the secure sign-in screen. Sign in on the PC, or use the remote view and type your PIN yourself.",
    validate: () => ({ ok: false, error: "Unsupported" }),
  },
};

export const DEFAULT_PERMISSION: Record<Risk, Permission> = { low: "auto", medium: "ask", high: "ask" };

export function permissionFor(tool: ToolDef, overrides: Record<string, Permission> | undefined): Permission {
  const o = overrides?.[tool.name];
  if (o === "auto" || o === "ask" || o === "deny") {
    // High-risk tools can never be set to auto-run.
    if (tool.risk === "high" && o === "auto") return "ask";
    return o;
  }
  return DEFAULT_PERMISSION[tool.risk];
}

/** Extract a model-proposed tool call: {"tool":"name","args":{...}} anywhere in the output. */
export function extractToolCall(text: string): { tool: string; args: Record<string, unknown> } | null {
  const m = text.match(/\{[^{}]*"tool"\s*:\s*"([a-z_]+)"[^{}]*(\{[^{}]*\})?[^{}]*\}/);
  if (!m) return null;
  try {
    const obj = JSON.parse(m[0]);
    if (typeof obj.tool === "string" && TOOLS[obj.tool]) {
      return { tool: obj.tool, args: obj.args && typeof obj.args === "object" ? obj.args : {} };
    }
  } catch {
    /* ignore */
  }
  return null;
}
