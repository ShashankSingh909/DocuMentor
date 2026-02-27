"""
Configuration Management for DocuMentor
Using Pydantic for settings - it's pretty nice for validation and env vars
"""

from typing import List, Optional
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """App settings - loads from .env file automatically"""

    # Application Info
    app_name: str = Field(default="RAG System", description="Application name")
    app_version: str = Field(default="2.0.0", description="Application version")

    # Server Configuration
    host: str = Field(default="127.0.0.1", description="Server host")
    port: int = Field(default=8501, description="Server port")
    debug: bool = Field(default=False, description="Debug mode - don't use in production!")

    @field_validator("debug", mode="before")
    @classmethod
    def coerce_debug(cls, v):
        """Handle non-boolean DEBUG env values (e.g. 'release') gracefully."""
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes")
        return bool(v)

    # CORS Configuration
    # added common dev ports here
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8501", "http://127.0.0.1:8501", "http://127.0.0.1:8506"],
        description="Allowed CORS origins (use ['*'] only for development)"
    )
    api_key: Optional[str] = Field(default=None, description="API key for authentication - set this in production!")

    # Ollama Configuration
    ollama_host: str = Field(default="localhost:11434", description="Ollama server host")
    ollama_model: str = Field(default="gemma2:2b", description="gemma2:2b is fast and good enough for most things")
    ollama_timeout: int = Field(default=120, description="Ollama can be slow, so generous timeout")

    # Vector Database Configuration
    vectordb_path: str = Field(default="./data/vectordb", description="Vector database path")
    chroma_persist_directory: str = Field(default="./data/chroma_db", description="ChromaDB persist directory")
    collection_name: str = Field(default="documents", description="Collection name")
    embedding_model: str = Field(default="all-MiniLM-L6-v2", description="Good balance of speed and quality")
    embedding_dimension: int = Field(default=384, description="Dimension for all-MiniLM-L6-v2")

    # Chunking Configuration
    # these values worked well in testing
    chunk_size: int = Field(default=1000, description="Default chunk size in chars")
    chunk_overlap: int = Field(default=200, description="Chunk overlap - helps with context")
    max_chunks_per_doc: int = Field(default=1000, description="Safety limit per document")

    # Caching Configuration
    cache_dir: str = Field(default="./data/cache", description="Cache directory")
    embedding_cache_dir: str = Field(default="./data/cache/embeddings", description="Embedding cache directory")
    max_cache_size: int = Field(default=1000, description="Maximum cache entries")
    cache_ttl: int = Field(default=3600, description="Cache TTL in seconds")

    # Performance Configuration
    max_workers: int = Field(default=4, description="Maximum worker threads")
    batch_size: int = Field(default=100, description="Default batch size")
    timeout: int = Field(default=30, description="Default timeout")

    # File Upload Configuration
    upload_dir: str = Field(default="./data/uploads", description="Upload directory")
    max_file_size: int = Field(default=50 * 1024 * 1024, description="Max file size in bytes")
    allowed_extensions: List[str] = Field(
        default=[".txt", ".md", ".pdf", ".docx", ".csv", ".doc", ".rtf", ".odt", ".pptx", ".xlsx"],
        description="Allowed file extensions"
    )

    # External API Configuration
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    gemini_api_key: Optional[str] = Field(default=None, description="Google Gemini API key")
    firecrawl_api_key: Optional[str] = Field(default=None, description="Firecrawl API key")

    # LLM Provider Settings
    default_llm_provider: str = Field(default="ollama", description="Default LLM provider (ollama, openai, gemini)")
    enable_web_search: bool = Field(default=True, description="Enable web search functionality")
    enable_code_generation: bool = Field(default=True, description="Enable code generation features")

    # Pre-embedded Documents
    preembedded_docs_dir: str = Field(default="./data/preembedded", description="Pre-embedded documents directory")
    enable_source_filtering: bool = Field(default=True, description="Enable filtering by document source")

    # Registry Configuration
    registry_catalog_path: str = Field(default="./data/doc_catalog.json", description="Path to documentation catalog")
    registry_state_path: str = Field(default="./data/registry_state.json", description="Path to registry state file")

    # Logging Configuration
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: str = Field(default="./logs/rag_system.log", description="Log file path")
    log_max_size: int = Field(default=10 * 1024 * 1024, description="Max log file size")
    log_backup_count: int = Field(default=5, description="Log backup count")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore"
    }

    def validate_settings(self):
        """Validate critical settings on startup"""
        import warnings

        # Warn if running in production without API key
        if not self.debug and not self.api_key:
            warnings.warn(
                "Running in production mode (debug=False) without API key authentication. "
                "Set API_KEY environment variable for security.",
                UserWarning
            )

        # Validate API key length if set
        if self.api_key and len(self.api_key) < 16:
            raise ValueError(
                f"API key must be at least 16 characters long. Current length: {len(self.api_key)}. "
                "Generate a secure API key with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )

        # Warn about wildcard CORS in production
        if not self.debug and "*" in self.cors_origins:
            warnings.warn(
                "CORS origins set to wildcard ['*'] in production mode. "
                "This is a security risk. Set specific origins in CORS_ORIGINS environment variable.",
                UserWarning
            )

        # Validate Ollama configuration if it's the default provider
        if self.default_llm_provider == "ollama" and not self.ollama_host:
            raise ValueError("Ollama host must be configured when using Ollama as the default LLM provider")

    def create_directories(self):
        """Create required directories"""
        directories = [
            Path(self.vectordb_path),
            Path(self.cache_dir),
            Path(self.embedding_cache_dir),
            Path(self.upload_dir),
            Path(self.log_file).parent,
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)


# Global settings instance
_settings = None


def get_settings() -> Settings:
    """Get global settings instance"""
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings.validate_settings()
        _settings.create_directories()
    return _settings