"""Unit tests for Local RAG Engine."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from edith.memory.local_store import LocalStore
from edith.memory.rag import LocalRAGEngine


class TestLocalRAG(unittest.TestCase):
    """Test Local RAG indexing and cosine retrieval."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_rag.db"
        self.store = LocalStore(db_path=self.db_path)
        self.rag = LocalRAGEngine(store=self.store)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_index_and_search_text(self):
        """Verify indexing text chunks and matching relevant content."""
        doc_key = "quantum_notes.md"
        content = "Quantum entanglement is a physical phenomenon where particles remain connected regardless of distance."
        chunks_indexed = self.rag.index_text(doc_key, content)
        self.assertGreater(chunks_indexed, 0)

        results = self.rag.search("quantum entanglement", top_k=2)
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].doc_path, doc_key)
        self.assertIn("entanglement", results[0].content)
        self.assertGreater(results[0].score, 0.2)

    def test_search_non_matching_query(self):
        """Verify non-relevant queries return empty or low scores."""
        self.rag.index_text("recipe.txt", "Mix flour, sugar, and cocoa to bake a chocolate cake.")
        results = self.rag.search("quantum mechanics", top_k=2)
        self.assertEqual(len(results), 0)

    def test_get_context_for_prompt(self):
        """Verify prompt context formatting."""
        self.rag.index_text("edith_specs.md", "EDITH uses Level 0 reflex engine for sub-15ms response latency.")
        context = self.rag.get_context_for_prompt("reflex engine latency")
        self.assertIn("edith_specs.md", context)
        self.assertIn("Level 0 reflex", context)


if __name__ == "__main__":
    unittest.main()
