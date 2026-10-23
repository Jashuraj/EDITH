"""Durable Reminders, Timers, and Calendar Engine for EDITH.

Supports:
- Recurrence (none, daily, weekdays, weekly by day, monthly, yearly)
- Manual arrival triggers ("when I reach home")
- Snooze (default 10m), complete, dismiss, delete
- Calendar events with yearly recurrence expansion (birthdays, anniversaries)
- ICS calendar import and export
- SQLite persistent airlock storage
"""

from __future__ import annotations

import datetime
import json
import logging
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("edith.tasks.reminders")

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "edith_memory.db"


def _get_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_reminders_schema() -> None:
    """Initialize database tables for reminders, events, and profile."""
    with _get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS reminders (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                notes TEXT,
                due_at TEXT NOT NULL,
                timezone TEXT DEFAULT 'Asia/Kolkata',
                recurrence TEXT DEFAULT 'none',
                by_weekday TEXT,
                priority TEXT DEFAULT 'normal',
                category TEXT DEFAULT 'general',
                trigger TEXT DEFAULT 'time',
                status TEXT DEFAULT 'pending',
                source TEXT DEFAULT 'ui',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS calendar_events (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                date TEXT NOT NULL,
                time TEXT,
                category TEXT DEFAULT 'event',
                recurrence TEXT DEFAULT 'none',
                notes TEXT,
                color TEXT,
                source TEXT DEFAULT 'ui',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS user_profile (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        """)
        conn.commit()


# Initialize on import
init_reminders_schema()


# ──────────────── Profile Operations ────────────────
DEFAULT_PROFILE: Dict[str, Any] = {
    "name": "Boss",
    "country": "IN",
    "state": "KA",
    "city": "Bengaluru",
    "timezone": "Asia/Kolkata",
    "holidayCategories": ["national", "gazetted"],
    "resourceProfile": "8gb",
    "quietStart": None,
    "quietEnd": None,
}


def get_profile() -> Dict[str, Any]:
    with _get_db() as conn:
        cur = conn.execute("SELECT value FROM user_profile WHERE key = 'profile'")
        row = cur.fetchone()
        if row:
            try:
                prof = json.loads(row["value"])
                merged = dict(DEFAULT_PROFILE)
                merged.update(prof)
                return merged
            except Exception:
                pass
    return dict(DEFAULT_PROFILE)


def set_profile(data: Dict[str, Any]) -> Dict[str, Any]:
    cur = get_profile()
    cur.update(data)
    with _get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO user_profile (key, value) VALUES ('profile', ?)",
            (json.dumps(cur),),
        )
        conn.commit()
    return cur


def get_tutorial_state() -> Dict[str, bool]:
    with _get_db() as conn:
        cur = conn.execute("SELECT value FROM user_profile WHERE key = 'tutorial'")
        row = cur.fetchone()
        if row:
            try:
                return json.loads(row["value"])
            except Exception:
                pass
    return {}


def set_tutorial_state(data: Dict[str, bool]) -> None:
    with _get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO user_profile (key, value) VALUES ('tutorial', ?)",
            (json.dumps(data),),
        )
        conn.commit()


# ──────────────── Reminders Operations ────────────────
def create_reminder(
    title: str,
    due_at: datetime.datetime | str,
    notes: Optional[str] = None,
    recurrence: str = "none",
    by_weekday: Optional[List[int]] = None,
    priority: str = "normal",
    category: str = "general",
    trigger: str = "time",
    source: str = "ui",
    timezone: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a persistent reminder."""
    rem_id = str(uuid.uuid4())
    if isinstance(due_at, datetime.datetime):
        due_str = due_at.isoformat()
    else:
        due_str = str(due_at)

    profile = get_profile()
    tz = timezone or profile.get("timezone", "Asia/Kolkata")
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    row = {
        "id": rem_id,
        "title": title[:200],
        "notes": (notes or "")[:1000] if notes else None,
        "due_at": due_str,
        "timezone": tz,
        "recurrence": recurrence if recurrence in ("none", "daily", "weekdays", "weekly", "monthly", "yearly") else "none",
        "by_weekday": json.dumps(by_weekday) if by_weekday else None,
        "priority": priority if priority in ("low", "normal", "high") else "normal",
        "category": (category or "general")[:30],
        "trigger": "manual_arrival" if trigger == "manual_arrival" else "time",
        "status": "pending",
        "source": source,
        "created_at": now_iso,
    }

    with _get_db() as conn:
        conn.execute(
            """INSERT INTO reminders
               (id, title, notes, due_at, timezone, recurrence, by_weekday, priority, category, trigger, status, source, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                row["id"], row["title"], row["notes"], row["due_at"], row["timezone"],
                row["recurrence"], row["by_weekday"], row["priority"], row["category"],
                row["trigger"], row["status"], row["source"], row["created_at"],
            ),
        )
        conn.commit()

    return row


def list_reminders(include_all: bool = False) -> List[Dict[str, Any]]:
    """List reminders. By default lists only pending/snoozed ones."""
    with _get_db() as conn:
        if include_all:
            cur = conn.execute("SELECT * FROM reminders ORDER BY due_at ASC")
        else:
            cur = conn.execute("SELECT * FROM reminders WHERE status IN ('pending', 'snoozed') ORDER BY due_at ASC")
        rows = [dict(r) for r in cur.fetchall()]

    for r in rows:
        if r.get("by_weekday"):
            try:
                r["by_weekday"] = json.loads(r["by_weekday"])
            except Exception:
                pass
    return rows


def snooze_reminder(reminder_id: str, minutes: int = 10) -> Optional[Dict[str, Any]]:
    """Snooze a reminder by N minutes."""
    new_due = (datetime.datetime.now() + datetime.timedelta(minutes=minutes)).isoformat()
    with _get_db() as conn:
        conn.execute(
            "UPDATE reminders SET due_at = ?, status = 'snoozed' WHERE id = ?",
            (new_due, reminder_id),
        )
        conn.commit()
        cur = conn.execute("SELECT * FROM reminders WHERE id = ?", (reminder_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def complete_reminder(reminder_id: str) -> Optional[Dict[str, Any]]:
    """Mark reminder as completed, advancing recurrence if recurring."""
    with _get_db() as conn:
        cur = conn.execute("SELECT * FROM reminders WHERE id = ?", (reminder_id,))
        r = cur.fetchone()
        if not r:
            return None
        rec = r["recurrence"]
        if rec and rec != "none":
            # Advance due date
            try:
                dt = datetime.datetime.fromisoformat(r["due_at"])
                if rec == "daily":
                    dt += datetime.timedelta(days=1)
                elif rec == "weekdays":
                    dt += datetime.timedelta(days=1)
                    while dt.weekday() >= 5:
                        dt += datetime.timedelta(days=1)
                elif rec == "weekly":
                    dt += datetime.timedelta(weeks=1)
                elif rec == "monthly":
                    dt += datetime.timedelta(days=30)
                elif rec == "yearly":
                    dt += datetime.timedelta(days=365)
                conn.execute(
                    "UPDATE reminders SET due_at = ?, status = 'pending' WHERE id = ?",
                    (dt.isoformat(), reminder_id),
                )
                conn.commit()
                return dict(r)
            except Exception:
                pass

        conn.execute("UPDATE reminders SET status = 'completed' WHERE id = ?", (reminder_id,))
        conn.commit()
        cur = conn.execute("SELECT * FROM reminders WHERE id = ?", (reminder_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def dismiss_reminder(reminder_id: str) -> Optional[Dict[str, Any]]:
    """Dismiss a reminder without marking complete."""
    with _get_db() as conn:
        conn.execute("UPDATE reminders SET status = 'dismissed' WHERE id = ?", (reminder_id,))
        conn.commit()
        cur = conn.execute("SELECT * FROM reminders WHERE id = ?", (reminder_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def delete_reminder(reminder_id: str) -> bool:
    """Delete reminder entirely."""
    with _get_db() as conn:
        cur = conn.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
        conn.commit()
        return cur.rowcount > 0


def fire_arrival() -> List[Dict[str, Any]]:
    """Fire all reminders waiting on manual arrival trigger."""
    with _get_db() as conn:
        cur = conn.execute(
            "SELECT * FROM reminders WHERE trigger = 'manual_arrival' AND status = 'pending'"
        )
        rows = [dict(r) for r in cur.fetchall()]
        conn.execute(
            "UPDATE reminders SET due_at = ?, trigger = 'time' WHERE trigger = 'manual_arrival' AND status = 'pending'",
            (datetime.datetime.now().isoformat(),),
        )
        conn.commit()
        return rows


# ──────────────── Calendar Operations ────────────────
def create_event(
    title: str,
    date: str,
    time: Optional[str] = None,
    category: str = "event",
    recurrence: str = "none",
    notes: Optional[str] = None,
    color: Optional[str] = None,
    source: str = "ui",
) -> Dict[str, Any]:
    """Create a calendar event."""
    event_id = str(uuid.uuid4())
    rec = "yearly" if recurrence == "yearly" or category in ("birthday", "anniversary") else "none"
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    row = {
        "id": event_id,
        "title": title[:200],
        "date": date[:10],
        "time": time[:5] if time else None,
        "category": category[:30],
        "recurrence": rec,
        "notes": (notes or "")[:1000] if notes else None,
        "color": color[:20] if color else None,
        "source": source,
        "created_at": now_iso,
    }

    with _get_db() as conn:
        conn.execute(
            """INSERT INTO calendar_events
               (id, title, date, time, category, recurrence, notes, color, source, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                row["id"], row["title"], row["date"], row["time"], row["category"],
                row["recurrence"], row["notes"], row["color"], row["source"], row["created_at"],
            ),
        )
        conn.commit()

    return row


def list_events(from_date: str, to_date: str) -> List[Dict[str, Any]]:
    """List calendar events in range, expanding yearly recurring events."""
    with _get_db() as conn:
        cur = conn.execute(
            """SELECT * FROM calendar_events
               WHERE (date >= ? AND date <= ?) OR recurrence = 'yearly'
               ORDER BY date ASC""",
            (from_date, to_date),
        )
        all_events = [dict(r) for r in cur.fetchall()]

    expanded: List[Dict[str, Any]] = []
    y0 = int(from_date[:4])
    y1 = int(to_date[:4])

    for e in all_events:
        if e.get("recurrence") == "yearly":
            orig_month_day = e["date"][4:]
            for y in range(y0, y1 + 1):
                occurs = f"{y}{orig_month_day}"
                if from_date <= occurs <= to_date and occurs >= e["date"]:
                    item = dict(e)
                    item["occurs"] = occurs
                    expanded.append(item)
        else:
            item = dict(e)
            item["occurs"] = e["date"]
            expanded.append(item)

    expanded.sort(key=lambda x: (x["occurs"], x.get("time") or ""))
    return expanded


def delete_event(event_id: str) -> bool:
    """Delete a calendar event."""
    with _get_db() as conn:
        cur = conn.execute("DELETE FROM calendar_events WHERE id = ?", (event_id,))
        conn.commit()
        return cur.rowcount > 0


def to_ics(events: List[Dict[str, Any]]) -> str:
    """Export calendar events to iCalendar (ICS) format."""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//EDITH AI//Calendar//EN",
        "CALSCALE:GREGORIAN",
    ]
    for e in events:
        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{e['id']}@edith.ai")
        lines.append(f"SUMMARY:{e['title']}")
        dt = e.get("occurs") or e.get("date") or "2026-01-01"
        clean_date = dt.replace("-", "")
        if e.get("time"):
            tm = e["time"].replace(":", "") + "00"
            lines.append(f"DTSTART:{clean_date}T{tm}")
        else:
            lines.append(f"DTSTART;VALUE=DATE:{clean_date}")
        if e.get("recurrence") == "yearly":
            lines.append("RRULE:FREQ=YEARLY")
        if e.get("notes"):
            lines.append(f"DESCRIPTION:{e['notes']}")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def parse_ics(ics_text: str) -> List[Dict[str, Any]]:
    """Parse basic VEVENT records from ICS text."""
    events: List[Dict[str, Any]] = []
    lines = ics_text.splitlines()
    in_event = False
    cur: Dict[str, Any] = {}

    for line in lines:
        line = line.strip()
        if line == "BEGIN:VEVENT":
            in_event = True
            cur = {"yearly": False}
        elif line == "END:VEVENT":
            in_event = False
            if cur.get("title") and cur.get("date"):
                events.append(cur)
        elif in_event:
            if line.startswith("SUMMARY:"):
                cur["title"] = line[len("SUMMARY:"):].strip()
            elif line.startswith("DTSTART"):
                val = line.split(":")[-1].strip()
                if "T" in val:
                    d_part, t_part = val.split("T", 1)
                    cur["date"] = f"{d_part[:4]}-{d_part[4:6]}-{d_part[6:8]}"
                    cur["time"] = f"{t_part[:2]}:{t_part[2:4]}"
                elif len(val) >= 8:
                    cur["date"] = f"{val[:4]}-{val[4:6]}-{val[6:8]}"
            elif "RRULE:" in line and "YEARLY" in line:
                cur["yearly"] = True
    return events
