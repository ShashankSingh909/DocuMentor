"""
Tests for DocRegistry — catalog loading, status management, custom sources, persistence.
"""
import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from rag_system.core.registry.models import DocSource, IngestionStatus, DocSourceType
from rag_system.core.registry.registry import DocRegistry
from rag_system.config.settings import get_settings


# ─── Helper ──────────────────────────────────────────────────────────────────

def _make_registry(catalog_path: str, state_path: str) -> DocRegistry:
    """Create a DocRegistry with patched settings pointing to temp paths."""
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


# ─── Model Tests ─────────────────────────────────────────────────────────────

class TestDocSourceModel:
    """Tests for the DocSource Pydantic model."""

    def test_default_status_is_not_started(self, sample_catalog_data):
        src = DocSource(**{**sample_catalog_data[0], "source_paths": ["path/to/file"]})
        assert src.status == IngestionStatus.NOT_STARTED

    def test_default_chunk_count_zero(self, sample_catalog_data):
        src = DocSource(**{**sample_catalog_data[0], "source_paths": ["path/to/file"]})
        assert src.chunk_count == 0

    def test_optional_fields_default_none(self, sample_catalog_data):
        src = DocSource(**{**sample_catalog_data[0], "source_paths": ["path/to/file"]})
        assert src.last_ingested is None
        assert src.error_message is None

    def test_source_type_enum_values(self):
        assert DocSourceType.PREEMBEDDED_FILE == "preembedded_file"
        assert DocSourceType.SCRAPED_JSON == "scraped_json"
        assert DocSourceType.WEB_SCRAPE == "web_scrape"
        assert DocSourceType.FILE_UPLOAD == "file_upload"

    def test_ingestion_status_enum_values(self):
        assert IngestionStatus.NOT_STARTED == "not_started"
        assert IngestionStatus.IN_PROGRESS == "in_progress"
        assert IngestionStatus.COMPLETED == "completed"
        assert IngestionStatus.FAILED == "failed"


# ─── Registry Initialization ──────────────────────────────────────────────────

class TestDocRegistryInit:

    def test_loads_catalog_from_json(self, temp_catalog_file, temp_state_file):
        reg = _make_registry(str(temp_catalog_file), str(temp_state_file))
        sources = reg.get_all_sources()
        assert len(sources) == 2
        ids = [s.id for s in sources]
        assert "python" in ids
        assert "fastapi" in ids

    def test_all_sources_default_not_started(self, temp_catalog_file, temp_state_file):
        reg = _make_registry(str(temp_catalog_file), str(temp_state_file))
        for src in reg.get_all_sources():
            assert src.status == IngestionStatus.NOT_STARTED

    def test_missing_catalog_loads_empty(self, temp_dir):
        reg = _make_registry(str(temp_dir / "nonexistent.json"), str(temp_dir / "state.json"))
        assert len(reg.get_all_sources()) == 0

    def test_state_file_created_on_update(self, temp_catalog_file, temp_state_file):
        reg = _make_registry(str(temp_catalog_file), str(temp_state_file))
        reg.update_status("python", IngestionStatus.COMPLETED, chunk_count=100)
        assert temp_state_file.exists()
        data = json.loads(temp_state_file.read_text(encoding="utf-8"))
        assert isinstance(data, dict)


# ─── Registry CRUD ────────────────────────────────────────────────────────────

