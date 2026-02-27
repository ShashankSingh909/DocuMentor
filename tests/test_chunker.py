"""
Tests for SmartChunker — strategy selection, chunking output, metadata enrichment.

SmartChunker.chunk_document() takes a single Dict argument with keys like
'content', 'title', 'technology', 'source', 'doc_type', etc.
"""
import pytest

from rag_system.core.chunking.chunker import SmartChunker


@pytest.fixture
def chunker():
    return SmartChunker(chunk_size=500, chunk_overlap=50)


def _make_doc(content: str, technology: str = "python", source: str = "docs", doc_type: str = "reference") -> dict:
    """Helper to build a document dict compatible with chunk_document()."""
    return {
        "content": content,
        "title": "Test Document",
        "technology": technology,
        "source": source,
        "doc_type": doc_type,
    }


# ─── Strategy Detection ───────────────────────────────────────────────────────

class TestChunkingStrategyDetection:

    def test_api_doc_content_produces_chunks(self, chunker, api_doc_content):
        doc = _make_doc(api_doc_content, technology="fastapi", doc_type="api_reference")
        chunks = chunker.chunk_document(doc)
        assert len(chunks) > 0

    def test_code_content_produces_chunks(self, chunker, code_content):
        doc = _make_doc(code_content, doc_type="guide")
        chunks = chunker.chunk_document(doc)
        assert len(chunks) > 0

    def test_plain_text_produces_chunks(self, chunker, plain_text_content):
        doc = _make_doc(plain_text_content, doc_type="reference")
        chunks = chunker.chunk_document(doc)
        assert len(chunks) > 0


# ─── Output Format ────────────────────────────────────────────────────────────

class TestChunkOutputFormat:

    def test_chunks_have_content_key(self, chunker, plain_text_content):
        chunks = chunker.chunk_document(_make_doc(plain_text_content))
        for chunk in chunks:
            assert "content" in chunk
            assert isinstance(chunk["content"], str)
            assert len(chunk["content"]) > 0

    def test_chunks_have_metadata_key(self, chunker, plain_text_content):
        chunks = chunker.chunk_document(_make_doc(plain_text_content))
        for chunk in chunks:
            assert "metadata" in chunk
            assert isinstance(chunk["metadata"], dict)

    def test_chunks_have_chunk_id_in_metadata(self, chunker, plain_text_content):
        chunks = chunker.chunk_document(_make_doc(plain_text_content))
        for chunk in chunks:
            assert "chunk_id" in chunk["metadata"]
            assert isinstance(chunk["metadata"]["chunk_id"], str)
            assert len(chunk["metadata"]["chunk_id"]) > 0

    def test_chunk_ids_are_unique(self, chunker, plain_text_content):
        chunks = chunker.chunk_document(_make_doc(plain_text_content))
        ids = [c["metadata"]["chunk_id"] for c in chunks]
        assert len(ids) == len(set(ids))

    def test_chunk_ids_are_hex(self, chunker, plain_text_content):
        chunks = chunker.chunk_document(_make_doc(plain_text_content))
        for chunk in chunks:
            cid = chunk["metadata"]["chunk_id"]
            assert len(cid) == 16  # md5[:16]
            assert all(c in "0123456789abcdef" for c in cid)


# ─── Metadata Propagation ─────────────────────────────────────────────────────

class TestChunkMetadata:

    def test_technology_metadata_propagated(self, chunker, plain_text_content):
        doc = _make_doc(plain_text_content, technology="django")
        chunks = chunker.chunk_document(doc)
        for chunk in chunks:
            assert chunk["metadata"].get("technology") == "django"

    def test_source_metadata_propagated(self, chunker, plain_text_content):
        doc = _make_doc(plain_text_content, source="my_source")
        chunks = chunker.chunk_document(doc)
        for chunk in chunks:
            assert chunk["metadata"].get("source") == "my_source"


# ─── Chunk Size Constraints ───────────────────────────────────────────────────

class TestChunkSizeConstraints:

    def test_chunks_not_larger_than_chunk_size_plus_slack(self, plain_text_content):
        chunk_size = 300
        chunker = SmartChunker(chunk_size=chunk_size, chunk_overlap=50)
        chunks = chunker.chunk_document(_make_doc(plain_text_content))
        for chunk in chunks:
            assert len(chunk["content"]) <= chunk_size * 3

    def test_short_content_produces_single_chunk(self, chunker):
        doc = _make_doc("This is a very short document.")
        chunks = chunker.chunk_document(doc)
        assert len(chunks) == 1

    def test_empty_content_returns_empty_list(self, chunker):
        doc = _make_doc("")
        chunks = chunker.chunk_document(doc)
        assert chunks == []

    def test_whitespace_only_content_returns_empty_list(self, chunker):
        doc = _make_doc("   \n\n   ")
        chunks = chunker.chunk_document(doc)
        assert chunks == []


# ─── Determinism ─────────────────────────────────────────────────────────────

class TestChunkDeterminism:

    def test_same_content_same_chunk_ids(self, chunker, plain_text_content):
        doc = _make_doc(plain_text_content)
        chunks1 = chunker.chunk_document(doc)
        chunks2 = chunker.chunk_document(doc)
        ids1 = [c["metadata"]["chunk_id"] for c in chunks1]
        ids2 = [c["metadata"]["chunk_id"] for c in chunks2]
        assert ids1 == ids2

    def test_different_content_different_chunk_ids(self, chunker):
        chunks1 = chunker.chunk_document(_make_doc("Content A " * 50))
        chunks2 = chunker.chunk_document(_make_doc("Content B " * 50))
        ids1 = set(c["metadata"]["chunk_id"] for c in chunks1)
        ids2 = set(c["metadata"]["chunk_id"] for c in chunks2)
        assert ids1.isdisjoint(ids2)
