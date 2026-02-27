"""
Tests for IngestionPipeline — load, chunk, embed, store, remove, progress.
Uses mocked core components so no real ChromaDB/LLM/filesystem needed.
"""
import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from rag_system.core.registry.models import IngestionStatus, DocSourceType
from rag_system.core.registry.registry import DocRegistry
from rag_system.core.ingestion.pipeline import IngestionPipeline
from rag_system.config.settings import get_settings


# ─── Helper ──────────────────────────────────────────────────────────────────

def _make_registry(catalog_path: str, state_path: str) -> DocRegistry:
    settings = get_settings()
    orig_catalog = settings.registry_catalog_path
    orig_state = settings.registry_state_path
    try:
        settings.registry_catalog_path = catalog_path
        settings.registry_state_path = state_path
        return DocRegistry()
    finally:
        settings.registry_catalog_path = orig_catalog
        settings.registry_state_path = orig_state


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def temp_env(tmp_path):
    """Full temporary environment with catalog, state, preembedded docs."""
    catalog_data = [
        {
            "id": "python",
            "name": "Python",
            "category": "language",
            "icon": "",
            "source_type": "preembedded_file",
            "source_paths": [str(tmp_path / "preembedded" / "python_docs.txt")],
        },
        {
            "id": "mylib",
            "name": "MyLib",
            "category": "library",
            "icon": "",
            "source_type": "web_scrape",
            "source_paths": ["https://example.com/docs"],
        },
    ]

    pre_dir = tmp_path / "preembedded"
    pre_dir.mkdir()
    (pre_dir / "python_docs.txt").write_text(
        "Python is a versatile programming language. " * 100,
        encoding="utf-8",
    )

    catalog_path = tmp_path / "catalog.json"
    state_path = tmp_path / "state.json"

    catalog_path.write_text(json.dumps(catalog_data))

    return {
        "tmp_path": tmp_path,
        "catalog_path": str(catalog_path),
        "state_path": str(state_path),
    }


@pytest.fixture
def registry(temp_env):
    return _make_registry(temp_env["catalog_path"], temp_env["state_path"])


@pytest.fixture
def mock_vector_store():
    vs = MagicMock()
    vs.add_documents.return_value = 10
    vs.collection = MagicMock()
    return vs


@pytest.fixture
def mock_chunker():
    chunker = MagicMock()
    # chunk_document returns a list of chunk dicts
    chunker.chunk_document.return_value = [
        {"content": "chunk 1", "metadata": {"technology": "python"}, "chunk_id": "c1"},
        {"content": "chunk 2", "metadata": {"technology": "python"}, "chunk_id": "c2"},
    ]
    return chunker


@pytest.fixture
def mock_doc_processor():
    proc = MagicMock()
    proc.process_file.return_value = {"success": True, "content": "Processed content. " * 50}
    return proc


@pytest.fixture
def pipeline(registry, mock_vector_store, mock_chunker, mock_doc_processor):
    return IngestionPipeline(
        vector_store=mock_vector_store,
        chunker=mock_chunker,
        document_processor=mock_doc_processor,
        registry=registry,
    )


# ─── Preembedded File Ingestion ───────────────────────────────────────────────

class TestPreembeddedIngestion:

    def test_ingest_preembedded_returns_success(self, pipeline):
        result = pipeline.ingest_source("python")
        assert result["success"] is True

    def test_ingest_preembedded_reports_chunk_count(self, pipeline):
        result = pipeline.ingest_source("python")
        assert result["chunk_count"] > 0

    def test_ingest_preembedded_updates_registry_status(self, pipeline, registry):
        pipeline.ingest_source("python")
        src = registry.get_source("python")
        assert src.status == IngestionStatus.COMPLETED

    def test_ingest_preembedded_sets_chunk_count_in_registry(self, pipeline, registry):
        pipeline.ingest_source("python")
        src = registry.get_source("python")
        assert src.chunk_count > 0

    def test_ingest_nonexistent_doc_returns_failure(self, pipeline):
        result = pipeline.ingest_source("nonexistent_doc")
        assert result["success"] is False


# ─── Web Scrape Ingestion (mocked) ────────────────────────────────────────────

class TestWebScrapeIngestion:

    def test_ingest_web_scrape_success(self, pipeline, registry):
        scraped_content = "This is scraped documentation content. " * 50
        with patch.object(pipeline, "_load_web_scrape", return_value=[
            {"content": scraped_content, "title": "MyLib Docs", "technology": "mylib", "source": "web"}
        ]):
            result = pipeline.ingest_source("mylib")
        assert result["success"] is True
        assert result["chunk_count"] > 0

    def test_ingest_web_scrape_failure_sets_failed_status(self, pipeline, registry):
        with patch.object(pipeline, "_load_web_scrape", side_effect=Exception("Network error")):
            result = pipeline.ingest_source("mylib")
        assert result["success"] is False
        src = registry.get_source("mylib")
        assert src.status == IngestionStatus.FAILED


# ─── Remove Source ────────────────────────────────────────────────────────────

class TestRemoveSource:
    def test_remove_after_ingest_resets_registry(self, pipeline, registry):
        pipeline.ingest_source("python")
        pipeline.remove_source("python")
        src = registry.get_source("python")
        assert src.status == IngestionStatus.NOT_STARTED
        assert src.chunk_count == 0

    def test_remove_nonexistent_source_does_not_raise(self, pipeline):
        pipeline.remove_source("nonexistent_source")


# ─── Progress Tracking ────────────────────────────────────────────────────────

class TestIngestionProgress:
    def test_get_progress_before_ingest(self, pipeline):
        progress = pipeline.get_progress("python")
        assert isinstance(progress, dict)
        assert "step" in progress or "status" in progress

    def test_get_progress_after_ingest(self, pipeline):
        pipeline.ingest_source("python")
        progress = pipeline.get_progress("python")
        assert isinstance(progress, dict)


# ─── URL Ingestion ────────────────────────────────────────────────────────────

class TestIngestFromURL:
    def test_ingest_from_url_creates_and_ingests(self, pipeline, registry):
        url = "https://docs.example.com/myframework"
        scraped = "MyFramework documentation content. " * 50

        with patch.object(pipeline, "_load_web_scrape", return_value=[
            {"content": scraped, "title": "MyFramework", "technology": "myframework", "source": "web"}
        ]):
            result = pipeline.ingest_from_url(
                url=url, name="My Framework", doc_id="myframework", category="framework",
            )

        assert result["success"] is True
        src = registry.get_source("myframework")
        assert src is not None
        assert src.status == IngestionStatus.COMPLETED


# ─── Upload Ingestion ─────────────────────────────────────────────────────────

class TestIngestFromUpload:
    def test_ingest_from_upload_bytes(self, pipeline, registry, tmp_path):
        file_content = b"This is my uploaded documentation content. " * 50
        file_path = tmp_path / "my_upload.txt"

        result = pipeline.ingest_from_upload(
            file_path=str(file_path),
            name="My Upload",
            doc_id="my_upload",
            category="tool",
            file_content=file_content,
        )

        assert result["success"] is True
        assert result["chunk_count"] > 0

    def test_ingest_from_upload_updates_registry(self, pipeline, registry, tmp_path):
        file_content = b"Uploaded text. " * 50
        file_path = tmp_path / "upload2.txt"

        pipeline.ingest_from_upload(
            file_path=str(file_path),
            name="Upload2",
            doc_id="upload2",
            category="library",
            file_content=file_content,
        )

        src = registry.get_source("upload2")
        assert src is not None
        assert src.status == IngestionStatus.COMPLETED
