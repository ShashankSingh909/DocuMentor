"""
Unit tests for response caching
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from rag_system.core.utils.cache import ResponseCache


class TestResponseCache:
    """Tests for response caching functionality"""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create a temporary directory for cache testing"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def cache(self, temp_cache_dir):
        """Create a ResponseCache instance for testing"""
        return ResponseCache(cache_dir=temp_cache_dir, max_cache_size=10)

    def test_cache_initialization(self, cache, temp_cache_dir):
        """Test that cache initializes correctly"""
        assert cache.cache_dir == Path(temp_cache_dir)
        assert cache.max_cache_size == 10
        assert len(cache.cache) == 0

    def test_cache_miss(self, cache):
        """Test that cache returns None for non-existent entries"""
        result = cache.get("test query", [])
        assert result is None

    def test_cache_set_and_get(self, cache):
        """Test that cached responses can be retrieved"""
        query = "test query"
        search_results = [{"content": "test content"}]
        response = "This is a test response"

        cache.set(query, search_results, response)
        result = cache.get(query, search_results)

        assert result == response

    def test_cache_key_generation_uses_sha256(self, cache):
        """Test that cache keys are generated using SHA256"""
        query = "test query"
        search_results = [{"content": "test"}]

        # Generate a cache key
        cache.set(query, search_results, "response")

        # Verify that the cache key is a hex string (SHA256 produces hex)
        cache_key = cache._generate_cache_key(query, search_results)
        assert len(cache_key) == 64  # SHA256 produces 64 character hex string
        assert all(c in '0123456789abcdef' for c in cache_key)

    def test_cache_normalization(self, cache):
        """Test that queries are normalized for caching"""
        query1 = "Test Query"
        query2 = "test query"
        search_results = [{"content": "test"}]
        response = "This is a sufficiently long response for caching"

        cache.set(query1, search_results, response)
        result = cache.get(query2, search_results)

        # Should get hit because queries are normalized
        assert result == response

    def test_cache_eviction(self, cache):
        """Test that cache evicts oldest entries when full"""
        search_results = [{"content": "test"}]

        # Fill cache to max
        for i in range(11):
            cache.set(f"query {i}", search_results, f"response {i}")

        # Cache should be at max size
        assert len(cache.cache) == 10

        # First entry should have been evicted
        result = cache.get("query 0", search_results)
        assert result is None

    def test_cache_does_not_store_short_responses(self, cache):
        """Test that very short responses are not cached"""
        query = "test"
        search_results = [{"content": "test"}]
        short_response = "short"

        cache.set(query, search_results, short_response)
        result = cache.get(query, search_results)

        assert result is None

    def test_cache_clear(self, cache):
        """Test that cache can be cleared"""
        query = "test query"
        search_results = [{"content": "test"}]
        response = "This is a sufficiently long response for caching"

        cache.set(query, search_results, response)
        assert len(cache.cache) > 0

        cache.clear()
        assert len(cache.cache) == 0

    def test_cache_persistence(self, temp_cache_dir):
        """Test that cache persists to disk"""
        cache1 = ResponseCache(cache_dir=temp_cache_dir)
        query = "test query"
        search_results = [{"content": "test content"}]
        response = "This is a test response"

        cache1.set(query, search_results, response)
        cache1._save_cache()

        # Create new cache instance with same directory
        cache2 = ResponseCache(cache_dir=temp_cache_dir)
        result = cache2.get(query, search_results)

        assert result == response

    def test_cache_stats(self, cache):
        """Test that cache statistics are correct"""
        stats = cache.get_stats()

        assert "total_entries" in stats
        assert "max_size" in stats
        assert "cache_dir" in stats
        assert stats["total_entries"] == 0
        assert stats["max_size"] == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
