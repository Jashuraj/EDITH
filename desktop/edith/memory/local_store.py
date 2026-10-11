"""Structured Local SQLite Memory Store for EDITH.

Implements Sections 42, 43, 89 (Audit Log), 157 of the Engineering Constitution.
Manages user key-value memory, conversations, audit trails, and task checkpoints.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from edith.core.config import CONFIG

logger = logging.getLogger("edith.memory.local_store")


class LocalStore:
    """Thread-safe SQLite persistent store for local data."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or (CONFIG.data_dir / "edith_memory.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager guaranteeing connection closure to prevent Windows file locks."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        """Create tables for preferences, conversations, audit logs, and task checkpoints."""
        with self._connection() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                model TEXT,
                timestamp TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                tool_name TEXT,
                parameters TEXT,
                risk_level TEXT NOT NULL,
                status TEXT NOT NULL,
                result TEXT,
                timestamp TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS task_checkpoints (
                task_id TEXT PRIMARY KEY,
                goal TEXT NOT NULL,
                step_index INTEGER NOT NULL,
                total_steps INTEGER NOT NULL,
                status TEXT NOT NULL,
                context_data TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS learned_skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal TEXT UNIQUE NOT NULL,
                command TEXT NOT NULL,
                description TEXT,
                success_count INTEGER DEFAULT 1,
                last_verified TEXT NOT NULL
            );
            """)

    def set_preference(self, key: str, value: Any) -> None:
        """Persist a user preference or state value."""
        now = datetime.now(timezone.utc).isoformat()
        val_str = json.dumps(value)
        with self._connection() as conn:
            conn.execute(
                "INSERT INTO preferences (key, value, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at;",
                (key, val_str, now),
            )

    def get_preference(self, key: str, default: Any = None) -> Any:
        """Retrieve a stored preference."""
        with self._connection() as conn:
            cur = conn.execute("SELECT value FROM preferences WHERE key = ?;", (key,))
            row = cur.fetchone()
            if row:
                return json.loads(row["value"])
            return default

    def remember_fact(self, fact: str) -> str:
        """Store a fact learned from the user in SQLite."""
        f = (fact or "").strip().rstrip(".")
        if not f:
            return ""
        facts = self.get_preference("learned_memories", [])
        if not isinstance(facts, list):
            facts = []
        if not any(f.lower() == existing.lower() for existing in facts):
            facts.append(f)
            self.set_preference("learned_memories", facts[-100:])
        return f

    def get_memories(self) -> List[str]:
        """Retrieve all learned user facts and memories."""
        facts = self.get_preference("learned_memories", [])
        return facts if isinstance(facts, list) else []

    def forget_memory(self, query: str) -> bool:
        """Remove a memory matching query or clear all."""
        q = (query or "").strip().lower()
        facts = self.get_memories()
        if q in ("all", "everything", "all memories", "all facts"):
            self.set_preference("learned_memories", [])
            return True
        kept = [f for f in facts if q not in f.lower()]
        if len(kept) != len(facts):
            self.set_preference("learned_memories", kept)
            return True
        return False

    def teach_command(self, trigger: str, action: str) -> str:
        """Teach EDITH a custom trigger-action alias."""
        t = (trigger or "").strip().lower()
        a = (action or "").strip()
        custom = self.get_preference("custom_commands", {})
        if not isinstance(custom, dict):
            custom = {}
        custom[t] = a
        self.set_preference("custom_commands", custom)
        return f"Learned: when you say '{t}', I will execute '{a}'."

    def get_custom_command(self, trigger: str) -> Optional[str]:
        """Look up a custom learned trigger command."""
        t = (trigger or "").strip().lower()
        custom = self.get_preference("custom_commands", {})
        if isinstance(custom, dict):
            return custom.get(t)
        return None

    def remember_skill(self, goal: str, command: str, description: str = "") -> None:
        """Store or update a learned autonomous procedure in SQLite."""
        now = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            conn.execute(
                "INSERT INTO learned_skills (goal, command, description, success_count, last_verified) "
                "VALUES (?, ?, ?, 1, ?) "
                "ON CONFLICT(goal) DO UPDATE SET command=excluded.command, "
                "description=excluded.description, success_count=success_count+1, last_verified=excluded.last_verified;",
                (goal.strip().lower(), command.strip(), description.strip(), now),
            )

    def find_learned_skill(self, goal: str) -> Optional[Dict[str, Any]]:
        """Look up a previously learned skill or procedure."""
        g = goal.strip().lower()
        with self._connection() as conn:
            cur = conn.execute("SELECT * FROM learned_skills WHERE goal = ?;", (g,))
            row = cur.fetchone()
            if row:
                return dict(row)
            cur = conn.execute("SELECT * FROM learned_skills WHERE ? LIKE ('%' || goal || '%') OR goal LIKE ('%' || ? || '%');", (g, g))
            row = cur.fetchone()
            if row:
                return dict(row)
        return None

    def get_all_learned_skills(self) -> List[Dict[str, Any]]:
        """Retrieve all self-learned autonomous skills."""
        with self._connection() as conn:
            cur = conn.execute("SELECT * FROM learned_skills ORDER BY success_count DESC, id DESC;")
            return [dict(row) for row in cur.fetchall()]

    def log_audit(
        self,
        action: str,
        tool_name: Optional[str],
        parameters: Dict[str, Any],
        risk_level: str,
        status: str,
        result: str = "",
    ) -> int:
        """Append an entry to the immutable audit log (Section 89)."""
        now = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            cur = conn.execute(
                "INSERT INTO audit_log (action, tool_name, parameters, risk_level, status, result, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?, ?);",
                (action, tool_name, json.dumps(parameters), risk_level, status, result, now),
            )
            return cur.lastrowid

    def get_recent_audit_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch recent audit log items for 'what did you do?' queries."""
        with self._connection() as conn:
            cur = conn.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT ?;", (limit,))
            return [dict(row) for row in cur.fetchall()]

    def save_checkpoint(
        self,
        task_id: str,
        goal: str,
        step_index: int,
        total_steps: int,
        status: str,
        context_data: Dict[str, Any],
    ) -> None:
        """Save a task execution checkpoint."""
        now = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            conn.execute(
                "INSERT INTO task_checkpoints (task_id, goal, step_index, total_steps, status, context_data, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(task_id) DO UPDATE SET step_index=excluded.step_index, status=excluded.status, "
                "context_data=excluded.context_data, updated_at=excluded.updated_at;",
                (task_id, goal, step_index, total_steps, status, json.dumps(context_data), now),
            )

    def get_checkpoint(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve task checkpoint for resuming."""
        with self._connection() as conn:
            cur = conn.execute("SELECT * FROM task_checkpoints WHERE task_id = ?;", (task_id,))
            row = cur.fetchone()
            if row:
                d = dict(row)
                d["context_data"] = json.loads(d["context_data"])
                return d
            return None


# Global memory store singleton
MEMORY = LocalStore()
