import os
import pytest
from app.config import settings


@pytest.fixture(autouse=True)
def force_mock_llm_for_tests(monkeypatch):
    """Ensures test suite always executes deterministically offline with MockLLMClient."""
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(settings, "llm_provider", "mock")
    monkeypatch.setattr(settings, "gemini_api_key", None)

