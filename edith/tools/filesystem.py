"""Sandboxed Filesystem Toolpack (FILES_PACK).

Implements Section 23 and 39 of the Engineering Constitution.
Enforces strict workspace directory jailing and path traversal defense.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from edith.core.config import CONFIG
from edith.core.security import RiskLevel, SecurityViolationError

logger = logging.getLogger("edith.tools.filesystem")


class FilesystemTools:
    """Sandboxed filesystem operations."""

    def __init__(self, workspace_root: Optional[Path] = None):
        self._root = (workspace_root or CONFIG.workspace_dir).resolve()

    def _resolve_safe_path(self, user_path: str) -> Path:
        """Resolve path and verify it stays inside the allowed workspace root."""
        clean = Path(user_path)
        if not clean.is_absolute():
            resolved = (self._root / clean).resolve()
        else:
            resolved = clean.resolve()

        # Strict jail check: must start with root path
        try:
            resolved.relative_to(self._root)
        except ValueError:
            msg = f"Path traversal violation: '{user_path}' escapes workspace jail '{self._root}'"
            logger.error(msg)
            raise SecurityViolationError(msg)

        return resolved

    def read_file(self, path: str, offset: int = 0, limit: int = 500) -> Dict[str, Any]:
        """Read lines from a jailed file."""
        target = self._resolve_safe_path(path)
        if not target.exists():
            return {"success": False, "error": f"File '{path}' does not exist."}
        if target.is_dir():
            return {"success": False, "error": f"Path '{path}' is a directory."}

        try:
            lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
            total_lines = len(lines)
            selected = lines[offset : offset + limit]
            return {
                "success": True,
                "path": str(target),
                "total_lines": total_lines,
                "offset": offset,
                "lines": selected,
                "content": "\n".join(selected),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def write_file(self, path: str, content: str, overwrite: bool = True) -> Dict[str, Any]:
        """Write content into a jailed file."""
        target = self._resolve_safe_path(path)
        if target.exists() and not overwrite:
            return {"success": False, "error": f"File '{path}' exists and overwrite=False."}

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            logger.info("Wrote %d bytes to %s", len(content), target)
            return {"success": True, "path": str(target), "bytes_written": len(content)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_dir(self, path: str = ".", recursive: bool = False) -> Dict[str, Any]:
        """List contents of a directory."""
        target = self._resolve_safe_path(path)
        if not target.exists() or not target.is_dir():
            return {"success": False, "error": f"Directory '{path}' does not exist."}

        try:
            entries = []
            if recursive:
                for p in target.rglob("*"):
                    entries.append({"name": str(p.relative_to(target)), "is_dir": p.is_dir(), "size": p.stat().st_size if p.is_file() else 0})
            else:
                for p in target.iterdir():
                    entries.append({"name": p.name, "is_dir": p.is_dir(), "size": p.stat().st_size if p.is_file() else 0})

            return {"success": True, "path": str(target), "entries": entries}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_file(self, path: str) -> Dict[str, Any]:
        """Delete a file inside the jailed workspace."""
        target = self._resolve_safe_path(path)
        if not target.exists():
            return {"success": False, "error": f"File '{path}' does not exist."}

        try:
            if target.is_dir():
                return {"success": False, "error": f"Cannot delete directory '{path}' with delete_file."}
            target.unlink()
            logger.warning("Deleted file: %s", target)
            return {"success": True, "path": str(target)}
        except Exception as e:
            return {"success": False, "error": str(e)}


# Global filesystem tool instance
FS_TOOLS = FilesystemTools()
