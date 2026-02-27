"""
Ingestion Pipeline - orchestrates the full flow from raw documents to ChromaDB embeddings.

Supports: pre-embedded text files, scraped JSON, web scraping, and file uploads.
"""

import json
import threading
from typing import Dict, List, Optional
from pathlib import Path

from rag_system.core.registry.models import DocSource, DocSourceType, IngestionStatus
from rag_system.core.registry.registry import DocRegistry
from rag_system.core.chunking.chunker import SmartChunker
from rag_system.core.retrieval.vector_store import ChromaVectorStore
from rag_system.core.processing.document_processor import EnhancedDocumentProcessor
from rag_system.core.search.web_search import WebSearchProvider
from rag_system.core.utils.logger import get_logger
from rag_system.core.constants import INGESTION_BATCH_LOG_INTERVAL

logger = get_logger(__name__)


class IngestionPipeline:
    """
    Orchestrates: fetch docs -> process -> chunk -> embed -> store in ChromaDB.

    Uses SmartChunker.chunk_document() (singular) to avoid the asyncio.run() crash
    that happens with chunk_documents() inside async contexts.
    """

    def __init__(
        self,
        vector_store: ChromaVectorStore,
        chunker: SmartChunker,
        document_processor: EnhancedDocumentProcessor,
        registry: DocRegistry,
    ):
        self.vector_store = vector_store
        self.chunker = chunker
        self.document_processor = document_processor
        self.registry = registry
        self.web_search = WebSearchProvider()
        self._progress: Dict[str, Dict] = {}

    def ingest_source(self, doc_id: str) -> Dict:
        """
        Ingest a documentation source end-to-end.

        Returns:
            Dict with keys: success, chunk_count, message
        """
        source = self.registry.get_source(doc_id)
        if not source:
            return {'success': False, 'chunk_count': 0, 'message': f'Source not found: {doc_id}'}

        logger.info(f"Starting ingestion for: {source.name} ({doc_id})")
        self.registry.update_status(doc_id, IngestionStatus.IN_PROGRESS)
        self._progress[doc_id] = {'status': 'starting', 'step': 0, 'total_steps': 4, 'message': 'Loading documents...'}

        try:
            # Step 1: Load documents based on source type
            self._progress[doc_id]['step'] = 1
            self._progress[doc_id]['message'] = 'Loading documents...'
            documents = self._load_documents(source)

            if not documents:
                self.registry.update_status(doc_id, IngestionStatus.FAILED, error_message='No documents loaded')
                return {'success': False, 'chunk_count': 0, 'message': 'No documents found for this source'}

            logger.info(f"Loaded {len(documents)} documents for {doc_id}")

            # Step 2: Chunk documents
            self._progress[doc_id]['step'] = 2
            self._progress[doc_id]['message'] = f'Chunking {len(documents)} documents...'
            all_chunks = []
            for doc in documents:
                # Use chunk_document (singular) to avoid asyncio.run() crash
                chunks = self.chunker.chunk_document(doc)
                all_chunks.extend(chunks)

            if not all_chunks:
                self.registry.update_status(doc_id, IngestionStatus.FAILED, error_message='No chunks created')
                return {'success': False, 'chunk_count': 0, 'message': 'Chunking produced no results'}

            logger.info(f"Created {len(all_chunks)} chunks for {doc_id}")

            # Step 3: Prepare and embed
            self._progress[doc_id]['step'] = 3
            self._progress[doc_id]['message'] = f'Embedding {len(all_chunks)} chunks...'

            texts = [chunk['content'] for chunk in all_chunks]
            metadatas = []
            ids = []

            for i, chunk in enumerate(all_chunks):
                metadata = chunk.get('metadata', {})
                # Ensure technology and source metadata are set
                metadata['technology'] = doc_id
                if 'source' not in metadata or not metadata['source']:
                    metadata['source'] = 'comprehensive_docs'
                metadatas.append(metadata)
                ids.append(f"{doc_id}_{i}")

                if (i + 1) % INGESTION_BATCH_LOG_INTERVAL == 0:
                    logger.info(f"Prepared {i + 1}/{len(all_chunks)} chunks for {doc_id}")

            # Step 4: Store in ChromaDB
            self._progress[doc_id]['step'] = 4
            self._progress[doc_id]['message'] = 'Storing in vector database...'

            added = self.vector_store.add_documents(texts, metadatas, ids)

            # Update registry
            self.registry.update_status(doc_id, IngestionStatus.COMPLETED, chunk_count=added)
            self._progress[doc_id] = {'status': 'completed', 'step': 4, 'total_steps': 4, 'message': f'Done! {added} chunks added.'}

            logger.info(f"Ingestion complete for {doc_id}: {added} chunks")
            return {'success': True, 'chunk_count': added, 'message': f'Successfully ingested {added} chunks'}

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Ingestion failed for {doc_id}: {error_msg}")
            self.registry.update_status(doc_id, IngestionStatus.FAILED, error_message=error_msg)
            self._progress[doc_id] = {'status': 'failed', 'step': 0, 'total_steps': 4, 'message': f'Error: {error_msg}'}
            return {'success': False, 'chunk_count': 0, 'message': f'Ingestion failed: {error_msg}'}

    def _load_documents(self, source: DocSource) -> List[Dict]:
        """Load documents based on source type."""
        if source.source_type == DocSourceType.PREEMBEDDED_FILE:
            return self._load_preembedded(source)
        elif source.source_type == DocSourceType.SCRAPED_JSON:
            return self._load_scraped_json(source)
        elif source.source_type == DocSourceType.WEB_SCRAPE:
            return self._load_web_scrape(source)
        elif source.source_type == DocSourceType.FILE_UPLOAD:
            return self._load_uploaded_files(source)
        else:
            logger.error(f"Unknown source type: {source.source_type}")
            return []

    def _load_preembedded(self, source: DocSource) -> List[Dict]:
        """Load pre-embedded text files."""
        documents = []
        for path_str in source.source_paths:
            file_path = Path(path_str)
            if not file_path.exists():
                logger.warning(f"File not found: {file_path}")
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                if content.strip():
                    documents.append({
                        'title': f"{source.name} - {file_path.stem}",
                        'content': content,
                        'source': 'comprehensive_docs',
                        'technology': source.id,
                        'doc_type': 'reference',
                    })
                    logger.info(f"Loaded {file_path.name}: {len(content)} chars")
            except Exception as e:
                logger.error(f"Failed to read {file_path}: {e}")

        return documents

    def _load_scraped_json(self, source: DocSource) -> List[Dict]:
        """Load pre-scraped JSON documentation files."""
        documents = []
        for path_str in source.source_paths:
            file_path = Path(path_str)
            if not file_path.exists():
                logger.warning(f"JSON file not found: {file_path}")
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                if isinstance(data, list):
                    for doc in data:
                        doc.setdefault('technology', source.id)
                        doc.setdefault('source', 'scraped_docs')
                        documents.append(doc)
                elif isinstance(data, dict):
                    data.setdefault('technology', source.id)
                    data.setdefault('source', 'scraped_docs')
                    documents.append(data)

                logger.info(f"Loaded {file_path.name}: {len(documents)} documents")
            except Exception as e:
                logger.error(f"Failed to load JSON {file_path}: {e}")

        return documents

    def _load_web_scrape(self, source: DocSource) -> List[Dict]:
        """Scrape documentation from URLs."""
        documents = []
        for url in source.source_paths:
            try:
                result = self.web_search.crawl_url(url)
                if result and result.get('content'):
                    documents.append({
                        'title': result.get('metadata', {}).get('title', url),
                        'content': result['content'],
                        'source': 'web_scrape',
                        'technology': source.id,
                        'url': url,
                    })
                    logger.info(f"Scraped {url}: {len(result['content'])} chars")
                else:
                    logger.warning(f"No content from URL: {url}")
            except Exception as e:
                logger.error(f"Failed to scrape {url}: {e}")

        return documents

    def _load_uploaded_files(self, source: DocSource) -> List[Dict]:
        """Process uploaded files."""
        documents = []
        for path_str in source.source_paths:
            file_path = Path(path_str)
            if not file_path.exists():
                logger.warning(f"Upload file not found: {file_path}")
                continue

            try:
                result = self.document_processor.process_file(file_path)
                if result.get('success') and result.get('content'):
                    documents.append({
                        'title': f"{source.name} - {file_path.name}",
                        'content': result['content'],
                        'source': 'file_upload',
                        'technology': source.id,
                    })
                    logger.info(f"Processed upload {file_path.name}: {len(result['content'])} chars")
            except Exception as e:
                logger.error(f"Failed to process upload {file_path}: {e}")

        return documents

    def remove_source(self, doc_id: str) -> Dict:
        """Remove all chunks for a documentation source from ChromaDB."""
        try:
            # Delete from ChromaDB by technology metadata
            self.vector_store.collection.delete(where={"technology": doc_id})

            # Update registry
            self.registry.remove_source(doc_id)

            logger.info(f"Removed all chunks for {doc_id}")
            return {'success': True, 'message': f'Removed {doc_id} from knowledge base'}
        except Exception as e:
            logger.error(f"Failed to remove {doc_id}: {e}")
            return {'success': False, 'message': f'Failed to remove: {str(e)}'}

    def get_progress(self, doc_id: str) -> Dict:
        """Get ingestion progress for a source."""
        return self._progress.get(doc_id, {'status': 'unknown', 'step': 0, 'total_steps': 4, 'message': 'No ingestion in progress'})

    def ingest_source_background(self, doc_id: str):
        """Run ingestion in a background thread."""
        thread = threading.Thread(target=self.ingest_source, args=(doc_id,), daemon=True)
        thread.start()
        logger.info(f"Background ingestion started for {doc_id}")

    def ingest_from_url(self, url: str, name: str, doc_id: str, category: str = "custom") -> Dict:
        """Add a new documentation source from a URL and ingest it."""
        # Register the source
        self.registry.add_custom_source(
            doc_id=doc_id,
            name=name,
            category=category,
            source_type=DocSourceType.WEB_SCRAPE,
            source_paths=[url],
            icon="",
        )

        # Ingest it
        return self.ingest_source(doc_id)

    def ingest_from_upload(
        self,
        file_path: str,
        name: str,
        doc_id: str,
        category: str = "custom",
        file_content: Optional[bytes] = None,
    ) -> Dict:
        """Add a new documentation source from an uploaded file and ingest it."""
        upload_dir = Path("./data/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Save file content if provided as bytes
        saved_path = file_path
        if file_content:
            saved_path = str(upload_dir / Path(file_path).name)
            with open(saved_path, 'wb') as f:
                f.write(file_content)

        # Register the source
        self.registry.add_custom_source(
            doc_id=doc_id,
            name=name,
            category=category,
            source_type=DocSourceType.FILE_UPLOAD,
            source_paths=[saved_path],
            icon="",
        )

        # Ingest it
        return self.ingest_source(doc_id)
