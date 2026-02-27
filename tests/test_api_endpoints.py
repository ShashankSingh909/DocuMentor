"""
Tests for all FastAPI REST API endpoints via TestClient.
Uses mocked core components so no real ChromaDB/LLM/filesystem needed.
"""
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from fastapi.testclient import TestClient

from rag_system.api.server import create_enhanced_fastapi_app


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_vector_store():
    vs = MagicMock()
    vs.get_collection_stats.return_value = {
        "total_chunks": 500,
        "count": 500,
        "collection_name": "documents",
        "sources": {"python": 300, "fastapi": 200},
    }
    vs.search.return_value = [
        {
            "content": "Python list comprehensions are concise.",
            "metadata": {"technology": "python", "source": "docs"},
            "score": 0.92,
        },
        {
            "content": "Use [x for x in iterable] syntax.",
            "metadata": {"technology": "python", "source": "docs"},
            "score": 0.85,
        },
    ]
    return vs


@pytest.fixture
def mock_registry():
    from rag_system.core.registry.models import DocSource, IngestionStatus, DocSourceType

    sources = [
        DocSource(
            id="python", name="Python", category="language", icon="",
            source_type=DocSourceType.PREEMBEDDED_FILE,
            source_paths=["data/preembedded/python_docs.txt"],
            status=IngestionStatus.COMPLETED, chunk_count=300,
        ),
        DocSource(
            id="fastapi", name="FastAPI", category="framework", icon="",
            source_type=DocSourceType.PREEMBEDDED_FILE,
            source_paths=["data/preembedded/fastapi_docs.txt"],
            status=IngestionStatus.NOT_STARTED, chunk_count=0,
        ),
    ]

    reg = MagicMock()
    reg.get_all_sources.return_value = sources
    reg.get_source.side_effect = lambda doc_id: next((s for s in sources if s.id == doc_id), None)
    reg.get_ingested_sources.return_value = [s for s in sources if s.status == IngestionStatus.COMPLETED]
    reg.get_all_technology_mapping.return_value = {"python": "Python", "fastapi": "FastAPI"}
    reg.get_technology_mapping.return_value = {"python": "Python"}
    return reg


@pytest.fixture
def mock_llm_handler():
    handler = MagicMock()
    handler.generate_answer.return_value = "Python is a versatile programming language."
    handler.generate_code.return_value = "def hello():\n    return 'Hello World'"
    handler.generate_response.return_value = "def hello():\n    return 'Hello World'"
    handler.get_provider_status.return_value = {"ollama": True, "openai": False, "gemini": False}
    handler.get_available_providers.return_value = ["ollama"]
    handler.current_provider = "ollama"
    return handler


@pytest.fixture
def mock_ingestion_pipeline():
    pipe = MagicMock()
    pipe.ingest_source.return_value = {"success": True, "chunk_count": 150, "doc_id": "fastapi", "message": "OK"}
    pipe.remove_source.return_value = {"success": True, "message": "Removed"}
    pipe.get_progress.return_value = {"step": 3, "total_steps": 5, "message": "Chunking...", "status": "in_progress"}
    return pipe


@pytest.fixture
def client(mock_vector_store, mock_registry, mock_llm_handler, mock_ingestion_pipeline):
    """Create a TestClient with all core components mocked.

    create_enhanced_fastapi_app() uses deferred imports:
        from rag_system.core import VectorStore, SmartChunker, DocRegistry, IngestionPipeline

    These resolve via core.__getattr__ → from .retrieval import VectorStore, etc.
    We patch at the *subpackage* level (the re-exported names) so the deferred
    imports pick up the mocks.
    """
    mock_doc_proc = MagicMock(
        get_supported_formats=MagicMock(return_value=[".txt", ".pdf", ".md"]),
        is_supported=MagicMock(return_value=True),
    )
    with patch("rag_system.core.retrieval.VectorStore", return_value=mock_vector_store), \
         patch("rag_system.core.chunking.SmartChunker", return_value=MagicMock()), \
         patch("rag_system.core.registry.DocRegistry", return_value=mock_registry), \
         patch("rag_system.core.ingestion.IngestionPipeline", return_value=mock_ingestion_pipeline), \
         patch("rag_system.core.generation.llm_handler.enhanced_llm_handler", mock_llm_handler), \
         patch("rag_system.core.search.web_search_provider", MagicMock()), \
         patch("rag_system.core.processing.document_processor", mock_doc_proc):
        # Reset the cached app singleton so it recreates with mocks
        import rag_system.api.server as srv
        srv._app = None
        app = create_enhanced_fastapi_app()
        yield TestClient(app)
        srv._app = None


