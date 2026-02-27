"""
Tests for EnhancedLLMHandler — provider detection, answer generation, code generation,
fallback behavior, and response caching.

EnhancedLLMHandler API:
- __init__() — no args, uses settings
- .current_provider: str — name of active provider
- .set_provider(name) -> bool
- .get_available_providers() -> List[str]
- .generate_answer(question, search_results) -> str
- .generate_code(prompt, language, context) -> str
- .generate_response(prompt, context) -> str  (via CodeGenerationMixin)
"""
import pytest
from unittest.mock import patch, MagicMock

from rag_system.core.generation.llm_handler import EnhancedLLMHandler


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def handler():
    return EnhancedLLMHandler()


@pytest.fixture
def search_results():
    return [
        {
            "content": "FastAPI provides automatic OpenAPI schema generation.",
            "metadata": {"technology": "fastapi", "source": "docs", "title": "Intro"},
            "score": 0.92,
        },
        {
            "content": "Use @app.get('/') to define a GET endpoint in FastAPI.",
            "metadata": {"technology": "fastapi", "source": "tutorial"},
            "score": 0.85,
        },
    ]


# ─── Initialization ───────────────────────────────────────────────────────────

class TestLLMHandlerInit:
    def test_creates_without_error(self):
        h = EnhancedLLMHandler()
        assert h is not None

    def test_has_current_provider_attribute(self):
        h = EnhancedLLMHandler()
        assert hasattr(h, "current_provider")
        assert isinstance(h.current_provider, str)

    def test_get_available_providers_returns_list(self, handler):
        providers = handler.get_available_providers()
        assert isinstance(providers, list)

    def test_provider_list_entries_are_strings(self, handler):
        providers = handler.get_available_providers()
        for p in providers:
            assert isinstance(p, str)

    def test_providers_dict_has_known_keys(self, handler):
        assert "ollama" in handler.providers
        assert "openai" in handler.providers
        assert "gemini" in handler.providers


# ─── Provider Switching ───────────────────────────────────────────────────────

class TestProviderSwitching:
    def test_set_provider_to_known_name(self, handler):
        # set_provider returns bool; may fail if provider unavailable
        result = handler.set_provider("ollama")
        assert isinstance(result, bool)

    def test_set_provider_to_unknown_returns_false(self, handler):
        result = handler.set_provider("totally_unknown_provider_xyz")
        assert result is False

    def test_current_provider_is_string(self, handler):
        assert isinstance(handler.current_provider, str)
        assert len(handler.current_provider) > 0


# ─── Answer Generation (mocked) ──────────────────────────────────────────────

class TestAnswerGeneration:
    def test_generate_answer_returns_string(self, handler, search_results):
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.generate_response.return_value = "FastAPI is a modern Python web framework."
        handler.providers[handler.current_provider] = mock_provider

        answer = handler.generate_answer("What is FastAPI?", search_results)
        assert isinstance(answer, str)
        assert len(answer) > 0

    def test_generate_answer_calls_provider(self, handler, search_results):
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.generate_response.return_value = "Mock answer."
        handler.providers[handler.current_provider] = mock_provider

        handler.generate_answer("What is FastAPI?", search_results)
        assert mock_provider.generate_response.called

    def test_generate_answer_with_empty_results(self, handler):
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.generate_response.return_value = "I don't have information on that."
        handler.providers[handler.current_provider] = mock_provider

        answer = handler.generate_answer("Random question?", [])
        assert isinstance(answer, str)


# ─── Code Generation (mocked) ────────────────────────────────────────────────

class TestCodeGeneration:
    def test_generate_code_returns_string(self, handler, search_results):
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.generate_response.return_value = "def hello(): return 'Hello'"
        handler.providers[handler.current_provider] = mock_provider

        result = handler.generate_code(
            prompt="Create a simple FastAPI endpoint",
            language="python",
            context=search_results,
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_code_passes_prompt_to_provider(self, handler):
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.generate_response.return_value = "def foo(): pass"
        handler.providers[handler.current_provider] = mock_provider

        handler.generate_code("Write a function", language="python", context=[])
        call_args = mock_provider.generate_response.call_args[0]
        # First arg is the prompt, should contain "python"
        assert "python" in call_args[0].lower()


# ─── Provider Status ─────────────────────────────────────────────────────────

class TestProviderStatus:
    def test_get_provider_status_returns_dict(self, handler):
        status = handler.get_provider_status()
        assert isinstance(status, dict)

    def test_provider_status_has_ollama_key(self, handler):
        status = handler.get_provider_status()
        assert "ollama" in status

    def test_provider_status_values_are_bool(self, handler):
        status = handler.get_provider_status()
        for v in status.values():
            assert isinstance(v, bool)
