"""
Documentation Registry - manages the catalog of available documentation sources
and tracks their ingestion state.
"""

import json
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path

from rag_system.core.registry.models import DocSource, IngestionStatus, DocSourceType
from rag_system.core.utils.logger import get_logger
from rag_system.config.settings import get_settings

logger = get_logger(__name__)
settings = get_settings()


class DocRegistry:
    """
    Manages available documentation sources and their ingestion state.

    Loads a static catalog from doc_catalog.json and persists runtime state
    (ingestion status, chunk counts) to registry_state.json.
    """

    def __init__(self):
        self.catalog_path = Path(settings.registry_catalog_path)
        self.state_path = Path(settings.registry_state_path)
        self._sources: Dict[str, DocSource] = {}

        self._load_catalog()
        self._load_state()

        logger.info(f"DocRegistry initialized with {len(self._sources)} sources")

    def _load_catalog(self):
        """Load the static documentation catalog."""
        if not self.catalog_path.exists():
            logger.warning(f"Catalog file not found: {self.catalog_path}")
            return

        try:
            with open(self.catalog_path, 'r', encoding='utf-8') as f:
                catalog_data = json.load(f)

            for entry in catalog_data:
                source = DocSource(**entry)
                self._sources[source.id] = source

            logger.info(f"Loaded {len(self._sources)} sources from catalog")
        except Exception as e:
            logger.error(f"Failed to load catalog: {e}")

    def _load_state(self):
        """Load persisted ingestion state and merge with catalog."""
        if not self.state_path.exists():
            return

        try:
            with open(self.state_path, 'r', encoding='utf-8') as f:
                state_data = json.load(f)

            for doc_id, state in state_data.items():
                if doc_id in self._sources:
                    # Update existing catalog entry with saved state
                    source = self._sources[doc_id]
                    source.status = IngestionStatus(state.get('status', 'not_started'))
                    source.chunk_count = state.get('chunk_count', 0)
                    if state.get('last_ingested'):
                        source.last_ingested = datetime.fromisoformat(state['last_ingested'])
                    source.error_message = state.get('error_message')
                else:
                    # Custom source added via dashboard (not in static catalog)
                    source = DocSource(
                        id=doc_id,
                        name=state.get('name', doc_id),
                        category=state.get('category', 'custom'),
                        icon=state.get('icon', ''),
                        source_type=DocSourceType(state.get('source_type', 'file_upload')),
                        source_paths=state.get('source_paths', []),
                        status=IngestionStatus(state.get('status', 'not_started')),
                        chunk_count=state.get('chunk_count', 0),
                        error_message=state.get('error_message'),
                    )
                    if state.get('last_ingested'):
                        source.last_ingested = datetime.fromisoformat(state['last_ingested'])
                    self._sources[doc_id] = source

            logger.info(f"Loaded state for {len(state_data)} sources")
        except Exception as e:
            logger.error(f"Failed to load registry state: {e}")

    def _save_state(self):
        """Persist current ingestion state to disk."""
        try:
            state_data = {}
            for doc_id, source in self._sources.items():
                state_data[doc_id] = {
                    'name': source.name,
                    'category': source.category,
                    'icon': source.icon,
                    'source_type': source.source_type.value,
                    'source_paths': source.source_paths,
                    'status': source.status.value,
                    'chunk_count': source.chunk_count,
                    'last_ingested': source.last_ingested.isoformat() if source.last_ingested else None,
                    'error_message': source.error_message,
                }

            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_path, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)

            logger.debug("Registry state saved")
        except Exception as e:
            logger.error(f"Failed to save registry state: {e}")

    def get_all_sources(self) -> List[DocSource]:
        """Get all documentation sources (both catalog and custom)."""
        return list(self._sources.values())

    def get_source(self, doc_id: str) -> Optional[DocSource]:
        """Get a specific documentation source by ID."""
        return self._sources.get(doc_id)

    def get_ingested_sources(self) -> List[DocSource]:
        """Get only sources that have been successfully ingested."""
        return [s for s in self._sources.values() if s.status == IngestionStatus.COMPLETED]

    def get_technology_mapping(self) -> Dict[str, str]:
        """
        Build a technology mapping dict from ingested sources.
        Replaces the old hardcoded TECHNOLOGY_MAPPING.
        Returns: {doc_id: display_name} for all ingested sources.
        """
        return {s.id: s.name for s in self._sources.values() if s.status == IngestionStatus.COMPLETED}

    def get_all_technology_mapping(self) -> Dict[str, str]:
        """Get mapping for ALL sources (ingested or not)."""
        return {s.id: s.name for s in self._sources.values()}

    def update_status(
        self,
        doc_id: str,
        status: IngestionStatus,
        chunk_count: int = 0,
        error_message: Optional[str] = None,
    ):
        """Update the ingestion status of a documentation source."""
        source = self._sources.get(doc_id)
        if not source:
            logger.error(f"Source not found: {doc_id}")
            return

        source.status = status
        source.chunk_count = chunk_count
        source.error_message = error_message

        if status == IngestionStatus.COMPLETED:
            source.last_ingested = datetime.now()

        self._save_state()
        logger.info(f"Updated {doc_id}: status={status.value}, chunks={chunk_count}")

    def add_custom_source(
        self,
        doc_id: str,
        name: str,
        category: str,
        source_type: DocSourceType,
        source_paths: List[str],
        icon: str = "",
    ) -> DocSource:
        """Add a custom documentation source (URL scrape or file upload)."""
        if doc_id in self._sources:
            logger.warning(f"Source {doc_id} already exists, updating")

        source = DocSource(
            id=doc_id,
            name=name,
            category=category,
            icon=icon,
            source_type=source_type,
            source_paths=source_paths,
        )
        self._sources[doc_id] = source
        self._save_state()
        logger.info(f"Added custom source: {doc_id} ({name})")
        return source

    def remove_source(self, doc_id: str) -> bool:
        """
        Reset a source's status to NOT_STARTED.
        Does NOT remove from catalog (catalog entries are permanent).
        Custom sources are fully removed.
        """
        source = self._sources.get(doc_id)
        if not source:
            return False

        # Check if it's a catalog entry (has matching file in catalog)
        is_catalog_entry = self._is_catalog_entry(doc_id)

        if is_catalog_entry:
            # Reset status but keep in catalog
            source.status = IngestionStatus.NOT_STARTED
            source.chunk_count = 0
            source.last_ingested = None
            source.error_message = None
        else:
            # Custom source - remove entirely
            del self._sources[doc_id]

        self._save_state()
        logger.info(f"Removed/reset source: {doc_id}")
        return True

    def _is_catalog_entry(self, doc_id: str) -> bool:
        """Check if a source is from the static catalog."""
        if not self.catalog_path.exists():
            return False
        try:
            with open(self.catalog_path, 'r', encoding='utf-8') as f:
                catalog_data = json.load(f)
            return any(entry.get('id') == doc_id for entry in catalog_data)
        except Exception:
            return False