class TestDocRegistryCRUD:

    @pytest.fixture
    def registry(self, temp_catalog_file, temp_state_file):
        return _make_registry(str(temp_catalog_file), str(temp_state_file))

    def test_get_source_by_id(self, registry):
        src = registry.get_source("python")
        assert src is not None
        assert src.id == "python"
        assert src.name == "Python"

    def test_get_nonexistent_source_returns_none(self, registry):
        assert registry.get_source("nonexistent_id") is None

    def test_update_status_to_completed(self, registry):
        registry.update_status("python", IngestionStatus.COMPLETED, chunk_count=500)
        src = registry.get_source("python")
        assert src.status == IngestionStatus.COMPLETED
        assert src.chunk_count == 500

    def test_update_status_to_failed_with_error(self, registry):
        registry.update_status("python", IngestionStatus.FAILED, error_message="Connection error")
        src = registry.get_source("python")
        assert src.status == IngestionStatus.FAILED
        assert src.error_message == "Connection error"

    def test_update_status_to_in_progress(self, registry):
        registry.update_status("fastapi", IngestionStatus.IN_PROGRESS)
        src = registry.get_source("fastapi")
        assert src.status == IngestionStatus.IN_PROGRESS

    def test_remove_source_resets_to_not_started(self, registry):
        registry.update_status("python", IngestionStatus.COMPLETED, chunk_count=300)
        registry.remove_source("python")
        src = registry.get_source("python")
        assert src.status == IngestionStatus.NOT_STARTED
        assert src.chunk_count == 0

    def test_remove_nonexistent_source_doesnt_raise(self, registry):
        registry.remove_source("nonexistent_id")

    def test_get_ingested_sources_empty_initially(self, registry):
        assert registry.get_ingested_sources() == []

    def test_get_ingested_sources_after_completion(self, registry):
        registry.update_status("python", IngestionStatus.COMPLETED, chunk_count=100)
        registry.update_status("fastapi", IngestionStatus.FAILED)
        ingested = registry.get_ingested_sources()
        assert len(ingested) == 1
        assert ingested[0].id == "python"


# ─── Custom Sources ───────────────────────────────────────────────────────────

class TestDocRegistryCustomSources:

    @pytest.fixture
    def registry(self, temp_catalog_file, temp_state_file):
        return _make_registry(str(temp_catalog_file), str(temp_state_file))

    def test_add_custom_source(self, registry):
        registry.add_custom_source(
            doc_id="my_lib", name="My Library", category="library",
            source_type=DocSourceType.WEB_SCRAPE,
            source_paths=["https://mylib.example.com/docs"],
        )
        src = registry.get_source("my_lib")
        assert src is not None
        assert src.name == "My Library"
        assert src.status == IngestionStatus.NOT_STARTED

    def test_add_custom_source_appears_in_all_sources(self, registry):
        initial_count = len(registry.get_all_sources())
        registry.add_custom_source("new_doc", "New Doc", "tool", DocSourceType.FILE_UPLOAD, [])
        assert len(registry.get_all_sources()) == initial_count + 1

    def test_duplicate_custom_source_id_overwrites(self, registry):
        registry.add_custom_source("unique_doc", "Unique", "tool", DocSourceType.FILE_UPLOAD, [])
        registry.add_custom_source("unique_doc", "Duplicate", "tool", DocSourceType.FILE_UPLOAD, [])
        src = registry.get_source("unique_doc")
        assert src.name == "Duplicate"


# ─── Technology Mapping ───────────────────────────────────────────────────────

class TestTechnologyMapping:

    @pytest.fixture
    def registry(self, temp_catalog_file, temp_state_file):
        return _make_registry(str(temp_catalog_file), str(temp_state_file))

    def test_technology_mapping_contains_all_sources(self, registry):
        mapping = registry.get_all_technology_mapping()
        assert "python" in mapping
        assert "fastapi" in mapping

    def test_technology_mapping_values_are_names(self, registry):
        mapping = registry.get_all_technology_mapping()
        assert mapping["python"] == "Python"
        assert mapping["fastapi"] == "FastAPI"

    def test_get_ingested_mapping_empty_initially(self, registry):
        assert registry.get_technology_mapping() == {}

    def test_get_ingested_mapping_after_ingest(self, registry):
        registry.update_status("python", IngestionStatus.COMPLETED, chunk_count=100)
        mapping = registry.get_technology_mapping()
        assert "python" in mapping
        assert "fastapi" not in mapping


# ─── State Persistence ────────────────────────────────────────────────────────

class TestRegistryPersistence:

    def test_state_persists_across_instances(self, temp_catalog_file, temp_state_file):
        reg1 = _make_registry(str(temp_catalog_file), str(temp_state_file))
        reg1.update_status("python", IngestionStatus.COMPLETED, chunk_count=999)

        reg2 = _make_registry(str(temp_catalog_file), str(temp_state_file))
        src = reg2.get_source("python")
        assert src.status == IngestionStatus.COMPLETED
        assert src.chunk_count == 999
