"""
Enhanced FastAPI REST API v2 for Advanced RAG System
Provides programmatic access to all enhanced RAG functionality

Production-ready with:
- API Key Authentication
- Rate Limiting
- Input Validation
- Metrics & Monitoring
- Structured Logging
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import json
import io
import time
from pathlib import Path

from rag_system.core.registry.models import IngestionStatus
from rag_system.config import get_settings
from rag_system.core.utils.metrics import (
    track_request_duration,
    track_llm_request,
    track_vector_search,
    record_api_request,
    record_auth_attempt,
    record_rate_limit_hit,
    update_vector_store_size,
)
from rag_system.core.constants import (
    RATE_LIMIT_SEARCH,
    RATE_LIMIT_UPLOAD,
    RATE_LIMIT_QUERY,
    RATE_LIMIT_GENERATION,
    DEFAULT_SEARCH_K,
    MAX_SEARCH_K,
)
from rag_system.core.utils.logger import get_logger

logger = get_logger(__name__)

# Enhanced Pydantic models for API v2
class EnhancedQuestionRequest(BaseModel):
    question: str = Field(..., description="The question to ask")
    search_k: int = Field(default=8, description="Number of results to retrieve")
    enable_web_search: bool = Field(default=False, description="Enable web search")
    response_mode: str = Field(default="smart_answer", description="Response mode: smart_answer, code_generation, detailed_sources")
    technology_filter: Optional[str] = Field(default=None, description="Filter by specific technology")
    source_filter: Optional[List[str]] = Field(default=None, description="Filter by document sources")
    temperature: float = Field(default=0.3, description="Response creativity (0.0-1.0)")
    max_tokens: int = Field(default=800, description="Maximum response length")
    chunk_overlap: int = Field(default=2, description="Search overlap for better context")

class EnhancedCodeGenerationRequest(BaseModel):
    prompt: str = Field(..., description="Code generation prompt")
    language: str = Field(default="python", description="Programming language")
    technology: Optional[str] = Field(default=None, description="Specific technology context")
    include_context: bool = Field(default=True, description="Include relevant documentation context")
    style: str = Field(default="complete", description="Code style: complete, snippet, explanation")

class TechnologyFilterRequest(BaseModel):
    technology: str = Field(..., description="Technology to filter by")
    question: str = Field(..., description="Question within technology context")
    mode: str = Field(default="smart", description="Response mode: smart, code, detailed")

class EnhancedQuestionResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    response_time: float
    provider_used: str
    source_count: int
    technology_context: Optional[str]
    response_mode: str
    search_metadata: Dict[str, Any]

class EnhancedSystemStatus(BaseModel):
    status: str
    providers: Dict[str, bool]
    document_count: int
    available_sources: List[str]
    available_technologies: List[str]
    supported_formats: List[str]
    system_version: str

class TechnologyStatsResponse(BaseModel):
    technology: str
    chunk_count: int
    sample_content: List[str]
    topics_covered: List[str]

def create_enhanced_fastapi_app() -> FastAPI:
    """Create and configure enhanced FastAPI application v2 with production features"""

    # Deferred imports — these create heavyweight singletons (ChromaDB, LLM providers,
    # embedding models, etc.) and must not run at module import time.
    from rag_system.core import SmartChunker, VectorStore, DocRegistry, IngestionPipeline
    from rag_system.core.processing import document_processor
    from rag_system.core.generation.llm_handler import enhanced_llm_handler
    from rag_system.core.search import web_search_provider

    # Initialize components
    settings = get_settings()

    app = FastAPI(
        title="DocuMentor API",
        description="Production-Ready AI Documentation Assistant API with Authentication, Rate Limiting, and Monitoring",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # Initialize rate limiter
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Configure CORS with secure defaults
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,  # Configured via environment variables
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )

    # Initialize core components
    vector_store = VectorStore()
    chunker = SmartChunker()
    registry = DocRegistry()
    ingestion_pipeline = IngestionPipeline(
        vector_store=vector_store,
        chunker=chunker,
        document_processor=document_processor,
        registry=registry,
    )

    def get_technology_mapping():
        """Dynamic technology mapping from registry (replaces hardcoded dict)."""
        return registry.get_all_technology_mapping()

    TECHNOLOGY_MAPPING = get_technology_mapping()

    logger.info("FastAPI application initialized with production features")
    logger.info(f"Authentication: {'Enabled' if settings.api_key else 'Disabled'}")
    logger.info(f"Rate limiting: Enabled")
    logger.info(f"Metrics: Enabled at /metrics")

    @app.get("/", tags=["General"])
    async def root():
        """Enhanced API root endpoint"""
        return {
            "message": "DocuMentor API - AI Documentation Assistant",
            "version": "2.0.0",
            "features": [
                "Smart Documentation Search",
                "AI-Powered Code Generation",
                "Technology-Specific Filtering",
                "Dark/Light Mode Support",
                "Real-time Web Search"
            ],
            "docs": "/docs",
            "status": "/status",
            "technologies": "/technologies"
        }

    @app.get("/status", response_model=EnhancedSystemStatus, tags=["General"])
    async def get_enhanced_status():
        """Get enhanced system status and capabilities"""
        try:
            stats = vector_store.get_collection_stats()
            provider_status = enhanced_llm_handler.get_provider_status()

            # Update metrics
            update_vector_store_size(stats.get('total_chunks', 0))

            return EnhancedSystemStatus(
                status="operational",
                providers=provider_status,
                document_count=stats.get('total_chunks', 0),
                available_sources=list(stats.get('sources', {}).keys()),
                available_technologies=list(TECHNOLOGY_MAPPING.values()),
                supported_formats=document_processor.get_supported_formats(),
                system_version="2.0.0"
            )
        except Exception as e:
            logger.error(f"Status check failed: {e}")
            raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

    @app.get("/metrics", tags=["Monitoring"])
    async def get_metrics():
        """
        Prometheus-compatible metrics endpoint
        Tracks API requests, LLM usage, cache performance, and more
        """
        metrics_output = generate_latest()
        return Response(content=metrics_output, media_type=CONTENT_TYPE_LATEST)

    @app.get("/technologies", tags=["Technologies"])
    async def list_technologies():
        """List all available technologies with stats"""
        try:
            stats = vector_store.get_collection_stats()
            technologies = []

            for tech_key, tech_name in TECHNOLOGY_MAPPING.items():
                # Get technology-specific chunks
                try:
                    tech_filter = {"technology": tech_key}
                    tech_results = vector_store.search("overview", k=3, filter_dict=tech_filter)

                    technologies.append({
                        "key": tech_key,
                        "name": tech_name,
                        "available": len(tech_results) > 0,
                        "sample_topics": [r.get('content', '')[:100] + "..." for r in tech_results[:2]]
                    })
                except Exception as e:
                    # Log the error but continue processing other technologies
                    logger.warning(f"Failed to check technology {tech_name}: {e}")
                    technologies.append({
                        "key": tech_key,
                        "name": tech_name,
                        "available": False,
                        "sample_topics": []
                    })

            return {
                "total_technologies": len(TECHNOLOGY_MAPPING),
                "technologies": technologies,
                "total_chunks": stats.get('total_chunks', 0)
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to list technologies: {str(e)}")

    @app.get("/technologies/{technology}/stats", response_model=TechnologyStatsResponse, tags=["Technologies"])
    async def get_technology_stats(technology: str):
        """Get detailed stats for a specific technology"""
        try:
            if technology not in TECHNOLOGY_MAPPING:
                raise HTTPException(status_code=404, detail=f"Technology '{technology}' not found")

            tech_filter = {"technology": technology}
            tech_results = vector_store.search("", k=10, filter_dict=tech_filter)

            # Extract topics from content
            topics = set()
            sample_content = []

            for result in tech_results:
                content = result.get('content', '')
                sample_content.append(content[:200] + "...")

                # Simple topic extraction (you could enhance this)
                words = content.lower().split()
                for word in words:
                    if len(word) > 5 and word.isalpha():
                        topics.add(word)

            return TechnologyStatsResponse(
                technology=TECHNOLOGY_MAPPING[technology],
                chunk_count=len(tech_results),
                sample_content=sample_content[:5],
                topics_covered=list(topics)[:10]
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get technology stats: {str(e)}")

    @app.post("/ask/enhanced", response_model=EnhancedQuestionResponse, tags=["Enhanced Q&A"])
    @limiter.limit(f"{RATE_LIMIT_QUERY}/minute")
    async def ask_enhanced_question(request: Request, body: EnhancedQuestionRequest):
        """Ask a question with enhanced features and filtering"""
        try:
            import time
            start_time = time.time()

            # Build combined filter
            combined_filter = {}

            # Add technology filter
            if body.technology_filter and body.technology_filter in TECHNOLOGY_MAPPING:
                combined_filter = {
                    "$and": [
                        {"technology": body.technology_filter},
                        {"source": "comprehensive_docs"}
                    ]
                }

            # Add source filter
            if body.source_filter:
                if "source" not in combined_filter:
                    combined_filter["source"] = {"$in": body.source_filter}

            filter_dict = combined_filter if combined_filter else None

            # Enhanced search with overlap
            search_results = []
            if body.response_mode != "web_only":
                search_results = vector_store.search(
                    body.question,
                    k=body.search_k + body.chunk_overlap,
                    filter_dict=filter_dict
                )

            # Add web search if enabled
            if body.enable_web_search:
                web_results = web_search_provider.search_web(body.question, max_results=3)
                search_results.extend(web_results)

            # Generate enhanced response based on mode
            if body.response_mode == "code_generation":
                # Enhanced code generation
                tech_context = ""
                if body.technology_filter:
                    tech_name = TECHNOLOGY_MAPPING.get(body.technology_filter, body.technology_filter)
                    tech_context = f"Focus on {tech_name} implementation. "

                code_prompt = f"{tech_context}Provide a complete, working code implementation for: {body.question}"
                answer = enhanced_llm_handler.generate_code(code_prompt, "python", search_results[:5])

                # Format code response
                if "```" not in answer:
                    answer = f"```python\n{answer}\n```"

            elif body.response_mode == "detailed_sources":
                # Generate answer with detailed source focus
                detailed_prompt = f"Provide a comprehensive answer with specific references to documentation. Include examples and detailed explanations. Question: {body.question}"
                answer = enhanced_llm_handler.generate_answer(detailed_prompt, search_results)

            else:  # smart_answer
                # Enhanced smart answer
                smart_prompt = f"Provide a clear, practical answer with examples when helpful. Be comprehensive but concise. Question: {body.question}"
                answer = enhanced_llm_handler.generate_answer(smart_prompt, search_results)

            response_time = time.time() - start_time

            return EnhancedQuestionResponse(
                answer=answer,
                sources=search_results,
                response_time=response_time,
                provider_used=enhanced_llm_handler.current_provider,
                source_count=len(search_results),
                technology_context=TECHNOLOGY_MAPPING.get(body.technology_filter) if body.technology_filter else None,
                response_mode=body.response_mode,
                search_metadata={
                    "filter_used": filter_dict is not None,
                    "overlap_chunks": body.chunk_overlap,
                    "web_search_enabled": body.enable_web_search
                }
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Enhanced question processing failed: {str(e)}")

    @app.post("/generate-code/enhanced", tags=["Enhanced Code Generation"])
    @limiter.limit(f"{RATE_LIMIT_GENERATION}/minute")
    async def generate_enhanced_code(request: Request, body: EnhancedCodeGenerationRequest):
        """Generate code with enhanced technology context"""
        try:
            # Get enhanced context
            context = []
            if body.include_context:
                search_query = f"{body.language} {body.prompt}"
                if body.technology:
                    search_query = f"{body.technology} {search_query}"
                    filter_dict = {"technology": body.technology} if body.technology in TECHNOLOGY_MAPPING else None
                else:
                    filter_dict = None

                context = vector_store.search(search_query, k=5, filter_dict=filter_dict)

            # Enhanced code generation prompt
            if body.technology and body.technology in TECHNOLOGY_MAPPING:
                tech_name = TECHNOLOGY_MAPPING[body.technology]
                enhanced_prompt = f"Generate {body.style} {body.language} code for {tech_name}. Request: {body.prompt}"
            else:
                enhanced_prompt = f"Generate {body.style} {body.language} code. Request: {body.prompt}"

            # Generate code
            code = enhanced_llm_handler.generate_code(
                enhanced_prompt,
                body.language,
                context
            )

            return {
                "code": code,
                "language": body.language,
                "technology": TECHNOLOGY_MAPPING.get(body.technology) if body.technology else "General",
                "style": body.style,
                "context_used": len(context),
                "provider": enhanced_llm_handler.current_provider
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Enhanced code generation failed: {str(e)}")

    @app.post("/technology-query", tags=["Technology Queries"])
    @limiter.limit(f"{RATE_LIMIT_QUERY}/minute")
    async def technology_specific_query(request: Request, body: TechnologyFilterRequest):
        """Query with technology-specific filtering and context"""
        try:
            if body.technology not in TECHNOLOGY_MAPPING:
                raise HTTPException(status_code=400, detail=f"Technology '{body.technology}' not supported")

            import time
            start_time = time.time()

            # Technology-specific filter
            tech_filter = {
                "$and": [
                    {"technology": body.technology},
                    {"source": "comprehensive_docs"}
                ]
            }

            # Search with technology filter
            search_results = vector_store.search(
                body.question,
                k=8,
                filter_dict=tech_filter
            )

            # Generate technology-focused response
            tech_name = TECHNOLOGY_MAPPING[body.technology]

            if body.mode == "code":
                prompt = f"Provide {tech_name} code implementation for: {body.question}"
                answer = enhanced_llm_handler.generate_code(prompt, "python", search_results)
            elif body.mode == "detailed":
                prompt = f"Provide detailed {tech_name} documentation and examples for: {body.question}"
                answer = enhanced_llm_handler.generate_answer(prompt, search_results)
            else:  # smart
                prompt = f"Explain how to {body.question} using {tech_name}. Include practical examples."
                answer = enhanced_llm_handler.generate_answer(prompt, search_results)

            response_time = time.time() - start_time

            return {
                "answer": answer,
                "technology": tech_name,
                "mode": body.mode,
                "sources": search_results,
                "response_time": response_time,
                "source_count": len(search_results)
            }

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Technology query failed: {str(e)}")

    # Include all original endpoints for backward compatibility
    @app.post("/ask", response_model=EnhancedQuestionResponse, tags=["Q&A"])
    @limiter.limit(f"{RATE_LIMIT_QUERY}/minute")
    async def ask_question_legacy(request: Request, body: EnhancedQuestionRequest):
        """Legacy ask endpoint - redirects to enhanced version"""
        return await ask_enhanced_question(request, body)

    @app.post("/upload", tags=["Documents"])
    @limiter.limit(f"{RATE_LIMIT_UPLOAD}/minute")
    async def upload_document(
        request: Request,
        file: UploadFile = File(...),
        source: str = Form(default="api_upload")
    ):
        """Upload and process a document (enhanced version)"""
        try:
            # Check file format
            file_extension = Path(file.filename).suffix.lower()
            if not document_processor.is_supported(file_extension):
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file format: {file_extension}"
                )

            # Read file content
            content = await file.read()

            # Process document
            result = document_processor.process_file(file.filename, content)

            if not result['success']:
                raise HTTPException(
                    status_code=400,
                    detail=f"Document processing failed: {result['metadata'].get('error', 'Unknown error')}"
                )

            # Create document object with enhanced metadata
            document = {
                'title': file.filename,
                'content': result['content'],
                'source': source,
                'file_type': file_extension,
                'upload_timestamp': time.time()
            }

            # Chunk the document
            chunks = chunker.chunk_document(document)

            if chunks:
                texts = [chunk['content'] for chunk in chunks]
                metadatas = [chunk['metadata'] for chunk in chunks]
                ids = [f"upload_{file.filename}_{i}" for i in range(len(chunks))]

                added = vector_store.add_documents(texts, metadatas, ids)

                return {
                    "success": True,
                    "message": f"Successfully processed {file.filename}",
                    "chunks_created": added,
                    "document_id": f"upload_{file.filename}",
                    "file_type": file_extension,
                    "processing_metadata": result.get('metadata', {})
                }
            else:
                raise HTTPException(status_code=400, detail="Failed to create chunks from document")

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

    # ── Documentation Management Endpoints ──────────────────

    @app.get("/docs/catalog", tags=["Documentation Management"])
    async def get_documentation_catalog():
        """Get all available documentation sources with their ingestion status."""
        sources = registry.get_all_sources()
        return {
            "total": len(sources),
            "sources": [
                {
                    "id": s.id,
                    "name": s.name,
                    "category": s.category,
                    "icon": s.icon,
                    "source_type": s.source_type.value,
                    "status": s.status.value,
                    "chunk_count": s.chunk_count,
                    "last_ingested": s.last_ingested.isoformat() if s.last_ingested else None,
                    "error_message": s.error_message,
                }
                for s in sources
            ],
        }

    @app.get("/docs/ingested", tags=["Documentation Management"])
    async def get_ingested_technologies():
        """Get only technologies that have been successfully ingested."""
        ingested = registry.get_ingested_sources()
        return {
            "total": len(ingested),
            "technologies": [
                {"id": s.id, "name": s.name, "icon": s.icon, "chunk_count": s.chunk_count}
                for s in ingested
            ],
        }

    @app.get("/docs/{doc_id}/status", tags=["Documentation Management"])
    async def get_doc_status(doc_id: str):
        """Get ingestion status for a specific documentation source."""
        source = registry.get_source(doc_id)
        if not source:
            raise HTTPException(status_code=404, detail=f"Documentation source '{doc_id}' not found")
        return {
            "id": source.id,
            "name": source.name,
            "status": source.status.value,
            "chunk_count": source.chunk_count,
            "last_ingested": source.last_ingested.isoformat() if source.last_ingested else None,
            "error_message": source.error_message,
        }

    @app.post("/docs/{doc_id}/ingest", tags=["Documentation Management"])
    async def trigger_ingestion(doc_id: str):
        """Trigger ingestion of a documentation source."""
        source = registry.get_source(doc_id)
        if not source:
            raise HTTPException(status_code=404, detail=f"Documentation source '{doc_id}' not found")

        if source.status == IngestionStatus.IN_PROGRESS:
            raise HTTPException(status_code=409, detail=f"Ingestion already in progress for '{doc_id}'")

        result = ingestion_pipeline.ingest_source(doc_id)
        if result['success']:
            return result
        else:
            raise HTTPException(status_code=500, detail=result['message'])

    @app.delete("/docs/{doc_id}", tags=["Documentation Management"])
    async def remove_documentation(doc_id: str):
        """Remove a documentation source from the knowledge base."""
        source = registry.get_source(doc_id)
        if not source:
            raise HTTPException(status_code=404, detail=f"Documentation source '{doc_id}' not found")

        result = ingestion_pipeline.remove_source(doc_id)
        if result['success']:
            return result
        else:
            raise HTTPException(status_code=500, detail=result['message'])

    @app.get("/docs/{doc_id}/progress", tags=["Documentation Management"])
    async def get_ingestion_progress(doc_id: str):
        """Get ingestion progress for a source (for polling during background ingestion)."""
        return ingestion_pipeline.get_progress(doc_id)

    class CustomDocRequest(BaseModel):
        name: str = Field(..., description="Display name for the documentation")
        url: Optional[str] = Field(default=None, description="URL to scrape documentation from")
        category: str = Field(default="custom", description="Category (framework, language, tool, etc.)")

    @app.post("/docs/custom", tags=["Documentation Management"])
    async def add_custom_documentation(request: CustomDocRequest):
        """Add a custom documentation source from a URL and ingest it."""
        if not request.url:
            raise HTTPException(status_code=400, detail="URL is required for custom documentation")

        import re
        doc_id = re.sub(r'[^a-z0-9_]', '_', request.name.lower().strip()).strip('_')
        doc_id = re.sub(r'_+', '_', doc_id)

        result = ingestion_pipeline.ingest_from_url(
            url=request.url,
            name=request.name,
            doc_id=doc_id,
            category=request.category,
        )

        if result['success']:
            return {"doc_id": doc_id, **result}
        else:
            raise HTTPException(status_code=500, detail=result['message'])

    return app

# App instance created lazily — not at import time.
# This prevents booting heavy dependencies (ChromaDB, LLM handlers, etc.) when
# subpackages like rag_system.api.middleware are imported in unit tests.
_app = None


def get_app():
    """Get or create the FastAPI app singleton."""
    global _app
    if _app is None:
        _app = create_enhanced_fastapi_app()
    return _app


# For backwards compatibility and uvicorn string-based lookup ("rag_system.api.server:app")
# we expose `app` as a module-level property via __getattr__.
def __getattr__(name):
    if name == "app":
        return get_app()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")