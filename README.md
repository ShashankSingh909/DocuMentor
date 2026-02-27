# DocuMentor

> **AI-Powered Documentation Assistant with Retrieval-Augmented Generation (RAG)**

DocuMentor is an intelligent documentation assistant that helps developers search, understand, and generate code from a curated knowledge base of developer documentation. It ingests documentation sources (text files, scraped JSON, URLs, or file uploads), chunks them intelligently, stores them as vector embeddings in ChromaDB, and uses an LLM to answer questions grounded in those documents.

The system has two user-facing interfaces — a **Next.js TypeScript frontend** (Admin Dashboard + Q&A Chat) and a **FastAPI REST API** — backed by a shared Python RAG pipeline.

---

## Table of Contents

- [Features](#features)
- [Architecture Overview](#architecture-overview)
- [How the RAG Pipeline Works](#how-the-rag-pipeline-works)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Frontend (Next.js)](#frontend-nextjs)
- [Backend (FastAPI)](#backend-fastapi)
- [Core Components Deep Dive](#core-components-deep-dive)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## Features

- **Semantic Documentation Search** — Vector similarity search across 10+ technology docs using ChromaDB + all-MiniLM-L6-v2 embeddings
- **AI-Powered Q&A** — Ask natural-language questions; the LLM answers grounded in retrieved documentation chunks
- **Code Generation** — Context-aware code generation using documentation as reference
- **Multi-Provider LLM** — Switch between Ollama (local), OpenAI, or Google Gemini at runtime
- **Admin Dashboard** — Browse, ingest, and remove documentation sources; add custom docs via URL scraping or file upload
- **Real-Time Ingestion Progress** — Frontend polls backend for step-by-step ingestion status
- **Web Search Augmentation** — Optionally augment answers with live web results (Firecrawl / DuckDuckGo)
- **Multi-Format Document Processing** — PDF, DOCX, PPTX, XLSX, CSV, TXT, MD, RTF, ODT
- **Smart Chunking** — Code-aware splitting that preserves code blocks, markdown headers, and API reference sections
- **Production Features** — Rate limiting, CORS, Prometheus metrics, structured logging, API key authentication
- **Dark/Light Mode** — Full theme support via next-themes

### Supported Documentation Sources (Pre-bundled)

| Technology | Category | Source Type |
|---|---|---|
| Python 3.13.5 | Language | Pre-embedded text |
| FastAPI | Framework | Pre-embedded text |
| Django 5.2 | Framework | Pre-embedded text |
| React & Next.js | Framework | Pre-embedded text |
| Node.js | Runtime | Pre-embedded text |
| PostgreSQL | Database | Pre-embedded text |
| MongoDB | Database | Pre-embedded text |
| TypeScript | Language | Pre-embedded text |
| LangChain | Framework | Pre-embedded text |
| Docker | Tool | Scraped JSON |

You can add more documentation sources through the Admin Dashboard (URL scraping or file upload).

---

## Architecture Overview

```
+-------------------------------------------------------------------+
|                        User Interfaces                            |
|                                                                   |
|  +-------------------------+     +-----------------------------+  |
|  |  Next.js Frontend       |     |  FastAPI REST API           |  |
|  |  (Port 3000)            |---->|  (Port 8100)               |  |
|  |                         |<----|                             |  |
|  |  - Landing Page   /     |     |  - /ask/enhanced            |  |
|  |  - Dashboard /dashboard |     |  - /generate-code/enhanced  |  |
|  |  - Q&A Chat  /qa        |     |  - /docs/catalog            |  |
|  +-------------------------+     |  - /docs/{id}/ingest        |  |
|                                  |  - /upload                  |  |
|                                  |  - /technologies            |  |
|                                  |  - /status, /metrics        |  |
|                                  +-------------+---------------+  |
+-----------------------------------------------|-------------------+
                                                |
                    +---------------------------v-----------------------+
                    |              Core RAG Pipeline                     |
                    |                                                    |
                    |  +------------+  +------------+  +-------------+  |
                    |  | DocRegistry|  | Ingestion  |  | SmartChunker|  |
                    |  |            |  | Pipeline   |  |             |  |
                    |  | catalog +  |  | fetch ->   |  | code-aware  |  |
                    |  | state mgmt |  | process -> |  | splitting   |  |
                    |  +------------+  | chunk ->   |  +-------------+  |
                    |                  | embed ->   |                    |
                    |                  | store      |                    |
                    |                  +------------+                    |
                    |                                                    |
                    |  +------------+  +------------+  +-------------+  |
                    |  | VectorStore|  | LLM Handler|  | Web Search  |  |
                    |  | (ChromaDB) |  | (Multi-    |  | (Firecrawl/ |  |
                    |  |            |  |  Provider) |  |  DuckDuckGo)|  |
                    |  | embeddings |  |            |  +-------------+  |
                    |  | + search   |  | Ollama /   |                    |
                    |  +------------+  | OpenAI /   |                    |
                    |                  | Gemini     |                    |
                    |                  +------------+                    |
                    +---------------------------------------------------+
```

---

## How the RAG Pipeline Works

This section explains the end-to-end data flow — from raw documentation to answering a user's question.

### Step 1: Documentation Catalog (`data/doc_catalog.json`)

All available documentation sources are defined in `data/doc_catalog.json`. Each entry specifies:
- `id` — unique key (e.g. `"python"`, `"fastapi"`)
- `source_type` — how to load it (`preembedded_file`, `scraped_json`, `web_scrape`, `file_upload`)
- `source_paths` — file paths or URLs to the raw content

The **DocRegistry** loads this catalog on startup, merges it with any saved runtime state (`data/registry_state.json`), and tracks which sources have been ingested.

### Step 2: Ingestion (Triggered via Dashboard or API)

When a user clicks "Ingest" on a documentation source:

1. **Load** — The IngestionPipeline reads raw content based on the source type:
   - `preembedded_file`: reads `.txt` files from `data/preembedded/`
   - `scraped_json`: reads pre-scraped `.json` files from `data/scraped/`
   - `web_scrape`: uses Firecrawl to crawl a URL
   - `file_upload`: uses EnhancedDocumentProcessor to parse PDF/DOCX/etc.

2. **Chunk** — The SmartChunker splits each document into overlapping chunks (~1000 chars each). It detects content type and uses different strategies:
   - **Code blocks** (``` ``` ```) are preserved intact and split with a Python-aware splitter
   - **API references** are split by section headers (`###`)
   - **Plain text** is split by paragraphs, sentences, then words

   Each chunk gets metadata: `technology`, `source`, `chunk_type`, `chunk_id` (MD5 hash), `chunk_position`, etc.

3. **Embed & Store** — Chunks are sent to ChromaDB, which uses `all-MiniLM-L6-v2` (384-dim sentence-transformer) to generate vector embeddings. The `CachedEmbeddingFunction` wrapper caches embeddings to avoid recomputing them. Metadata is stored alongside each vector for filtering.

4. **Update Registry** — The DocRegistry updates the source's status to `completed` with the chunk count, and persists to `data/registry_state.json`.

### Step 3: Question Answering

When a user asks a question via the Q&A interface:

1. **Search** — The query is sent to ChromaDB's `collection.query()`, which embeds the query and finds the top-K most similar document chunks. Optional filters narrow results to a specific technology.

2. **Augment** — If web search is enabled, additional results from Firecrawl/DuckDuckGo are appended.

3. **Generate** — The retrieved chunks (context) + the user's question are sent to the LLM provider (Ollama/OpenAI/Gemini). The LLM generates an answer grounded in the documentation context.

4. **Return** — The answer, source chunks, response time, and provider info are returned to the frontend.

---

## Tech Stack

### Frontend
| Technology | Purpose |
|---|---|
| Next.js 14 (App Router) | React framework with server components |
| TypeScript | Type-safe frontend code |
| shadcn/ui | Component library (Radix UI primitives) |
| Tailwind CSS | Utility-first styling |
| next-themes | Dark/light mode |
| lucide-react | Icons |

### Backend
| Technology | Purpose |
|---|---|
| FastAPI | REST API framework |
| Uvicorn | ASGI server |
| Pydantic / pydantic-settings | Settings management and validation |
| slowapi | Rate limiting |
| prometheus-client | Metrics endpoint |

### AI / ML
| Technology | Purpose |
|---|---|
| ChromaDB | Vector database (persistent, SQLite-backed) |
| sentence-transformers (all-MiniLM-L6-v2) | Text to 384-dim embeddings |
| LangChain text splitters | Code-aware and markdown-aware chunking |
| Ollama (gemma2:2b) | Default local LLM |
| OpenAI (gpt-3.5-turbo) | Optional cloud LLM |
| Google Gemini (gemini-pro) | Optional cloud LLM |

### Document Processing
| Library | Formats |
|---|---|
| pypdf | PDF |
| python-docx | DOCX |
| python-pptx | PPTX |
| pandas + openpyxl | CSV, XLSX, XLS |
| Built-in | TXT, MD, RTF, ODT |

---

## Quick Start

### Prerequisites

- **Python 3.10+** (tested with 3.13/3.14)
- **Node.js 18+** and npm
- **Ollama** (for local LLM) — or set `OPENAI_API_KEY` / `GEMINI_API_KEY` for cloud LLMs
- 2GB+ RAM for the embedding model and vector database

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/Shashank-Singh90/DocuMentor.git
cd DocuMentor

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Install frontend dependencies
cd frontend && npm install && cd ..

# 4. Configure environment
cp .env.example .env
# Edit .env with your settings (Ollama host, API keys, etc.)

# 5. Set up Ollama (if using local LLM)
ollama pull gemma2:2b
```

### Running

```bash
# Option 1: Launch both servers (recommended)
python launcher.py
# -> FastAPI on http://127.0.0.1:8100
# -> Next.js on http://127.0.0.1:3000

# Option 2: Start backend only
python api_server.py

# Option 3: Start frontend only
cd frontend && npm run dev
```

### First-Time Usage

1. Open **http://localhost:3000** — the landing page shows backend connection status
2. Go to **Dashboard** (`/dashboard`) — you'll see the 10 pre-bundled documentation sources
3. Click **Ingest** on any source (e.g. Python) — this chunks the docs and stores embeddings in ChromaDB
4. Go to **Q&A** (`/qa`) — ask a question like "How do list comprehensions work in Python?"
5. The system retrieves relevant chunks, sends them with your question to the LLM, and returns a grounded answer

---

## Project Structure

```
DocuMentor/
├── frontend/                          # Next.js TypeScript frontend
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx             # Root layout (Navbar + ThemeProvider)
│   │   │   ├── page.tsx               # Landing page with system status
│   │   │   ├── dashboard/page.tsx     # Admin dashboard
│   │   │   └── qa/page.tsx            # Q&A chat interface
│   │   ├── components/
│   │   │   ├── ui/                    # shadcn/ui primitives (Button, Card, etc.)
│   │   │   ├── layout/               # Navbar, ThemeProvider
│   │   │   ├── dashboard/            # DocCard, CatalogGrid, AddUrlForm,
│   │   │   │                         # FileUploadForm, StatsPanel
│   │   │   └── qa/                   # ChatInterface, MessageBubble,
│   │   │                             # SourceCitations, SettingsSidebar
│   │   ├── lib/
│   │   │   ├── api.ts                # All fetch calls to FastAPI backend
│   │   │   └── types.ts              # TypeScript types mirroring Pydantic models
│   │   └── hooks/
│   │       ├── useDocSources.ts      # Catalog fetch + ingest/remove actions
│   │       ├── useIngestion.ts       # Progress polling (1.5s interval)
│   │       └── useChat.ts            # Chat state + sendMessage + clearChat
│   ├── package.json
│   └── tailwind.config.ts
│
├── rag_system/                        # Python backend package
│   ├── api/
│   │   ├── __init__.py               # Lazy app import (get_app())
│   │   ├── server.py                 # FastAPI app factory + all endpoints
│   │   └── middleware/
│   │       ├── auth.py               # API key authentication
│   │       └── validation.py         # Input sanitization & validation
│   │
│   ├── config/
│   │   └── settings.py               # Pydantic Settings (loads from .env)
│   │
│   ├── core/
│   │   ├── __init__.py               # Lazy imports via __getattr__
│   │   ├── constants.py              # All magic numbers in one place
│   │   ├── registry/                 # Documentation catalog management
│   │   │   ├── models.py             # DocSource, IngestionStatus, DocSourceType
│   │   │   └── registry.py           # DocRegistry class
│   │   ├── ingestion/                # Ingestion pipeline
│   │   │   └── pipeline.py           # IngestionPipeline class
│   │   ├── chunking/                 # Document chunking
│   │   │   └── chunker.py            # SmartChunker class
│   │   ├── retrieval/                # Vector store
│   │   │   └── vector_store.py       # ChromaVectorStore + CachedEmbeddingFunction
│   │   ├── generation/               # LLM providers
│   │   │   └── llm_handler.py        # EnhancedLLMHandler + provider classes
│   │   ├── processing/               # File format processing
│   │   │   └── document_processor.py # EnhancedDocumentProcessor
│   │   ├── search/                   # Web search
│   │   │   └── web_search.py         # WebSearchProvider
│   │   └── utils/
│   │       ├── logger.py             # Structured logging with rotation
│   │       ├── cache.py              # ResponseCache (LRU + SHA256 keys)
│   │       ├── embedding_cache.py    # EmbeddingCache (NumPy serialization)
│   │       └── metrics.py            # Prometheus metrics helpers
│
├── data/
│   ├── doc_catalog.json              # Documentation source definitions
│   ├── registry_state.json           # Runtime ingestion state (auto-managed)
│   ├── preembedded/                  # Pre-bundled documentation text files
│   ├── scraped/                      # Pre-scraped documentation JSON files
│   ├── chroma_db/                    # ChromaDB persistent storage
│   ├── cache/                        # Response cache
│   ├── uploads/                      # Uploaded files
│   └── embeddings_cache/             # Cached embedding vectors
│
├── tests/                            # Test suite (167 tests)
│   ├── conftest.py                   # Shared fixtures
│   ├── test_api_endpoints.py         # 38 FastAPI endpoint tests
│   ├── test_registry.py              # 20 registry tests
│   ├── test_chunker.py               # 14 chunker tests
│   ├── test_vector_store.py          # 15 vector store tests (real ChromaDB)
│   ├── test_ingestion.py             # 13 ingestion pipeline tests
│   ├── test_llm_handler.py           # 11 LLM handler tests
│   ├── test_cache.py                 # Cache tests
│   ├── test_auth.py                  # Authentication tests
│   └── test_validation.py            # Input validation tests
│
├── launcher.py                       # Launches both FastAPI + Next.js
├── api_server.py                     # Launches FastAPI only (uvicorn)
├── main.py                           # Info/help entry point
├── requirements.txt                  # Python dependencies
├── .env.example                      # Environment variable template
└── CLAUDE.md                         # AI assistant instructions
```

---

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and edit:

```bash
# --- Core ---
DEBUG=false                          # true/false/1/0/yes/no
DEFAULT_LLM_PROVIDER=ollama          # ollama | openai | gemini

# --- Ollama (Local LLM) ---
OLLAMA_HOST=localhost:11434
OLLAMA_MODEL=gemma2:2b               # Fast 2B param model
OLLAMA_TIMEOUT=120                   # Generous timeout for slow models

# --- Cloud LLM Keys (Optional) ---
OPENAI_API_KEY=sk-...                # For OpenAI provider
GEMINI_API_KEY=...                   # For Google Gemini provider

# --- Vector Database ---
CHROMA_PERSIST_DIRECTORY=./data/chroma_db
COLLECTION_NAME=documents
EMBEDDING_MODEL=all-MiniLM-L6-v2

# --- Chunking ---
CHUNK_SIZE=1000                      # Characters per chunk
CHUNK_OVERLAP=200                    # Overlap between chunks

# --- Security ---
API_KEY=                             # Set for production (min 16 chars)
CORS_ORIGINS=http://localhost:3000,http://localhost:8501

# --- Web Search (Optional) ---
FIRECRAWL_API_KEY=
ENABLE_WEB_SEARCH=true
```

See `.env.example` for the complete list of all configurable options.

### Frontend Configuration

Create `frontend/.env.local`:
```bash
NEXT_PUBLIC_API_URL=http://127.0.0.1:8100
```

### Ollama Setup

```bash
# Install Ollama (https://ollama.ai)
# Then pull the default model:
ollama pull gemma2:2b

# Verify it's running:
curl http://localhost:11434/api/version
```

---

## Frontend (Next.js)

The frontend is a Next.js 14 App Router application in `frontend/`.

### Pages

| Route | Component | Purpose |
|---|---|---|
| `/` | `page.tsx` | Landing page — system status, feature cards, navigation |
| `/dashboard` | `dashboard/page.tsx` | Admin — catalog grid, ingest/remove buttons, add custom docs, stats |
| `/qa` | `qa/page.tsx` | Chat interface — settings sidebar + message thread |

### Key Components

**Dashboard:**
- `CatalogGrid` — renders a grid of `DocCard` components (one per documentation source)
- `DocCard` — shows source name, icon, status badge, ingest/remove buttons
- `AddUrlForm` — form to add a custom documentation source from a URL
- `FileUploadForm` — drag-and-drop file upload with multipart/form-data
- `StatsPanel` — displays knowledge base statistics from `/status`

**Q&A:**
- `ChatInterface` — message thread with auto-scroll, textarea input, send/clear buttons
- `MessageBubble` — renders user/assistant messages with markdown support
- `SourceCitations` — expandable list of source chunks that informed the answer
- `SettingsSidebar` — controls for LLM provider, response mode, technology filter, search K, web search toggle

### Custom Hooks

- `useDocSources()` — fetches catalog, provides `triggerIngest(docId)` and `triggerRemove(docId)` with optimistic UI updates
- `useIngestionProgress(docId, active)` — polls `/docs/{id}/progress` every 1.5s while active, auto-stops on completion/failure
- `useChat()` — manages chat messages array, `sendMessage(content, options)` dispatches to `/ask/enhanced` or `/generate-code/enhanced`, handles loading/error states

### API Client (`lib/api.ts`)

All backend communication goes through typed fetch wrappers:
```typescript
getCatalog()                    // GET /docs/catalog
ingestDoc(docId)               // POST /docs/{id}/ingest
removeDoc(docId)               // DELETE /docs/{id}
askQuestion(req)               // POST /ask/enhanced
generateCode(req)              // POST /generate-code/enhanced
uploadDocument(file, source)   // POST /upload (multipart)
getSystemStatus()              // GET /status
```

---

## Backend (FastAPI)

### Entry Points

| Script | What it does |
|---|---|
| `python launcher.py` | Starts FastAPI (port 8100) + Next.js (port 3000) with health checks |
| `python api_server.py` | Starts FastAPI only via uvicorn |
| `cd frontend && npm run dev` | Starts Next.js only |

### Server Architecture (`rag_system/api/server.py`)

The FastAPI app is created via `create_enhanced_fastapi_app()` — a factory function that:
1. **Defers heavy imports** — ChromaDB, LLM handlers, embedding models are imported inside the factory, not at module level. This prevents unit tests from bootstrapping the entire system when they import from the API package.
2. **Creates singleton components** — `VectorStore()`, `SmartChunker()`, `DocRegistry()`, `IngestionPipeline()`
3. **Registers middleware** — CORS, rate limiting
4. **Defines all endpoints** — Q&A, code gen, document management, status, metrics

The `app` module attribute is **lazy** — accessed via `__getattr__` so it's only created when first needed (e.g. by uvicorn).

### Middleware

- **CORS** — Allows origins from `settings.cors_origins` (default: `localhost:3000`)
- **Rate Limiting** — slowapi with per-endpoint limits (60/min search, 30/min query, 10/min upload, 20/min code gen)
- **Authentication** — Optional API key via `X-API-Key` header (set `API_KEY` env var)
- **Validation** — Input sanitization for queries, filenames, and parameters

---

## Core Components Deep Dive

### DocRegistry (`rag_system/core/registry/`)

**Purpose:** Manages the catalog of available documentation sources and their ingestion state.

- Loads `data/doc_catalog.json` (static catalog) on startup
- Merges with `data/registry_state.json` (runtime state — statuses, chunk counts, timestamps)
- Supports custom sources added via Dashboard (URL scrape or file upload)
- `get_all_sources()` returns all sources; `get_ingested_sources()` returns only completed ones
- `update_status(doc_id, status, chunk_count)` updates state and saves to disk
- `get_all_technology_mapping()` returns `{doc_id: display_name}` for API filtering

**Data Model (`DocSource`):**
```python
class DocSource(BaseModel):
    id: str                        # "python", "fastapi", etc.
    name: str                      # "Python 3.13.5"
    category: str                  # "language", "framework", "database", "tool"
    source_type: DocSourceType     # preembedded_file | scraped_json | web_scrape | file_upload
    source_paths: List[str]        # file paths or URLs
    status: IngestionStatus        # not_started | in_progress | completed | failed
    chunk_count: int               # number of chunks stored in ChromaDB
    last_ingested: Optional[datetime]
    error_message: Optional[str]
```

### SmartChunker (`rag_system/core/chunking/chunker.py`)

**Purpose:** Splits documents into overlapping chunks optimized for vector search.

- Default: 1000 chars per chunk, 200 char overlap
- Uses LangChain's `RecursiveCharacterTextSplitter` under the hood
- Three splitting strategies based on content detection:
  1. **Mixed content** (has code fences) — preserves code blocks as single chunks; splits surrounding text separately
  2. **API reference** (doc_type == `api_reference`) — splits by `###` section headers
  3. **Plain text** — recursive split by paragraphs, then sentences, then words
- Each chunk gets a 16-char MD5 `chunk_id` for deduplication
- Parallel processing using `ThreadPoolExecutor` for batch operations

**Chunk format:**
```python
{
    "content": "The actual text of this chunk...",
    "metadata": {
        "technology": "python",
        "source": "comprehensive_docs",
        "chunk_type": "text",       # text | code | api_reference
        "chunk_id": "a1b2c3d4e5f67890",
        "chunk_position": 3,
        "total_chunks": 42,
        "chunk_size": 987,
        "word_count": 156
    }
}
```

### ChromaVectorStore (`rag_system/core/retrieval/vector_store.py`)

**Purpose:** Stores document chunks as vector embeddings and performs semantic similarity search.

- Uses ChromaDB `PersistentClient` (SQLite-backed, stored at `data/chroma_db/`)
- Embedding model: `all-MiniLM-L6-v2` (384 dimensions) via sentence-transformers
- `CachedEmbeddingFunction` wraps the base embedder with a cache layer to avoid recomputing embeddings
- **File locking** (`filelock`) prevents concurrent write corruption
- **Corrupted DB recovery** — if `PersistentClient()` crashes (e.g. incompatible SQLite), the DB is automatically wiped and recreated

**Key methods:**
- `add_documents(texts, metadatas, ids)` — batch upsert with retry logic, data sanitization (null bytes, None values)
- `search(query, k=5, filter_dict=None)` — semantic search, returns `[{content, metadata, score}]`
- `get_collection_stats()` — returns `{total_chunks, sources: {name: count}, sample_size}`

### IngestionPipeline (`rag_system/core/ingestion/pipeline.py`)

**Purpose:** Orchestrates the full ingestion flow: load -> chunk -> embed -> store.

Four-step pipeline:
1. **Load documents** — dispatches to loader based on `source_type`
2. **Chunk documents** — calls `SmartChunker.chunk_document()` per doc (avoids asyncio conflicts)
3. **Prepare metadata** — ensures every chunk has `technology: doc_id` and `source` fields
4. **Store in ChromaDB** — calls `vector_store.add_documents()`

Also supports:
- `remove_source(doc_id)` — deletes chunks from ChromaDB by `technology` metadata filter
- `get_progress(doc_id)` — returns step/total_steps/message for UI polling
- `ingest_from_url(url, name, doc_id)` — registers a custom source and ingests it
- `ingest_source_background(doc_id)` — runs ingestion in a daemon thread

### EnhancedLLMHandler (`rag_system/core/generation/llm_handler.py`)

**Purpose:** Multi-provider LLM interface with automatic fallback.

- Three provider classes, all implementing `BaseLLMProvider`:
  - `OllamaProvider` — HTTP calls to `http://localhost:11434/api/generate`
  - `OpenAIProvider` — OpenAI v1.x client (`gpt-3.5-turbo`)
  - `GeminiProvider` — Google Generative AI (`gemini-pro`)
- `generate_answer(question, search_results)` — builds context from top-3 search results, sends to current provider
- `generate_code(prompt, language, context)` — specialized code generation prompt
- `set_provider(name)` switches active provider; `get_available_providers()` lists working ones
- **Automatic fallback** — if the current provider is unavailable, tries the first available alternative
- **Global singleton**: `enhanced_llm_handler = EnhancedLLMHandler()`

### WebSearchProvider (`rag_system/core/search/web_search.py`)

**Purpose:** Augments RAG answers with live web results.

Search cascade:
1. **Firecrawl** (local instance) — highest quality, requires API key
2. **DuckDuckGo HTML scraping** — free, no API key
3. **DuckDuckGo Instant Answer API** — free fallback
4. **Hardcoded fallback** — generic guidance when all services are down

### EnhancedDocumentProcessor (`rag_system/core/processing/document_processor.py`)

**Purpose:** Extracts text content from uploaded files.

Supported formats with specialized handlers:
- `.txt`, `.md` — direct text read (UTF-8 with Latin-1 fallback)
- `.pdf` — page-by-page extraction via pypdf
- `.docx` — paragraph + table extraction via python-docx
- `.pptx` — slide-by-slide via python-pptx
- `.csv` — summary + preview via pandas
- `.xlsx`, `.xls` — sheet-by-sheet via pandas
- `.rtf` — basic RTF tag stripping
- `.odt` — XML extraction from ZIP container

### Settings (`rag_system/config/settings.py`)

Pydantic `BaseSettings` class that loads from `.env` file:
- Validates all configuration on startup
- Custom `field_validator` for `DEBUG` env var (handles non-boolean values like `"release"`)
- Creates required directories on first access
- Global singleton via `get_settings()`

### Lazy Import Pattern

To avoid import-time side effects (bootstrapping ChromaDB, LLM handlers, etc. when running tests), the codebase uses lazy loading:

- `rag_system/core/__init__.py` — `__getattr__` defers imports of heavy components
- `rag_system/api/__init__.py` — `get_app()` function instead of eager `from .server import app`
- `rag_system/api/server.py` — app singleton via module `__getattr__`, heavy imports inside factory function

---

## API Reference

### General

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | API info and feature list |
| GET | `/status` | System status (providers, chunk count, technologies) |
| GET | `/metrics` | Prometheus-compatible metrics |

### Q&A

| Method | Endpoint | Description |
|---|---|---|
| POST | `/ask/enhanced` | Ask a question with filtering and mode options |
| POST | `/ask` | Legacy alias for `/ask/enhanced` |
| POST | `/technology-query` | Query within a specific technology context |

**POST /ask/enhanced** request body:
```json
{
  "question": "How do I create a FastAPI endpoint?",
  "search_k": 8,
  "enable_web_search": false,
  "response_mode": "smart_answer",
  "technology_filter": "fastapi",
  "temperature": 0.3,
  "max_tokens": 800
}
```

Response modes: `smart_answer` | `code_generation` | `detailed_sources`

### Code Generation

| Method | Endpoint | Description |
|---|---|---|
| POST | `/generate-code/enhanced` | Generate code with documentation context |

### Documentation Management

| Method | Endpoint | Description |
|---|---|---|
| GET | `/docs/catalog` | List all documentation sources with status |
| GET | `/docs/ingested` | List only ingested sources |
| GET | `/docs/{id}/status` | Get status of a specific source |
| POST | `/docs/{id}/ingest` | Trigger ingestion of a source |
| DELETE | `/docs/{id}` | Remove source from knowledge base |
| GET | `/docs/{id}/progress` | Get ingestion progress (for polling) |
| POST | `/docs/custom` | Add a custom source from URL |

### Technologies

| Method | Endpoint | Description |
|---|---|---|
| GET | `/technologies` | List all technologies with availability |
| GET | `/technologies/{tech}/stats` | Detailed stats for a technology |

### File Upload

| Method | Endpoint | Description |
|---|---|---|
| POST | `/upload` | Upload and process a document file |

### Rate Limits

| Endpoint Category | Limit |
|---|---|
| Search | 60/minute |
| Query (Q&A) | 30/minute |
| Code Generation | 20/minute |
| Upload | 10/minute |

### Interactive API Docs

When the backend is running, visit:
- **Swagger UI**: http://127.0.0.1:8100/docs
- **ReDoc**: http://127.0.0.1:8100/redoc

### Usage Examples

**Python:**
```python
import requests

API_URL = "http://127.0.0.1:8100"

# Ask a question
response = requests.post(f"{API_URL}/ask/enhanced", json={
    "question": "How do I use async/await in Python?",
    "search_k": 5,
    "response_mode": "smart_answer",
    "technology_filter": "python"
})
print(response.json()["answer"])

# Generate code
response = requests.post(f"{API_URL}/generate-code/enhanced", json={
    "prompt": "Create a PostgreSQL connection pool",
    "language": "python",
    "technology": "postgresql",
    "style": "complete"
})
print(response.json()["code"])

# Upload a document
with open("my_docs.pdf", "rb") as f:
    response = requests.post(f"{API_URL}/upload",
        files={"file": f},
        data={"source": "custom_docs"})
print(response.json())
```

**cURL:**
```bash
# Ask a question
curl -X POST "http://127.0.0.1:8100/ask/enhanced" \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I create a React component?", "technology_filter": "react_nextjs"}'

# Upload document
curl -X POST "http://127.0.0.1:8100/upload" -F "file=@document.pdf" -F "source=my_docs"

# Get system status
curl "http://127.0.0.1:8100/status"
```

---

## Testing

The test suite has **167 tests** covering all backend components.

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_registry.py -v

# Run with short traceback
pytest tests/ --tb=short
```

### Test Files

| File | Tests | What it covers |
|---|---|---|
| `test_api_endpoints.py` | 38 | All FastAPI endpoints via TestClient (mocked components) |
| `test_registry.py` | 20 | DocRegistry init, CRUD, custom sources, persistence |
| `test_vector_store.py` | 15 | Real ephemeral ChromaDB: add, search, filter, stats |
| `test_chunker.py` | 14 | SmartChunker: text, code, mixed content, metadata |
| `test_ingestion.py` | 13 | IngestionPipeline with mocked dependencies |
| `test_llm_handler.py` | 11 | EnhancedLLMHandler: providers, fallback, code gen |
| `test_cache.py` | - | Response cache: get/set, TTL, persistence |
| `test_auth.py` | - | API key authentication middleware |
| `test_validation.py` | - | Input sanitization: queries, filenames, parameters |

---

## Deployment

### Production Checklist

1. Set `DEBUG=false` and `API_KEY=<secure-key>` in `.env`
2. Set specific `CORS_ORIGINS` (not wildcards)
3. Build the frontend: `cd frontend && npm run build`
4. Use a process manager (systemd, PM2, or Docker)
5. Put behind a reverse proxy (Nginx) for HTTPS
6. Monitor via `/metrics` endpoint (Prometheus + Grafana)

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8100 3000
CMD ["python", "launcher.py"]
```

```bash
docker build -t documentor .
docker run -d -p 8100:8100 -p 3000:3000 \
  -v $(pwd)/data:/app/data \
  --env-file .env \
  documentor
```

---

## Troubleshooting

**Backend won't start / ChromaDB crash:**
The system auto-recovers from corrupted ChromaDB databases. If it still fails, delete `data/chroma_db/` and re-ingest.

**"Cannot connect to backend" on frontend:**
Ensure FastAPI is running on port 8100. Check `frontend/.env.local` has `NEXT_PUBLIC_API_URL=http://127.0.0.1:8100`.

**Ollama not available:**
```bash
ollama serve              # Start Ollama daemon
ollama pull gemma2:2b     # Pull the model
curl http://localhost:11434/api/version  # Verify
```

**Slow responses:**
- Reduce `search_k` (fewer chunks to process)
- Use `gemma2:2b` (fast) instead of larger models
- Enable caching — repeated queries are served from cache

**DEBUG env var crash:**
The `DEBUG` setting accepts `true`/`false`/`1`/`0`/`yes`/`no`. Any other value (like `release`) is treated as `false`.

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make changes with tests (`pytest tests/ -v`)
4. Commit and push
5. Open a Pull Request

---

## License

MIT License — see LICENSE file for details.

---

**Built by Shashank Singh** | Version 2.0.0
