"""
Vector Store implementation using ChromaDB for document embeddings and semantic search.

Handles document storage, retrieval, and similarity search with proper error handling
and retry logic for ChromaDB operations.
"""
import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions
import time
from pathlib import Path
from typing import List, Dict, Optional
from filelock import FileLock, Timeout
from rag_system.core.utils.logger import get_logger
from rag_system.core.utils.embedding_cache import embedding_cache
from rag_system.config.settings import get_settings
from rag_system.core.constants import CHROMADB_RETRY_ATTEMPTS, CHROMADB_RETRY_DELAY, CHROMADB_DOCUMENT_LIMIT

settings = get_settings()

logger = get_logger(__name__)

class ChromaVectorStore:
    def __init__(self):
        self.persist_directory = settings.chroma_persist_directory
        self.collection_name = settings.collection_name

        # Set up file locking to prevent database corruption
        lock_dir = Path(self.persist_directory).parent / "locks"
        lock_dir.mkdir(parents=True, exist_ok=True)
        self.lock_file_path = lock_dir / f"{self.collection_name}.lock"
        self.lock = FileLock(self.lock_file_path, timeout=10)

        logger.debug(f"Using lock file: {self.lock_file_path}")

        # Initialize client with proper locking
        with self.lock:
            logger.debug("Acquired lock for ChromaDB initialization")
            try:
                self.client = chromadb.PersistentClient(path=self.persist_directory)
            except Exception as e:
                # Corrupted or incompatible persistent DB — wipe and retry
                logger.warning(
                    f"ChromaDB initialization failed ({e}). "
                    f"Removing corrupted DB at {self.persist_directory} and recreating."
                )
                import shutil
                shutil.rmtree(self.persist_directory, ignore_errors=True)
                Path(self.persist_directory).mkdir(parents=True, exist_ok=True)
                self.client = chromadb.PersistentClient(path=self.persist_directory)

        # Get optimized embedding function with caching
        try:
            base_embedding = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )
            self.embedding_function = CachedEmbeddingFunction(
                base_embedding,
                model_name="all-MiniLM-L6-v2"
            )
            logger.info("Using optimized sentence-transformers with embedding cache")
        except Exception as e:
            logger.warning(f"Failed to load sentence-transformers, falling back to default: {e}")
            base_embedding = embedding_functions.DefaultEmbeddingFunction()
            self.embedding_function = CachedEmbeddingFunction(
                base_embedding,
                model_name="default"
            )
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection(
                name=self.collection_name
            )
            logger.info(f"Loaded collection: {self.collection.count()} docs")
        except (ValueError, Exception) as get_err:
            # Collection doesn't exist, create it (handles both ValueError and NotFoundError)
            try:
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    embedding_function=self.embedding_function
                )
                logger.info("Created new collection")
            except Exception as e:
                # If creation fails, try to get existing collection without embedding function
                logger.warning(f"Collection creation failed: {e}, attempting to load existing")
                self.collection = self.client.get_collection(name=self.collection_name)
                logger.info(f"Using existing collection: {self.collection.count()} docs")
    
    def add_documents(self, texts: List[str], metadatas: List[dict], ids: List[str]):
        """
        Add documents to the vector store using upsert for reliability.

        Args:
            texts: List of document texts to add
            metadatas: List of metadata dictionaries for each document
            ids: List of unique IDs for each document

        Returns:
            Number of documents successfully added

        Note: Implements data sanitization to handle ChromaDB compatibility issues:
            - None values are replaced with empty strings
            - High Unicode characters are stripped
            - Batching prevents timeout issues
        """
        # Use file locking to prevent concurrent writes
        with self.lock:
            logger.debug(f"Acquired lock for adding {len(texts)} documents")

            # Optimized batch size based on document size and system memory
            BATCH_SIZE = self._calculate_optimal_batch_size(texts)

            added = 0
            for i in range(0, len(texts), BATCH_SIZE):
                batch_end = min(i + BATCH_SIZE, len(texts))

                # Clean metadata - Chroma hates None
                clean_meta = []
                for m in metadatas[i:batch_end]:
                    # Sanitize metadata for ChromaDB compatibility
                    clean = {}
                    for k, v in m.items():
                        if v is None:
                            clean[k] = ""
                        elif isinstance(v, str):
                            # Strip high unicode that breaks Chroma
                            clean[k] = v.encode('utf-8', 'ignore').decode('utf-8')
                        else:
                            clean[k] = v
                    clean_meta.append(clean)

                # Clean texts too
                clean_texts = []
                for t in texts[i:batch_end]:
                    # Remove null bytes and high unicode
                    cleaned = t.replace('\x00', '').encode('utf-8', 'ignore').decode('utf-8')
                    clean_texts.append(cleaned)

                # Try to add with retry logic
                for retry in range(CHROMADB_RETRY_ATTEMPTS):
                    try:
                        self.collection.upsert(
                            documents=clean_texts,
                            metadatas=clean_meta,
                            ids=ids[i:batch_end]
                        )
                        added += len(clean_texts)
                        break
                    except Exception as e:
                        if "quota" in str(e).lower():
                            # Hit ChromaDB document limit
                            logger.error(f"ChromaDB quota exceeded (limit: {CHROMADB_DOCUMENT_LIMIT})")
                            raise
                        elif retry < CHROMADB_RETRY_ATTEMPTS - 1:
                            # Retry with exponential backoff
                            wait_time = CHROMADB_RETRY_DELAY * (2 ** retry)
                            logger.warning(f"Retry {retry + 1}/{CHROMADB_RETRY_ATTEMPTS} for batch {i//BATCH_SIZE}, waiting {wait_time}s")
                        time.sleep(0.5 * (retry + 1))  # Backoff
                    else:
                        logger.error(f"Failed batch {i//BATCH_SIZE}: {e}")
                        # Skip this batch rather than fail everything
                        break
            
            # Don't hammer ChromaDB
            if len(texts) > 500:
                time.sleep(0.1)  # Helps with large imports
        
        logger.info(f"Added {added}/{len(texts)} documents")
        return added
    
    def search(self, query: str, k: int = 5, filter_dict: Optional[Dict] = None) -> List[Dict]:
        """
        Search for similar documents using semantic similarity.

        Args:
            query: Search query string
            k: Number of results to return (default: 5, max: 100)
            filter_dict: Optional metadata filters

        Returns:
            List of dictionaries containing matched documents with content, metadata, and similarity scores
        """
        # Clean query
        query = query.encode('utf-8', 'ignore').decode('utf-8')

        # Enhance short queries for better semantic matching
        if len(query.split()) < 3:
            query = f"{query} documentation reference"
        
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=min(k, 100),  # ChromaDB max is 100
                where=filter_dict
            )
            
            # Unpack weird ChromaDB response format
            documents = results.get('documents', [[]])[0]
            metadatas = results.get('metadatas', [[]])[0]
            distances = results.get('distances', [[]])[0]
            
            # Format for API
            formatted = []
            for doc, meta, dist in zip(documents, metadatas, distances):
                formatted.append({
                    'content': doc,
                    'metadata': meta or {},
                    'score': 1 - dist  # Convert distance to similarity
                })
            
            return formatted
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []  # Return empty rather than crash
    
    def get_collection_stats(self) -> Dict:
        """
        Get collection statistics including document count and source distribution.

        Returns:
            Dictionary containing total chunks, sources distribution, and sample size
        """
        try:
            count = self.collection.count()
            # Sample documents to analyze source distribution
            sample = self.collection.get(limit=1000)
            sources = {}
            for meta in sample.get('metadatas', []):
                if meta and 'source' in meta:
                    src = meta['source']
                    sources[src] = sources.get(src, 0) + 1

            return {
                'total_chunks': count,
                'sources': sources,
                'sample_size': len(sample.get('ids', []))
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {'total_chunks': 0, 'sources': {}}

    def _calculate_optimal_batch_size(self, texts: List[str]) -> int:
        """Calculate optimal batch size based on text size and system constraints"""
        if not texts:
            return 100

        # Calculate average text length
        avg_length = sum(len(text) for text in texts[:100]) / min(100, len(texts))

        # Adjust batch size based on text length
        if avg_length < 500:  # Short texts
            return 200
        elif avg_length < 2000:  # Medium texts
            return 100
        elif avg_length < 5000:  # Long texts
            return 50
        else:  # Very long texts
            return 25

    def add_documents_optimized(self, texts: List[str], metadatas: List[dict], ids: List[str]):
        """
        Optimized document addition with better memory management.

        Args:
            texts: List of document texts to add
            metadatas: List of metadata dictionaries for each document
            ids: List of unique IDs for each document

        Returns:
            Number of documents successfully added
        """
        if not texts:
            return 0

        logger.info(f"Adding {len(texts)} documents with optimized processing")

        # Pre-process all data to avoid doing it in batches
        clean_texts, clean_metadatas = self._preprocess_documents(texts, metadatas)

        BATCH_SIZE = self._calculate_optimal_batch_size(clean_texts)
        logger.info(f"Using batch size: {BATCH_SIZE}")

        added = 0
        total_batches = (len(clean_texts) + BATCH_SIZE - 1) // BATCH_SIZE

        for batch_idx in range(0, len(clean_texts), BATCH_SIZE):
            batch_end = min(batch_idx + BATCH_SIZE, len(clean_texts))
            current_batch = batch_idx // BATCH_SIZE + 1

            logger.info(f"Processing batch {current_batch}/{total_batches}")

            try:
                self.collection.upsert(
                    documents=clean_texts[batch_idx:batch_end],
                    metadatas=clean_metadatas[batch_idx:batch_end],
                    ids=ids[batch_idx:batch_end]
                )
                added += batch_end - batch_idx

            except Exception as e:
                logger.error(f"Failed to add batch {current_batch}: {e}")
                # Try individual documents in this batch
                for i in range(batch_idx, batch_end):
                    try:
                        self.collection.upsert(
                            documents=[clean_texts[i]],
                            metadatas=[clean_metadatas[i]],
                            ids=[ids[i]]
                        )
                        added += 1
                    except Exception as individual_error:
                        logger.warning(f"Skipped document {i}: {individual_error}")

        logger.info(f"Successfully added {added}/{len(texts)} documents")
        return added

    def _preprocess_documents(self, texts: List[str], metadatas: List[dict]) -> tuple:
        """Pre-process documents for optimal ChromaDB compatibility"""
        clean_texts = []
        clean_metadatas = []

        for text, metadata in zip(texts, metadatas):
            # Clean text
            cleaned_text = text.replace('\x00', '').encode('utf-8', 'ignore').decode('utf-8')
            clean_texts.append(cleaned_text)

            # Clean metadata
            clean_meta = {}
            for k, v in metadata.items():
                if v is None:
                    clean_meta[k] = ""
                elif isinstance(v, str):
                    clean_meta[k] = v.encode('utf-8', 'ignore').decode('utf-8')
                else:
                    clean_meta[k] = str(v)
            clean_metadatas.append(clean_meta)

        return clean_texts, clean_metadatas

class CachedEmbeddingFunction:
    """Wrapper for embedding function with caching"""

    def __init__(self, base_embedding_function, model_name: str = "default"):
        self.base_function = base_embedding_function
        self.model_name = model_name
        logger.info(f"Initialized cached embedding function for model: {model_name}")

    def name(self) -> str:
        """Return the name of the embedding function"""
        return f"cached_{self.model_name}"

    def __call__(self, input: List[str]) -> List[List[float]]:
        """Generate embeddings with caching"""
        input_texts = input  # Use the new parameter name
        if not input_texts:
            return []

        # Check cache for existing embeddings
        cached_results = embedding_cache.get_embeddings_batch(input_texts, self.model_name)

        # Separate cached and uncached texts
        uncached_texts = []
        uncached_indices = []
        results = [None] * len(input_texts)

        for i, text in enumerate(input_texts):
            cached_embedding = cached_results.get(text)
            if cached_embedding is not None:
                results[i] = cached_embedding.tolist()
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)

        # Generate embeddings for uncached texts
        if uncached_texts:
            logger.debug(f"Generating {len(uncached_texts)} new embeddings")
            new_embeddings = self.base_function(uncached_texts)

            # Cache new embeddings and add to results
            cache_pairs = []
            for i, (text, embedding) in enumerate(zip(uncached_texts, new_embeddings)):
                idx = uncached_indices[i]
                results[idx] = embedding
                cache_pairs.append((text, embedding))

            # Batch cache the new embeddings
            embedding_cache.set_embeddings_batch(cache_pairs, self.model_name)

        return results

# Keep old import name for backwards compat
VectorStore = ChromaVectorStore