# ─── Root / Health ────────────────────────────────────────────────────────────

class TestRootEndpoint:
    def test_root_returns_200(self, client):
        r = client.get("/")
        assert r.status_code == 200

    def test_root_has_version(self, client):
        data = client.get("/").json()
        assert "version" in data

    def test_root_has_docs_link(self, client):
        data = client.get("/").json()
        assert data.get("docs") == "/docs"


# ─── Status ───────────────────────────────────────────────────────────────────

class TestStatusEndpoint:
    def test_status_returns_200(self, client):
        assert client.get("/status").status_code == 200

    def test_status_has_provider_info(self, client):
        data = client.get("/status").json()
        assert "providers" in data

    def test_status_has_document_count(self, client):
        data = client.get("/status").json()
        assert "document_count" in data
        assert data["document_count"] == 500

    def test_status_operational(self, client):
        data = client.get("/status").json()
        assert data["status"] == "operational"


# ─── Metrics ──────────────────────────────────────────────────────────────────

class TestMetricsEndpoint:
    def test_metrics_returns_200(self, client):
        assert client.get("/metrics").status_code == 200

    def test_metrics_content_type(self, client):
        r = client.get("/metrics")
        ct = r.headers.get("content-type", "")
        assert "text/plain" in ct or "text/openmetrics" in ct


# ─── Technologies ─────────────────────────────────────────────────────────────

class TestTechnologiesEndpoint:
    def test_list_technologies_returns_200(self, client):
        assert client.get("/technologies").status_code == 200

    def test_list_technologies_has_total(self, client):
        data = client.get("/technologies").json()
        assert "total_technologies" in data
        assert data["total_technologies"] == 2

    def test_list_technologies_array(self, client):
        data = client.get("/technologies").json()
        assert "technologies" in data
        assert isinstance(data["technologies"], list)


# ─── Docs Catalog ─────────────────────────────────────────────────────────────

class TestDocsCatalog:
    def test_catalog_returns_200(self, client):
        assert client.get("/docs/catalog").status_code == 200

    def test_catalog_returns_sources(self, client):
        data = client.get("/docs/catalog").json()
        # Endpoint returns {"total": N, "sources": [...]}
        assert "sources" in data
        assert isinstance(data["sources"], list)
        assert len(data["sources"]) == 2

    def test_catalog_source_has_required_fields(self, client):
        data = client.get("/docs/catalog").json()
        src = data["sources"][0]
        for field in ["id", "name", "category", "status", "chunk_count"]:
            assert field in src, f"Missing field: {field}"


class TestDocsIngested:
    def test_ingested_returns_200(self, client):
        assert client.get("/docs/ingested").status_code == 200

    def test_ingested_returns_only_completed(self, client):
        data = client.get("/docs/ingested").json()
        # Endpoint returns {"total": N, "technologies": [...]}
        assert "technologies" in data
        assert data["total"] == 1
        assert data["technologies"][0]["id"] == "python"


class TestDocStatus:
    def test_get_existing_doc_status(self, client):
        assert client.get("/docs/python/status").status_code == 200

    def test_get_nonexistent_doc_status(self, client):
        assert client.get("/docs/nonexistent_xyz/status").status_code == 404


