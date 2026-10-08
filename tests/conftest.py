import pytest
from app.config import settings


@pytest.fixture(autouse=True)
def force_mock_llm_for_tests(monkeypatch):
    """Ensures test suite always executes deterministically offline with MockLLMClient."""
    monkeypatch.setattr(settings, "llm_provider", "mock")
