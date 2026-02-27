"""
FastAPI REST API Module

The app instance is created lazily to avoid import-time side effects
(booting ChromaDB, LLM handlers, etc.) when subpackages like middleware
are imported independently in tests.
"""


def get_app():
    """Get the FastAPI app instance (created on first call)."""
    from .server import app
    return app


__all__ = ['get_app']
