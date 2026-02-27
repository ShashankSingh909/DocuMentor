"""
Ingestion Pipeline - orchestrates document fetching, processing, chunking, and embedding
"""

from .pipeline import IngestionPipeline

__all__ = ['IngestionPipeline']