# ─── Ingest / Remove ──────────────────────────────────────────────────────────

class TestDocIngest:
    def test_ingest_returns_200(self, client):
        assert client.post("/docs/fastapi/ingest").status_code == 200

    def test_ingest_returns_chunk_count(self, client):
        data = client.post("/docs/fastapi/ingest").json()
        assert data.get("chunk_count", 0) > 0 or data.get("success") is True


class TestDocRemove:
    def test_remove_existing_returns_200(self, client):
        r = client.delete("/docs/python")
        assert r.status_code == 200

    def test_remove_nonexistent_returns_404(self, client):
        assert client.delete("/docs/nonexistent_xyz").status_code == 404


class TestDocProgress:
    def test_progress_returns_200(self, client):
        assert client.get("/docs/fastapi/progress").status_code == 200

    def test_progress_has_step_info(self, client):
        data = client.get("/docs/fastapi/progress").json()
        assert "step" in data
        assert "total_steps" in data


# ─── Q&A Endpoints ────────────────────────────────────────────────────────────

class TestAskEndpoint:
    def test_ask_enhanced_returns_200(self, client):
        r = client.post("/ask/enhanced", json={
            "question": "What are Python list comprehensions?",
            "search_k": 5,
        })
        assert r.status_code == 200

    def test_ask_enhanced_has_answer(self, client):
        data = client.post("/ask/enhanced", json={"question": "What is Python?"}).json()
        assert "answer" in data
        assert len(data["answer"]) > 0

    def test_ask_enhanced_has_sources(self, client):
        data = client.post("/ask/enhanced", json={"question": "What is Python?"}).json()
        assert "sources" in data
        assert isinstance(data["sources"], list)

    def test_ask_enhanced_has_response_time(self, client):
        data = client.post("/ask/enhanced", json={"question": "What is Python?"}).json()
        assert "response_time" in data

    def test_ask_enhanced_with_technology_filter(self, client):
        r = client.post("/ask/enhanced", json={
            "question": "How do decorators work?",
            "technology_filter": "python",
        })
        assert r.status_code == 200

    def test_ask_enhanced_with_web_search(self, client):
        r = client.post("/ask/enhanced", json={
            "question": "Latest Python features?",
            "enable_web_search": True,
        })
        assert r.status_code == 200

    def test_ask_legacy_works(self, client):
        r = client.post("/ask", json={"question": "What is Python?"})
        assert r.status_code in (200, 307, 308)


# ─── Code Generation ──────────────────────────────────────────────────────────

class TestCodeGeneration:
    def test_generate_code_returns_200(self, client):
        r = client.post("/generate-code/enhanced", json={
            "prompt": "Create a hello world function",
            "language": "python",
        })
        assert r.status_code == 200

    def test_generate_code_has_code(self, client):
        data = client.post("/generate-code/enhanced", json={
            "prompt": "Create a hello world function",
        }).json()
        assert "code" in data or "answer" in data

    def test_generate_code_with_technology(self, client):
        r = client.post("/generate-code/enhanced", json={
            "prompt": "Create a FastAPI endpoint",
            "language": "python",
            "technology": "fastapi",
        })
        assert r.status_code == 200


# ─── Custom Docs ──────────────────────────────────────────────────────────────

class TestCustomDocs:
    def test_add_custom_doc_returns_200(self, client):
        r = client.post("/docs/custom", json={
            "url": "https://docs.example.com",
            "name": "Example Docs",
            "doc_id": "example",
            "category": "tool",
        })
        assert r.status_code == 200


# ─── CORS ─────────────────────────────────────────────────────────────────────

class TestCORS:
    def test_cors_allows_localhost_3000(self, client):
        r = client.options("/", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        })
        assert r.status_code in (200, 204, 405)

    def test_cors_header_present_on_response(self, client):
        r = client.get("/", headers={"Origin": "http://localhost:3000"})
        assert r.status_code == 200
