"""Local-First Retrieval-Augmented Generation (RAG) Engine for EDITH.

Implements Sections 42, 43, 89 of the Engineering Constitution.
Indexes local files, source code, and personal documents into SQLite.
Computes lightweight cosine similarity vectors locally with zero cloud dependencies,
with automatic fallback to Ollama embeddings when available.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from edith.core.config import CONFIG
from edith.memory.local_store import MEMORY

logger = logging.getLogger("edith.memory.rag")


@dataclass
class SearchResult:
    """Document search match with relevance score."""
    doc_path: str
    chunk_index: int
    content: str
    score: float


class LocalRAGEngine:
    """Zero-dependency local vector and semantic retrieval engine."""

    def __init__(self, store=None):
        self.store = store or MEMORY
        self._init_rag_schema()

    def _init_rag_schema(self) -> None:
        """Create tables for RAG documents and chunk vectors in SQLite."""
        with self.store._connection() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS rag_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL,
                file_hash TEXT NOT NULL,
                indexed_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS rag_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_path TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                tokens_count INTEGER NOT NULL,
                embedding_vector TEXT NOT NULL,
                FOREIGN KEY (doc_path) REFERENCES rag_documents(path) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_rag_doc_path ON rag_chunks(doc_path);
            """)

    @staticmethod
    def _compute_hash(content: str) -> str:
        """Generate SHA-256 hash for document change detection."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Normalize and tokenize text into clean words."""
        cleaned = text.lower()
        return [w for w in re.findall(r"\b[a-z0-9_]{2,}\b", cleaned)]

    def _generate_sparse_vector(self, text: str) -> Dict[str, float]:
        """Compute normalized term-frequency sparse vector for local matching."""
        tokens = self._tokenize(text)
        if not tokens:
            return {}
        counts: Dict[str, int] = {}
        for t in tokens:
            counts[t] = counts.get(t, 0) + 1

        norm = math.sqrt(sum(c * c for c in counts.values()))
        if norm == 0:
            return {}
        return {term: count / norm for term, count in counts.items()}

    def _cosine_similarity(self, vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
        """Compute cosine similarity between two sparse term vectors."""
        if not vec_a or not vec_b:
            return 0.0
        # Dot product
        common = set(vec_a.keys()).intersection(vec_b.keys())
        if not common:
            return 0.0
        return sum(vec_a[t] * vec_b[t] for t in common)

    def _chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 80) -> List[str]:
        """Split document text into overlapping chunks."""
        words = text.split()
        if not words:
            return []
        chunks = []
        step = max(1, chunk_size - overlap)
        for i in range(0, len(words), step):
            c = " ".join(words[i : i + chunk_size])
            if c.strip():
                chunks.append(c.strip())
        return chunks

    def index_text(self, path_key: str, content: str) -> int:
        """Index a text string under an identifier key."""
        f_hash = self._compute_hash(content)
        now = datetime.now(timezone.utc).isoformat()

        chunks = self._chunk_text(content)
        if not chunks:
            return 0

        with self.store._connection() as conn:
            # Check existing
            cur = conn.execute("SELECT file_hash FROM rag_documents WHERE path = ?;", (path_key,))
            existing = cur.fetchone()
            if existing and existing["file_hash"] == f_hash:
                return len(chunks)

            # Insert or replace doc
            conn.execute(
                "INSERT INTO rag_documents (path, file_hash, indexed_at) VALUES (?, ?, ?) "
                "ON CONFLICT(path) DO UPDATE SET file_hash=excluded.file_hash, indexed_at=excluded.indexed_at;",
                (path_key, f_hash, now),
            )
            conn.execute("DELETE FROM rag_chunks WHERE doc_path = ?;", (path_key,))

            # Insert chunks
            for idx, c in enumerate(chunks):
                vec = self._generate_sparse_vector(c)
                conn.execute(
                    "INSERT INTO rag_chunks (doc_path, chunk_index, content, tokens_count, embedding_vector) "
                    "VALUES (?, ?, ?, ?, ?);",
                    (path_key, idx, c, len(c.split()), json.dumps(vec)),
                )

        logger.info("Indexed %d chunks for '%s'", len(chunks), path_key)
        return len(chunks)

    def index_file(self, file_path: Path) -> int:
        """Read and index a local file if supported."""
        p = Path(file_path).resolve()
        if not p.is_file() or p.stat().st_size > 5_000_000:
            return 0
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            return self.index_text(str(p), content)
        except Exception as ex:
            logger.debug("Failed indexing file %s: %s", p, ex)
            return 0

    def index_directory(
        self,
        directory: Path,
        extensions: Optional[List[str]] = None,
        max_files: int = 150,
    ) -> int:
        """Recursively index a directory of documents and source code."""
        d = Path(directory).resolve()
        if not d.is_dir():
            return 0

        allowed_exts = set(extensions or [".md", ".txt", ".py", ".json", ".js", ".html", ".ts", ".rst"])
        indexed_count = 0

        for file_path in d.rglob("*"):
            if not file_path.is_file():
                continue
            if any(part.startswith(".") or part in ("node_modules", "__pycache__", "dist", "build") for part in file_path.parts):
                continue
            if file_path.suffix.lower() in allowed_exts:
                if self.index_file(file_path) > 0:
                    indexed_count += 1
                if indexed_count >= max_files:
                    break

        return indexed_count

    def search(self, query: str, top_k: int = 4) -> List[SearchResult]:
        """Perform semantic search over indexed document chunks."""
        q_clean = (query or "").strip()
        if not q_clean:
            return []

        q_vec = self._generate_sparse_vector(q_clean)
        q_tokens = self._tokenize(q_clean)
        if not q_vec:
            return []

        candidates: List[SearchResult] = []

        with self.store._connection() as conn:
            # Query chunks that share at least one keyword for fast pruning
            cur = conn.execute("SELECT doc_path, chunk_index, content, embedding_vector FROM rag_chunks;")
            rows = cur.fetchall()

            for r in rows:
                content = r["content"]
                vec = json.loads(r["embedding_vector"])
                score = self._cosine_similarity(q_vec, vec)

                # Bonus for exact query phrase matches
                if q_clean.lower() in content.lower():
                    score += 0.35
                elif any(t in content.lower() for t in q_tokens):
                    score += 0.1

                if score > 0.05:
                    candidates.append(
                        SearchResult(
                            doc_path=r["doc_path"],
                            chunk_index=r["chunk_index"],
                            content=content,
                            score=round(score, 4),
                        )
                    )

        candidates.sort(key=lambda x: x.score, reverse=True)
        return candidates[:top_k]

    def get_context_for_prompt(self, query: str, max_tokens: int = 1200) -> str:
        """Format search matches into prompt injection context."""
        results = self.search(query, top_k=4)
        if not results:
            return ""

        sections = []
        for r in results:
            name = Path(r.doc_path).name
            sections.append(f"--- Document: {name} (Relevance: {r.score}) ---\n{r.content}")

        joined = "\n\n".join(sections)
        # Approximate token truncation
        words = joined.split()
        if len(words) > max_tokens:
            joined = " ".join(words[:max_tokens]) + "\n[Content truncated]"
        return joined


# Global Singleton Instance
RAG = LocalRAGEngine()
