"""
Shared pytest fixtures and configuration for DocuMentor test suite.
"""
import pytest
import tempfile
import shutil
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure project root is on sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# ─── Basic data fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def sample_query():
    return "How do I create a FastAPI endpoint?"


@pytest.fixture
def sample_search_results():
    return [
        {
            "content": "FastAPI is a modern web framework for Python.",
            "metadata": {"technology": "fastapi", "source": "fastapi_docs", "title": "Intro"},
            "score": 0.95,
        },
        {
            "content": "To create an endpoint, use @app.get() decorator.",
            "metadata": {"technology": "fastapi", "source": "fastapi_tutorial", "title": "Routing"},
            "score": 0.87,
        },
    ]


@pytest.fixture
def sample_api_key():
    return "test-api-key-1234567890abcdef"


@pytest.fixture
def sample_chunk():
    return {
        "content": "Python is a high-level programming language.",
        "metadata": {
            "technology": "python",
            "source": "comprehensive_docs",
            "chunk_index": 0,
            "total_chunks": 5,
            "content_type": "text_content",
        },
        "chunk_id": "abc123",
    }


# ─── Temp directory fixtures ──────────────────────────────────────────────────

@pytest.fixture
def temp_dir():
    d = tempfile.mkdtemp()
    yield Path(d)
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def temp_cache_dir(temp_dir):
    cache = temp_dir / "cache"
    cache.mkdir()
    return cache


# ─── Registry fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def sample_catalog_data():
    return [
        {
            "id": "python",
            "name": "Python",
            "category": "language",
            "icon": "🐍",
            "source_type": "preembedded_file",
            "source_paths": ["data/preembedded/python_docs.txt"],
        },
        {
            "id": "fastapi",
            "name": "FastAPI",
            "category": "framework",
            "icon": "⚡",
            "source_type": "preembedded_file",
            "source_paths": ["data/preembedded/fastapi_docs.txt"],
        },
    ]


@pytest.fixture
def temp_catalog_file(temp_dir, sample_catalog_data):
    catalog_path = temp_dir / "doc_catalog.json"
    catalog_path.write_text(json.dumps(sample_catalog_data))
    return catalog_path


@pytest.fixture
def temp_state_file(temp_dir):
    return temp_dir / "registry_state.json"


# ─── Document fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def sample_documents():
    return [
        {
            "content": "Python is great for data science and web development.",
            "metadata": {"technology": "python", "source": "comprehensive_docs"},
        },
        {
            "content": "FastAPI provides automatic OpenAPI documentation generation.",
            "metadata": {"technology": "fastapi", "source": "comprehensive_docs"},
        },
        {
            "content": "```python\ndef hello():\n    return 'Hello World'\n```",
            "metadata": {"technology": "python", "source": "code_examples"},
        },
    ]


@pytest.fixture
def api_doc_content():
    """Content that triggers API documentation chunking strategy."""
    return """# FastAPI Reference

## GET /items
Returns a list of items.

**Parameters:**
- `skip` (int): Number of items to skip
- `limit` (int): Maximum items to return

## POST /items
Create a new item.

**Request Body:**
```json
{"name": "string", "price": 0}
```

## DELETE /items/{item_id}
Delete an item by ID.
"""


@pytest.fixture
def code_content():
    """Content that triggers mixed/code chunking strategy."""
    return """# Python Guide

## Functions

```python
def add(a, b):
    return a + b

class Calculator:
    def multiply(self, x, y):
        return x * y
```

## Decorators

```python
import functools

def my_decorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper
```
"""


@pytest.fixture
def plain_text_content():
    """Content that triggers plain text chunking strategy."""
    return " ".join(["This is a sentence about Python programming."] * 100)
