# DocuMentor - AI Documentation Assistant for Developers

## Architecture

Two-interface RAG system:
- **Admin Dashboard** (`frontend/src/app/dashboard/`): Next.js page — manage documentation sources, trigger ingestion, upload files
- **Q&A Frontend** (`frontend/src/app/qa/`): Next.js page — ask questions about ingested documentation
- **REST API** (FastAPI, port 8100): Programmatic access to all functionality

### Frontend Stack
- **Framework**: Next.js 14 (App Router)
- **UI**: shadcn/ui + Tailwind CSS
- **Language**: TypeScript
- **Location**: `frontend/` at project root

### Core Pipeline

1. **Registry** (`rag_system/core/registry/`) — Tracks available and ingested doc sources
2. **Ingestion** (`rag_system/core/ingestion/`) — Orchestrates: fetch -> process -> chunk -> embed -> store
3. **Chunking** (`rag_system/core/chunking/`) — SmartChunker with code-aware splitting
4. **Vector Store** (`rag_system/core/retrieval/`) — ChromaDB + all-MiniLM-L6-v2 embeddings
5. **Generation** (`rag_system/core/generation/`) — Multi-provider LLM (Ollama/OpenAI/Gemini)
6. **Web Search** (`rag_system/core/search/`) — Firecrawl/DuckDuckGo augmentation

### File Structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx        — Root layout (Navbar + ThemeProvider)
│   │   ├── page.tsx          — Landing page
│   │   ├── dashboard/page.tsx — Admin dashboard
│   │   └── qa/page.tsx       — Q&A interface
│   ├── components/
│   │   ├── ui/               — shadcn/ui primitives
│   │   ├── layout/           — Navbar, ThemeProvider
│   │   ├── dashboard/        — DocCard, CatalogGrid, AddUrlForm, FileUploadForm, StatsPanel
│   │   └── qa/               — ChatInterface, MessageBubble, SourceCitations, SettingsSidebar
│   ├── lib/
│   │   ├── api.ts            — All fetch calls to FastAPI (BASE_URL: http://127.0.0.1:8100)
│   │   └── types.ts          — TypeScript types mirroring FastAPI Pydantic models
│   └── hooks/
│       ├── useDocSources.ts  — Catalog fetch + ingest/remove actions
│       ├── useIngestion.ts   — Progress polling (1.5s interval)
│       └── useChat.ts        — Chat state + sendMessage + clearChat

data/doc_catalog.json         — Available documentation sources (add new docs here)
data/registry_state.json      — Runtime ingestion state (auto-managed)
data/preembedded/             — Pre-bundled documentation text files
data/scraped/                 — Pre-scraped documentation JSON files
rag_system/api/server.py      — FastAPI REST API (port 8100)
```

## Development

### Running

```bash
# Start both servers (recommended)
python launcher.py

# Start FastAPI backend only (port 8100)
python api_server.py

# Start Next.js frontend only (port 3000)
cd frontend && npm run dev

# Build frontend for production
cd frontend && npm run build
```

### Adding New Documentation Sources

1. Add entry to `data/doc_catalog.json` with source_type and paths/URLs
2. Or use the Admin Dashboard UI to add via URL scraping or file upload

### Key Conventions

- All chunk metadata MUST include `technology: <doc_id>` and `source: <source_name>`
- Use `SmartChunker.chunk_document()` (singular) in async contexts, not `chunk_documents()`
- ChromaDB filter pattern: `{"technology": doc_id}` for technology-specific search
- Settings via `.env` file or environment variables (see `.env.example`)
- Default LLM: Ollama with gemma2:2b (configure in .env)
- Frontend API base URL configured in `frontend/.env.local` (`NEXT_PUBLIC_API_URL`)
- CORS: FastAPI allows `http://localhost:3000` (Next.js dev port) — see `rag_system/config/settings.py`

### Testing

- `pytest tests/` — Run backend tests
- Test ingestion: Dashboard (http://localhost:3000/dashboard) -> Add docs -> verify chunk count
- Test Q&A: Q&A page (http://localhost:3000/qa) -> Ask a question -> verify answer references correct sources
