"""
Constants for the RAG System
Moved all the magic numbers here - was getting annoying to track them down everywhere
"""

# ============================================
# Vector Store Constants
# ============================================
DEFAULT_SEARCH_K = 8  # seems to work well for most queries
MAX_SEARCH_K = 100
MIN_SEARCH_K = 1

# Batch sizes for vector operations
# TODO: might need to tune these based on actual usage
SMALL_BATCH_SIZE = 100
MEDIUM_BATCH_SIZE = 500
LARGE_BATCH_SIZE = 2000
XLARGE_BATCH_SIZE = 5000

# ChromaDB limits - found these through trial and error
CHROMADB_DOCUMENT_LIMIT = 10000
CHROMADB_RETRY_ATTEMPTS = 3  # usually succeeds on 2nd try
CHROMADB_RETRY_DELAY = 1.0  # seconds

# Sample limits for statistics
STATS_SAMPLE_LIMIT = 1000

# ============================================
# LLM & Generation Constants
# ============================================
DEFAULT_TEMPERATURE = 0.3  # 0.7 was too creative, 0.1 too boring
MIN_TEMPERATURE = 0.0
MAX_TEMPERATURE = 1.0

DEFAULT_MAX_TOKENS = 800  # good balance between detail and speed
MIN_MAX_TOKENS = 100
MAX_MAX_TOKENS = 4000  # probably shouldn't go higher than this

# Context limits
MAX_CONTEXT_RESULTS = 3  # more than this and LLM gets confused
CONTEXT_CONTENT_LENGTH = 800
QUERY_PREVIEW_LENGTH = 50

# ============================================
# Caching Constants
# ============================================
DEFAULT_CACHE_SIZE = 1000
MIN_RESPONSE_LENGTH_TO_CACHE = 10
CACHE_SAVE_INTERVAL = 10  # Save every N entries
DEFAULT_CACHE_TTL = 3600  # seconds

# Embedding cache
MAX_EMBEDDING_CACHE_SIZE = 10000

# ============================================
# Chunking Constants
# ============================================
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200
MAX_CHUNKS_PER_DOCUMENT = 1000

OPTIMAL_BATCH_SIZE_DOCS = 10
DEFAULT_WORKER_THREADS = 4

# ============================================
# File Processing Constants
# ============================================
MAX_FILE_SIZE_MB = 50
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# Supported file extensions
SUPPORTED_TEXT_EXTENSIONS = ['.txt', '.md', '.markdown']
SUPPORTED_PDF_EXTENSIONS = ['.pdf']
SUPPORTED_DOC_EXTENSIONS = ['.docx', '.doc']
SUPPORTED_SPREADSHEET_EXTENSIONS = ['.xlsx', '.xls', '.csv']
SUPPORTED_PRESENTATION_EXTENSIONS = ['.pptx', '.ppt']

ALL_SUPPORTED_EXTENSIONS = (
    SUPPORTED_TEXT_EXTENSIONS +
    SUPPORTED_PDF_EXTENSIONS +
    SUPPORTED_DOC_EXTENSIONS +
    SUPPORTED_SPREADSHEET_EXTENSIONS +
    SUPPORTED_PRESENTATION_EXTENSIONS
)

# ============================================
# API & Network Constants
# ============================================
DEFAULT_API_TIMEOUT = 30  # seconds
OLLAMA_TIMEOUT = 120  # ollama can be slow sometimes, give it time
HEALTH_CHECK_TIMEOUT = 2  # seconds
HEALTH_CHECK_MAX_RETRIES = 30  # might be overkill but better safe than sorry

# Rate limiting (requests per minute)
# adjusted these after some testing
RATE_LIMIT_SEARCH = 60
RATE_LIMIT_UPLOAD = 10  # uploads are expensive
RATE_LIMIT_QUERY = 30
RATE_LIMIT_GENERATION = 20  # LLM calls cost money!

# ============================================
# Web Search Constants
# ============================================
DEFAULT_WEB_SEARCH_RESULTS = 5
MAX_WEB_SEARCH_RESULTS = 20
WEB_CONTENT_TRUNCATE_LENGTH = 2000

# ============================================
# Performance Constants
# ============================================
ACCEPTABLE_SEARCH_TIME = 3.0  # seconds
PERFORMANCE_LOG_THRESHOLD = 1.0  # Log if operation takes longer than this

# ============================================
# Logging Constants
# ============================================
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ============================================
# Validation Constants
# ============================================
MIN_QUERY_LENGTH = 1
MAX_QUERY_LENGTH = 1000

MIN_API_KEY_LENGTH = 16
MAX_API_KEY_LENGTH = 128

# ============================================
# Metrics Constants
# ============================================
METRICS_NAMESPACE = "documenter"
METRICS_SUBSYSTEM_API = "api"
METRICS_SUBSYSTEM_RAG = "rag"
METRICS_SUBSYSTEM_LLM = "llm"

# Histogram buckets for latency (in seconds)
LATENCY_BUCKETS = [0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]

# ============================================
# Registry & Ingestion Constants
# ============================================
REGISTRY_CATALOG_FILE = "doc_catalog.json"
REGISTRY_STATE_FILE = "registry_state.json"
MAX_SCRAPE_PAGES = 10
SCRAPE_TIMEOUT = 30  # seconds per URL
INGESTION_BATCH_LOG_INTERVAL = 50  # log progress every N chunks

# ============================================
# Error Messages
# ============================================
ERROR_FILE_TOO_LARGE = f"File size exceeds maximum allowed size of {MAX_FILE_SIZE_MB}MB"
ERROR_INVALID_FILE_TYPE = "Unsupported file type"
ERROR_QUERY_TOO_SHORT = f"Query must be at least {MIN_QUERY_LENGTH} characters"
ERROR_QUERY_TOO_LONG = f"Query must not exceed {MAX_QUERY_LENGTH} characters"
ERROR_INVALID_API_KEY = "Invalid or missing API key"
ERROR_RATE_LIMIT_EXCEEDED = "Rate limit exceeded. Please try again later."
