"""
Core RAG System Components

Uses lazy imports to avoid creating heavyweight singletons (ChromaDB, LLM
handlers, embedding models, document processor) when subpackages like
rag_system.core.registry.models are imported for type-only use.
"""

__all__ = [
    'SmartChunker',
    'LLMHandler',
    'VectorStore',
    'get_logger',
    'ResponseCache',
    'EmbeddingCache',
    'DocRegistry',
    'IngestionPipeline',
]


def __getattr__(name):
    """Lazy-load heavy components on first access."""
    if name == 'SmartChunker':
        from .chunking import SmartChunker
        return SmartChunker
    if name == 'LLMHandler':
        from .generation import LLMHandler
        return LLMHandler
    if name == 'VectorStore':
        from .retrieval import VectorStore
        return VectorStore
    if name in ('get_logger', 'ResponseCache', 'EmbeddingCache'):
        from .utils import get_logger, ResponseCache, EmbeddingCache
        return {'get_logger': get_logger, 'ResponseCache': ResponseCache, 'EmbeddingCache': EmbeddingCache}[name]
    if name == 'DocRegistry':
        from .registry import DocRegistry
        return DocRegistry
    if name == 'IngestionPipeline':
        from .ingestion import IngestionPipeline
        return IngestionPipeline
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
