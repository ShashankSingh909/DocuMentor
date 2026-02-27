from typing import List, Dict, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter, Language
from langchain_text_splitters import MarkdownHeaderTextSplitter
import hashlib
import re
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from rag_system.core.utils.logger import get_logger
from rag_system.config.settings import get_settings

settings = get_settings()

logger = get_logger(__name__)

class SmartChunker:
    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
        preserve_code_blocks: bool = True
    ):
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
        self.preserve_code_blocks = preserve_code_blocks
        
        logger.info(f"Initialized SmartChunker: chunk_size={self.chunk_size}, overlap={self.chunk_overlap}")
        
        # Different splitters for different content types
        self.markdown_splitter = self._create_markdown_splitter()
        self.code_splitter = RecursiveCharacterTextSplitter.from_language(
            language=Language.PYTHON,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
    def _create_markdown_splitter(self):
        """Create markdown-aware splitter"""
        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ]
        return MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
        
    def chunk_documents_from_files(self) -> List[Dict]:
        """Load documents from files and chunk them"""
        logger.info("📚 Loading documents from files...")

        documents = []

        # Use upload directory to look for processed documents
        raw_data_dir = Path(settings.upload_dir).parent / "raw"

        # Load LangChain docs if they exist
        langchain_file = raw_data_dir / "langchain" / "langchain_docs.json"
        if langchain_file.exists():
            with open(langchain_file, 'r', encoding='utf-8') as f:
                langchain_docs = json.load(f)
                documents.extend(langchain_docs)
                logger.info(f"📄 Loaded {len(langchain_docs)} LangChain documents")

        # Load FastAPI docs if they exist
        fastapi_file = raw_data_dir / "fastapi" / "fastapi_docs.json"
        if fastapi_file.exists():
            with open(fastapi_file, 'r', encoding='utf-8') as f:
                fastapi_docs = json.load(f)
                documents.extend(fastapi_docs)
                logger.info(f"📄 Loaded {len(fastapi_docs)} FastAPI documents")

        if not documents:
            logger.warning("⚠️ No documents found in raw data directory. This method expects pre-scraped JSON files.")
            return []

        logger.info(f"📚 Total documents loaded: {len(documents)}")

        # Chunk all documents
        return self.chunk_documents(documents)
        
    def chunk_documents(self, documents: List[Dict]) -> List[Dict]:
        """Chunk a list of documents with parallel processing"""
        logger.info(f"🔪 Starting to chunk {len(documents)} documents...")

        # Use async processing for better performance
        return asyncio.run(self._chunk_documents_async(documents))

    async def _chunk_documents_async(self, documents: List[Dict]) -> List[Dict]:
        """Async document chunking for better performance"""
        all_chunks = []

        # Process in batches to avoid overwhelming the system
        batch_size = min(10, len(documents))  # Optimal batch size

        # Use configured max_workers from settings
        with ThreadPoolExecutor(max_workers=settings.max_workers) as executor:
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                logger.info(f"🔪 Processing batch {i//batch_size + 1}/{(len(documents) + batch_size - 1)//batch_size}")

                # Submit batch to thread pool
                futures = [
                    executor.submit(self._chunk_document_safe, doc, idx)
                    for idx, doc in enumerate(batch, start=i+1)
                ]

                # Collect results
                for future in futures:
                    try:
                        chunks = future.result(timeout=30)  # 30 second timeout per document
                        all_chunks.extend(chunks)
                    except Exception as e:
                        logger.error(f"❌ Failed to chunk document: {e}")
                        continue

        logger.info(f"✅ Created {len(all_chunks)} chunks from {len(documents)} documents using parallel processing")
        return all_chunks

    def _chunk_document_safe(self, document: Dict, doc_index: int) -> List[Dict]:
        """Thread-safe wrapper for chunking a single document"""
        try:
            logger.debug(f"🔪 Chunking document {doc_index}: {document.get('title', 'Untitled')}")
            return self.chunk_document(document)
        except Exception as e:
            logger.error(f"❌ Error chunking document {doc_index}: {e}")
            return []
        
    def chunk_document(self, document: Dict) -> List[Dict]:
        """Chunk a single document intelligently"""
        content = document.get('content', '')
        if not content:
            logger.warning(f"⚠️ Empty content for document: {document.get('title', 'Unknown')}")
            return []
            
        metadata = document.copy()
        
        # Remove content from metadata to avoid duplication
        if 'content' in metadata:
            del metadata['content']
        if 'sections' in metadata:
            del metadata['sections']
        
        # Detect document type and chunk accordingly
        doc_type = metadata.get('doc_type', 'unknown')
        source = metadata.get('source', 'unknown')
        
        logger.debug(f"🔍 Chunking {source} document of type {doc_type}")
        
        if doc_type == 'api_reference':
            chunks = self._chunk_api_documentation(content, metadata)
        elif '```' in content:  # Contains code blocks
            chunks = self._chunk_mixed_content(content, metadata)
        else:
            chunks = self._chunk_text_content(content, metadata)
            
        # Add chunk position numbers
        for i, chunk in enumerate(chunks):
            chunk['metadata']['chunk_position'] = i
            chunk['metadata']['total_chunks'] = len(chunks)
            
        return chunks
        
    def _chunk_mixed_content(self, content: str, metadata: Dict) -> List[Dict]:
        """Chunk content with mixed text and code"""
        chunks = []
        
        # Split by code blocks first to preserve them
        code_block_pattern = r'```[\s\S]*?```'
        parts = re.split(f'({code_block_pattern})', content)
        
        current_text = ""
        chunk_counter = 0
        
        for part in parts:
            if part.startswith('```'):
                # This is a code block
                if current_text.strip():
                    # Process accumulated text first
                    text_chunks = self._create_text_chunks(current_text, metadata, chunk_counter)
                    chunks.extend(text_chunks)
                    chunk_counter += len(text_chunks)
                    current_text = ""
                
                # Handle code block
                if len(part) <= self.chunk_size:
                    # Code block fits in one chunk
                    chunks.append(self._create_chunk(
                        content=part,
                        metadata=metadata,
                        chunk_type='code',
                        chunk_id=self._generate_chunk_id(part + str(chunk_counter))
                    ))
                    chunk_counter += 1
                else:
                    # Code block too large, need to split carefully
                    code_chunks = self.code_splitter.split_text(part)
                    for code_chunk in code_chunks:
                        chunks.append(self._create_chunk(
                            content=code_chunk,
                            metadata=metadata,
                            chunk_type='code',
                            chunk_id=self._generate_chunk_id(code_chunk + str(chunk_counter))
                        ))
                        chunk_counter += 1
            else:
                # This is text content
                current_text += part
        
        # Process any remaining text
        if current_text.strip():
            text_chunks = self._create_text_chunks(current_text, metadata, chunk_counter)
            chunks.extend(text_chunks)
            
        return chunks
        
    def _chunk_api_documentation(self, content: str, metadata: Dict) -> List[Dict]:
        """Special handling for API documentation"""
        chunks = []
        
        # Try to split by function/endpoint definitions
        # Look for patterns like "### functionName" or "## GET /endpoint"
        section_pattern = r'(### .+?(?=\n###|\n##|\Z))'
        sections = re.split(section_pattern, content, flags=re.DOTALL)
        
        chunk_counter = 0
        for section in sections:
            if section.strip():
                if len(section) <= self.chunk_size:
                    chunks.append(self._create_chunk(
                        content=section,
                        metadata=metadata,
                        chunk_type='api_reference',
                        chunk_id=self._generate_chunk_id(section + str(chunk_counter))
                    ))
                    chunk_counter += 1
                else:
                    # Section too large, split it
                    sub_chunks = self.text_splitter.split_text(section)
                    for sub_chunk in sub_chunks:
                        chunks.append(self._create_chunk(
                            content=sub_chunk,
                            metadata=metadata,
                            chunk_type='api_reference',
                            chunk_id=self._generate_chunk_id(sub_chunk + str(chunk_counter))
                        ))
                        chunk_counter += 1
                        
        return chunks
        
    def _chunk_text_content(self, content: str, metadata: Dict) -> List[Dict]:
        """Chunk pure text content"""
        text_chunks = self.text_splitter.split_text(content)
        
        chunks = []
        for i, chunk_text in enumerate(text_chunks):
            chunks.append(self._create_chunk(
                content=chunk_text,
                metadata=metadata,
                chunk_type='text',
                chunk_id=self._generate_chunk_id(chunk_text + str(i))
            ))
            
        return chunks
    
    def _create_text_chunks(self, text: str, metadata: Dict, start_counter: int) -> List[Dict]:
        """Helper to create text chunks"""
        if not text.strip():
            return []
            
        text_chunks = self.text_splitter.split_text(text)
        chunks = []
        
        for i, chunk_text in enumerate(text_chunks):
            chunks.append(self._create_chunk(
                content=chunk_text,
                metadata=metadata,
                chunk_type='text',
                chunk_id=self._generate_chunk_id(chunk_text + str(start_counter + i))
            ))
            
        return chunks
    
    def _create_chunk(self, content: str, metadata: Dict, chunk_type: str, chunk_id: str) -> Dict:
        """Create a standardized chunk object"""
        chunk_metadata = metadata.copy()
        chunk_metadata.update({
            'chunk_type': chunk_type,
            'chunk_id': chunk_id,
            'chunk_size': len(content),
            'word_count': len(content.split())
        })
        
        return {
            'content': content.strip(),
            'metadata': chunk_metadata
        }
        
    def _generate_chunk_id(self, content: str) -> str:
        """Generate unique ID for chunk"""
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def save_chunks(self, chunks: List[Dict], filename: str = "chunks.json"):
        """Save chunks to file"""
        output_file = settings.PROCESSED_DATA_DIR / filename
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, indent=2, ensure_ascii=False)
            
        logger.info(f"💾 Saved {len(chunks)} chunks to {output_file}")
        
        # Save statistics
        stats = self._calculate_chunk_stats(chunks)
        stats_file = settings.PROCESSED_DATA_DIR / f"chunk_stats.json"
        
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2)
            
        logger.info(f"📊 Chunk statistics: {stats}")
        
        return output_file
        
    def _calculate_chunk_stats(self, chunks: List[Dict]) -> Dict:
        """Calculate statistics about chunks"""
        if not chunks:
            return {}
            
        chunk_sizes = [len(chunk['content']) for chunk in chunks]
        word_counts = [chunk['metadata'].get('word_count', 0) for chunk in chunks]
        
        # Count by type
        type_counts = {}
        source_counts = {}
        
        for chunk in chunks:
            chunk_type = chunk['metadata'].get('chunk_type', 'unknown')
            source = chunk['metadata'].get('source', 'unknown')
            
            type_counts[chunk_type] = type_counts.get(chunk_type, 0) + 1
            source_counts[source] = source_counts.get(source, 0) + 1
        
        return {
            'total_chunks': len(chunks),
            'avg_chunk_size': sum(chunk_sizes) / len(chunk_sizes),
            'max_chunk_size': max(chunk_sizes),
            'min_chunk_size': min(chunk_sizes),
            'avg_word_count': sum(word_counts) / len(word_counts),
            'chunk_types': type_counts,
            'sources': source_counts
        }

# Test function
def test_chunker():
    """Test the chunker with existing documents"""
    logger.info("🧪 Testing SmartChunker...")
    
    chunker = SmartChunker()
    chunks = chunker.chunk_documents_from_files()
    
    if chunks:
        output_file = chunker.save_chunks(chunks)
        logger.info(f"✅ Chunking test completed! Output: {output_file}")
    else:
        logger.error("❌ No chunks created!")

if __name__ == "__main__":
    test_chunker()




