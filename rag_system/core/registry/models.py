"""
Data models for the Documentation Registry
"""

from typing import Optional, List
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field


class IngestionStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class DocSourceType(str, Enum):
    PREEMBEDDED_FILE = "preembedded_file"
    SCRAPED_JSON = "scraped_json"
    WEB_SCRAPE = "web_scrape"
    FILE_UPLOAD = "file_upload"


class DocSource(BaseModel):
    """One documentation source that can be ingested into the RAG system."""
    id: str
    name: str
    category: str = "language"
    version: Optional[str] = None
    icon: str = ""
    source_type: DocSourceType = DocSourceType.PREEMBEDDED_FILE
    source_paths: List[str] = Field(default_factory=list)
    status: IngestionStatus = IngestionStatus.NOT_STARTED
    chunk_count: int = 0
    last_ingested: Optional[datetime] = None
    error_message: Optional[str] = None
