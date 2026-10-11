/**
 * Indian holiday data.
 * - National holidays (fixed dates) are definitive and recur every year.
 * - Gazetted holidays are year-specific. Source: Government of India, DoPT O.M.
 *   F.No.12/2/2023-JCA dated 03-07-2025 (holidays for Central Government offices, Delhi/New Delhi, 2026).
 *   Dates marked `tentative` depend on moon sighting and may shift by a day; state governments
 *   publish their own lists. Users can add overrides as custom holiday events.
 */
export interface Holiday {
  date: string; // YYYY-MM-DD
  name: string;
  category: "national" | "gazetted";
  tentative?: boolean;
  source: string;
}

export const HOLIDAY_SOURCE = "DoPT O.M. F.No.12/2/2023-JCA (03 Jul 2025), Central Govt offices, Delhi";
export const HOLIDAY_DATA_UPDATED = "2026-01 (verified against published DoPT list)";

const NATIONAL: { md: string; name: string }[] = [
  { md: "01-26", name: "Republic Day" },
  { md: "08-15", name: "Independence Day" },
  { md: "10-02", name: "Mahatma Gandhi Jayanti" },
];

const GAZETTED: Record<number, { date: string; name: string; tentative?: boolean }[]> = {
  2026: [
    { date: "2026-03-04", name: "Holi" },
    { date: "2026-03-21", name: "Id-ul-Fitr", tentative: true },
    { date: "2026-03-26", name: "Ram Navami" },
    { date: "2026-03-31", name: "Mahavir Jayanti" },
    { date: "2026-04-03", name: "Good Friday" },
    { date: "2026-05-01", name: "Buddha Purnima" },
    { date: "2026-05-27", name: "Id-ul-Zuha (Bakrid)", tentative: true },
    { date: "2026-06-26", name: "Muharram", tentative: true },
    { date: "2026-08-26", name: "Milad-un-Nabi (Id-e-Milad)", tentative: true },
    { date: "2026-09-04", name: "Janmashtami (Vaishnava)" },
    { date: "2026-10-20", name: "Dussehra (Vijaya Dashami)" },
    { date: "2026-11-08", name: "Diwali (Deepavali)" },
    { date: "2026-11-24", name: "Guru Nanak Jayanti" },
    { date: "2026-12-25", name: "Christmas Day" },
  ],
};

export function holidaysBetween(from: string, to: string, categories: string[] = ["national", "gazetted"]): Holiday[] {
  const out: Holiday[] = [];
  const y0 = Number(from.slice(0, 4));
  const y1 = Number(to.slice(0, 4));
  for (let y = y0; y <= y1; y++) {
    if (categories.includes("national")) {
      for (const n of NATIONAL) {
        const date = `${y}-${n.md}`;
        if (date >= from && date <= to) out.push({ date, name: n.name, category: "national", source: "Constitution/national holiday (fixed date)" });
      }
    }
    if (categories.includes("gazetted")) {
      for (const g of GAZETTED[y] ?? []) {
        if (g.date >= from && g.date <= to) out.push({ ...g, category: "gazetted", source: HOLIDAY_SOURCE });
      }
    }
  }
  return out.sort((a, b) => a.date.localeCompare(b.date));
}

export function hasGazettedData(year: number): boolean {
  return Boolean(GAZETTED[year]);
}

/** Minimal ICS parsing (VEVENT SUMMARY + DTSTART) for import. */
export function parseIcs(text: string): { title: string; date: string; time: string | null; yearly: boolean }[] {
  const out: { title: string; date: string; time: string | null; yearly: boolean }[] = [];
  const unfolded = text.replace(/\r?\n[ \t]/g, "");
  const blocks = unfolded.split("BEGIN:VEVENT").slice(1);
  for (const b of blocks) {
    const summary = b.match(/\nSUMMARY[^:]*:(.*)/)?.[1]?.trim();
    const dt = b.match(/\nDTSTART[^:]*:(\d{8})(T(\d{2})(\d{2}))?/);
    if (!summary || !dt) continue;
    const d = dt[1];
    out.push({
      title: summary.replace(/\\,/g, ",").replace(/\\n/g, " ").slice(0, 200),
      date: `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}`,
      time: dt[2] ? `${dt[3]}:${dt[4]}` : null,
      yearly: /RRULE:[^\n]*FREQ=YEARLY/.test(b),
    });
    if (out.length >= 1000) break;
  }
  return out;
}

export function toIcs(events: { id: string; title: string; date: string; time: string | null; recurrence: string; category: string }[]): string {
  const esc = (s: string) => s.replace(/[\\,;]/g, (m) => `\\${m}`).replace(/\n/g, "\\n");
  const lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//EDITH//Calendar//EN", "CALSCALE:GREGORIAN"];
  const stamp = new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d+/, "");
  for (const e of events) {
    const d = e.date.replace(/-/g, "");
    lines.push("BEGIN:VEVENT", `UID:${e.id}@edith`, `DTSTAMP:${stamp}`);
    if (e.time) lines.push(`DTSTART:${d}T${e.time.replace(":", "")}00`);
    else lines.push(`DTSTART;VALUE=DATE:${d}`);
    lines.push(`SUMMARY:${esc(e.title)}`, `CATEGORIES:${esc(e.category)}`);
    if (e.recurrence === "yearly") lines.push("RRULE:FREQ=YEARLY");
    lines.push("END:VEVENT");
  }
  lines.push("END:VCALENDAR");
  return lines.join("\r\n") + "\r\n";
}
